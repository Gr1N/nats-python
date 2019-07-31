local
  volume_cached_poetry = 'cached-poetry',
  volume_cached_deps = 'cached-deps',

  git_step = {
    name: 'fetch',
    image: 'docker:git',
    commands: ['git fetch --tags'],
  },
  py_step(name, commands, version='3.7') = {
    name: name,
    pull: 'always',
    image: 'python:%s' % version,
    commands: commands,
    volumes: [
      {
        name: volume_cached_poetry,
        path: '/root/.poetry',
      },
      {
        name: volume_cached_deps,
        path: '/root/.cache/pypoetry/virtualenvs',
      },
    ],
  },
  notify_step(name, message) = {
    name: name,
    pull: 'always',
    image: 'appleboy/drone-telegram',
    environment: {
      PLUGIN_TOKEN: {
        from_secret: 'TELEGRAM_BOT_TOKEN',
      },
      PLUGIN_TO: {
        from_secret: 'TELEGRAM_CHAT_ID',
      },
      PLUGIN_MESSAGE: message,
    },
  };

{
  kind: 'pipeline',
  name: 'default',
  clone: {
    depth: 50,
  },
  services: [
    {
      name: 'nats',
      image: 'nats',
      pull: 'always',
    },
  ],
  steps: [
    git_step,
    py_step('deps-3.6', ['make install'], version='3.6'),
    py_step('deps-3.7', ['make install']),
    py_step('lint-3.7', ['make lint']),
    py_step('test-3.6', ['make test'], version='3.6') {
      environment: {
        NATS_URL: 'nats://nats:4222',
      },
    },
    py_step('test-3.7', ['make test', 'make codecov']) {
      environment: {
        NATS_URL: 'nats://nats:4222',
        CODECOV_TOKEN: {
          from_secret: 'CODECOV_TOKEN',
        },
      },
    },
    notify_step('lint/test completed', |||
      {{#success build.status}}
        `{{repo.name}}` build {{build.number}} succeeded. Good job.
      {{else}}
        `{{repo.name}}` build {{build.number}} failed. Fix me please.
      {{/success}}
    |||) {
      when: {
        branch: ['master'],
        event: {
          exclude:
            ['pull_request'],
        },
        status: [
          'success',
          'failure',
        ],
      },
    },
    py_step('publish', ['make publish']) {
      environment: {
        PYPI_USERNAME: {
          from_secret: 'PYPI_USERNAME',
        },
        PYPI_PASSWORD: {
          from_secret: 'PYPI_PASSWORD',
        },
      },
      when: {
        event: ['tag'],
      },
    },
    notify_step('publish completed', |||
      {{#success build.status}}
        `{{repo.name}}` publish {{build.tag}} succeeded. Good job.
      {{else}}
        `{{repo.name}}` publish {{build.tag}} failed. Fix me please.
      {{/success}}
    |||) {
      when: {
        event: ['tag'],
        status: [
          'success',
          'failure',
        ],
      },
    },
  ],
  volumes: [
    {
      name: volume_cached_poetry,
      temp: {},
    },
    {
      name: volume_cached_deps,
      temp: {},
    },
  ],
}
