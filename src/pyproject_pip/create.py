import os
from pathlib import Path
import shutil
import sys
from typing import Literal
from pyproject_pip.pypip import create_pyproject_toml
from os import getcwd

WORKFLOW_UBUNTU ="""name: "Ubuntu"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  ubuntu:
    name: ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-20.04, ubuntu-latest]

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v3
        with:
          python-version: 3.11

      - name: Run install script
        run: |
            python -m pip install --upgrade pip
            python -m pip install hatch

      - name: Cache packages
        uses: actions/cache@v3
        env:
          cache-name: cache-packages
        with:
          path: ~/.local/bin ~/.local/lib .mbodied/envs/mbodied
          key: ${{ runner.os }}-${{ env.cache-name }}-${{ hashFiles('install.bash') }}
          restore-keys: |
            ${{ runner.os }}-${{ env.cache-name }}-

      - name: Check disk usage
        run: df -h

      - name: Clean up before running tests
        run: |
          # Add commands to clean up unnecessary files
          sudo apt-get clean
          sudo rm -rf /usr/share/dotnet /etc/mysql /etc/php /etc/apt/sources.list.d
          # Add more cleanup commands as needed

      - name: Check disk usage after cleanup
        run: df -h

      - name: Run tests
        run: |
          hatch run pip install '.'
          hatch run test"""

WORKFLOW_MAC = """name: "MacOS | Python 3.12|3.11|3.10"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  test:
    name: Python ${{ matrix.python-version }}
    runs-on: macos-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.11", "3.10"]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v3
        with:
          python-version: ${{ matrix.python-version }}

      - name: Run install script
        run: |
            python -m pip install --upgrade pip
            python -m pip install hatch

      - name: Cache packages
        uses: actions/cache@v3
        env:
          cache-name: cache-packages
        with:
          path: ~/Library/Caches/Homebrew
          key: ${{ runner.os }}-${{ env.cache-name }}-${{ hashFiles('install.bash') }}
          restore-keys: |
            ${{ runner.os }}-${{ env.cache-name }}-
      - name: Run tests
        run: |
          hatch run pip install '.'
          hatch run test"""


def create_project(project_name, author,description="", deps: list[str] | Literal["local"] | None = None):
    # Create project root directory
    root = Path(getcwd()) 
    project_root = root / project_name
    Path(project_root).mkdir(exist_ok=True)
    # Create main directories
    dirs = ['assets', 'docs', 'examples', 'resources', 'tests']
    for dir in dirs:
        Path(root / dir).mkdir(exist_ok=True)

    # Create files in root
    files = [
        ('LICENSE', ''),
        ('README.md', f'# {project_name}\n\n{description}\n\n## Installation\n\n```bash\npip install {project_name}\n```\n'),
        ('pyproject.toml', create_pyproject_toml(project_name, author, deps)),
    ]
    for file, content in files:
        Path(project_root / file).touch(exist_ok=False)
        Path(file).write_text(content)

    # Create __about__.py in project directory
    Path(project_root / '__about__.py').touch(exist_ok=True)
    Path(project_root / '__about__.py').write_text('__version__ = "0.1.0"')

    # Create __init__.py in project directory
    Path(project_root / '__init__.py').touch(exist_ok=True)
    Path('tests').mkdir(exist_ok=True)

    # Create workflows directory
    workflows = root / '.github/workflows'
    workflows.mkdir(exist_ok=True, parents=True)
    Path(workflows / 'macos.yml').touch(exist_ok=False)
    Path(workflows / 'ubuntu.yml').touch(exist_ok=False)
    Path(workflows / 'macos.yml').write_text(WORKFLOW_MAC)
    Path(workflows / 'ubuntu.yml').write_text(WORKFLOW_UBUNTU)

if __name__ == "__main__":
    project_name = input("Enter project name: ")
    author = input("Enter author name: ")
    description = input("Enter project description: ")
    deps = input("Enter dependencies separated by commas: ").split(',')
    create_project(project_name, author, description, deps)