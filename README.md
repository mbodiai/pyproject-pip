# pyproject-pip (WIP)

[![PyPI - Version](https://img.shields.io/pypi/v/pyproject-pip.svg)](https://pypi.org/project/pyproject-pip)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyproject-pip.svg)](https://pypi.org/project/pyproject-pip)

-----

Install and manage pyproject.toml with pip commands.

See usage:

```
pypip --help
```


## Table of Contents

- [pyproject-pip (WIP)](#pyproject-pip-wip)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Usage](#usage)
  - [License](#license)

## Installation

```console
pip install pyproject-pip
```

## Usage

```console
pypip --help
```

```
Usage: pypip [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --hatch-env TEXT  Specify the Hatch environment to use
  --help                Show this message and exit.

Commands:
  find       Find a package on PyPI and optionally sort the results.
  info       Get information about a package from PyPI.
  install    Install packages and update requirements.txt and...
  show       Show the dependencies from the pyproject.toml file.
  uninstall  Uninstall packages and update requirements.txt and...
```

## License

`pyproject-pip` is distributed under the terms of the [apache-2.0](https://spdx.org/licenses/apache-2.0.html) license.
