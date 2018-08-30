# nats-python [![Build Status](https://travis-ci.org/Gr1N/nats-python.svg?branch=master)](https://travis-ci.org/Gr1N/nats-python) [![codecov](https://codecov.io/gh/Gr1N/nats-python/branch/master/graph/badge.svg)](https://codecov.io/gh/Gr1N/nats-python) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Python client for NATS messaging system.

This project is a replacement for abandoned [pynats](https://github.com/mcuadros/pynats). `nats-python` supports only Python 3.6+ and fully covered with typings.

Go to the [asyncio-nats](https://github.com/nats-io/asyncio-nats) project, if you're looking for `asyncio` implementation.

## Installation

    $ pip install nats-python

## Usage

    from pynats import NATSClient

    with NATSClient() as client:
        client.publish("test-subject", payload=b"test-payload")

## Contributing

To work on the `nats-python` codebase, you'll want to clone the project locally and install the required dependencies via [poetry](https://poetry.eustace.io):

    $ git clone git@github.com:Gr1N/nats-python.git
    $ poetry install

To run tests and linters use command below:

    $ poetry run tox

If you want to run only tests or linters you can explicitly specify which test environment you want to run, e.g.:

    $ poetry run tox -e py37-tests

## License

`nats-python` is licensed under the MIT license. See the license file for details.
