# nats-python

[![Build Status](https://github.com/Gr1N/nats-python/workflows/default/badge.svg)](https://github.com/Gr1N/nats-python/actions?query=workflow%3Adefault) [![codecov](https://codecov.io/gh/Gr1N/nats-python/branch/master/graph/badge.svg)](https://codecov.io/gh/Gr1N/nats-python) ![PyPI](https://img.shields.io/pypi/v/nats-python.svg?label=pypi%20version) ![PyPI - Downloads](https://img.shields.io/pypi/dm/nats-python.svg?label=pypi%20downloads)

Python client for NATS messaging system.

This project is a replacement for abandoned [pynats](https://github.com/mcuadros/pynats). `nats-python` supports only Python 3.6+ and fully covered with typings.

Go to the [asyncio-nats](https://github.com/nats-io/asyncio-nats) project, if you're looking for `asyncio` implementation.

## Installation

```sh
$ pip install nats-python
```

## Usage

```python
from pynats import NATSClient

with NATSClient() as client:
    client.publish("test-subject", payload=b"test-payload")
```

## Contributing

To work on the `nats-python` codebase, you'll want to clone the project locally and install the required dependencies via [poetry](https://poetry.eustace.io):

```sh
$ git clone git@github.com:Gr1N/nats-python.git
$ make install
```

To run tests and linters use command below:

```sh
$ make lint && make test
```

If you want to run only tests or linters you can explicitly specify which test environment you want to run, e.g.:

```sh
$ make lint-black
```

## License

`nats-python` is licensed under the MIT license. See the license file for details.
