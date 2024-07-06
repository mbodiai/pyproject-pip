# pyproject-pip

[![PyPI - Version](https://img.shields.io/pypi/v/pyproject-pip.svg)](https://pypi.org/project/pyproject-pip)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyproject-pip.svg)](https://pypi.org/project/pyproject-pip)

-----

Install and manage pyproject.toml with pip commands.

See usage:

```
pypip --help
```


## Table of Contents

- [pyproject-pip](#pyproject-pip)
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

  Main CLI entry point. If no subcommand is provided, it shows the
  dependencies.

  Args:     ctx (click.Context): Click context object.     hatch_env (str,
  optional): The Hatch environment to use. Defaults to "default".

Options:
  -v, --hatch-env TEXT  Specify the Hatch environment to use
  --help                Show this message and exit.

Commands:
  install    Install packages and update requirements.txt and...
  show       Show the dependencies from the pyproject.toml file.
  uninstall  Uninstall packages and update requirements.txt and...
```

## License

`pyproject-pip` is distributed under the terms of the [apache-2.0](https://spdx.org/licenses/apache-2.0.html) license.
