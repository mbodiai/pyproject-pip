
from pathlib import Path
from typing import Literal

getcwd = Path.cwd
WORKFLOW_UBUNTU = """name: "Ubuntu"

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


def create_project(
    project_name,
    author,
    description="",
    deps: list[str] | Literal["local"] | None = None,
    python_version="3.11",
    add_cli=True,
) -> None:
    # Create project root directory
    root = Path(getcwd())
    project_root = root / project_name
    Path(project_root).mkdir(exist_ok=True)
    # Create main directories
    dirs = ["assets", "docs", "examples", "resources", "tests"]
    for dir in dirs: # noqa
        Path(root / dir).mkdir(exist_ok=True)

        # Create __about__.py in project directory
    Path(project_root / "__about__.py").touch(exist_ok=True)
    # Create __init__.py in project directory
    if not Path(project_root / "__init__.py").exists() and not Path(project_root / "main.py").exists() and add_cli:
        Path(project_root / "__init__.py").write_text(
            "from .main import cli\n\n__all__ = ['cli']",
        )
        Path(project_root / "main.py").write_text(
            "from click import command\n\n@command()\ndef cli() -> None:\n    pass\n\nif __name__ == '__main__':\n    cli()",
        )

    else:
        Path(project_root / "__init__.py").touch(exist_ok=True)

    if not Path(project_root / "__about__.py").exists():
        Path(project_root / "__about__.py").write_text('__version__ = "0.0.1"')
    elif "__version__" not in Path(project_root / "__about__.py").read_text() and\
      "y" in input("No __version__ found in __about__.py. Overwrite? (y/n): "):
        Path(project_root / "__about__.py").write_text("__version__ = '0.0.1'")
        # Create files in root
    files = [
        ("LICENSE", ""),
        (
            "README.md",
            f"# {project_name}\n\n{description}\n\n## Installation\n\n```bash\npip install {project_name}\n```\n",
        ),
        (
            "pyproject.toml",
            create_pyproject_toml(
                project_name,
                author,
                description,
                deps,
                python_version=python_version,
                add_cli=add_cli,
            ),
        ),
        ("requirements.txt", "click" if add_cli else ""),
    ]
    for file, content in files:
        if Path(root / file).exists() and "y" not in input(
            f"{file} already exists. Overwrite? (y/n): ",
        ):
            print(f"{file} already exists. Skipping...")  # noqa
            continue
        Path(root / file).touch(exist_ok=True)
        Path(root / file).write_text(content)

    Path("tests").mkdir(exist_ok=True)

    # Create workflows directory
    workflows = root / ".github/workflows"
    workflows.mkdir(exist_ok=True, parents=True)
    if Path(workflows / "macos.yml").exists() or Path(workflows / "ubuntu.yml").exists():
        should_overwrite = input("Workflows already exist. Overwrite? (y/n): ")
        if should_overwrite.lower() != "y":
            return
    Path(workflows / "macos.yml").touch(exist_ok=True)
    Path(workflows / "ubuntu.yml").touch(exist_ok=True)
    Path(workflows / "macos.yml").write_text(WORKFLOW_MAC)
    Path(workflows / "ubuntu.yml").write_text(WORKFLOW_UBUNTU)


def create_pyproject_toml(
    project_name,
    author,
    desc="",
    deps=None,
    python_version="3.10",
    add_cli=True,
) -> str:
    """Create a pyproject.toml file for a Hatch project."""
    authors = ",".join(["{" + f'name="{a}"' + "}" for a in author.split(",")])
    test_docs = "{tests,docs}"
    deps = ",\n     ".join([f'"{dep}"' for dep in deps]) if deps else ""
    python_version = str(python_version)
    version_str = f"py{python_version.replace('.', '')}"
    cli_str = f"{project_name} ={project_name}:cli" if add_cli else ""

    python_version_str = ">=" + python_version.lstrip("><=")
    if len(python_version_str.split(".")) < 2:
      raise ValueError("Invalid Python version")
    programming_language = [f"Programming Language :: Python ::3.{str(v)}" for v in range(int(python_version_str.split(".")[1]), 13)]
    programming_language =  "\n".join(f"\"{programming_language}\"," for programming_language in programming_language)

    return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
dynamic = ["version"]
description = "{desc}"
readme = "README.md"
requires-python = "{python_version_str}"
license = "apache-2.0"
keywords = []
authors = [{authors}]
classifiers = [
"Development Status :: 4 - Beta",
"Programming Language :: Python",
{programming_language}
"Programming Language :: Python :: Implementation :: CPython",
"Programming Language :: Python :: Implementation :: PyPy",
]

dependencies = [
    {deps}
]

[project.optional-dependencies]


[project.urls]
Documentation = "https://github.com/{author}/{project_name}#readme"
Issues = "https://github.com/{author}/{project_name}/issues"
Source = "https://github.com/{author}/{project_name}"

[project.scripts]
{cli_str}

[tool.hatch.version]
path = "{project_name}/__about__.py"

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.targets.wheel.force-include]
"resources" = "{project_name}/resources"

[tool.hatch.envs.default]
python = "{python_version}"
path = ".{project_name}/envs/{project_name}"
dependencies = [
"pytest",
"pytest-mock",
"pytest-asyncio",
]

[tool.hatch.envs.default.env-vars]

[tool.hatch.envs.conda]
type = "conda"
python = "{python_version}"
command = "conda"
conda-forge = false
environment-file = "environment.yml"
prefix = ".venv/"

[tool.hatch.envs.default.scripts]
test = "pytest -vv --ignore third_party {{args:tests}}"
test-cov = "coverage run -m pytest {{args:tests}}"
cov-report = ["- coverage combine", "coverage report"]
cov = ["test-cov", "cov-report"]

[[tool.hatch.envs.all.matrix]]
python = ["3.10", "3.11", "3.12"]

[tool.hatch.envs.types]
dependencies = [
"mypy>=1.0.0"
]
[tool.hatch.envs.types.scripts]
check = "mypy --install-types --non-interactive {{args:{project_name}/ tests}}"

[tool.coverage.run]
source_pkgs = ["{project_name}", "tests"]
branch = true
parallel = true
omit = ["{project_name}/__about__.py"]

[tool.coverage.paths]
{project_name} = ["{project_name}/"]
tests = ["tests"]

[tool.coverage.report]
exclude_lines = ["no cov", "if __name__ == .__main__.:", "if TYPE_CHECKING:"]

[tool.ruff]
line-length = 120
indent-width = 4
target-version = "{version_str}"

[tool.ruff.lint]
extend-unsafe-fixes = ["ALL"]
select = [
"A", "C4", "D", "E", "F", "UP", "B", "SIM", "N", "ANN", "ASYNC",
"S", "T20", "RET", "SIM", "ARG", "PTH", "ERA", "PD", "I", "PLW",
]
ignore = [
"D100", "D101", "D104", "D106", "ANN101", "ANN102", "ANN003", "UP009", "ANN204",
"B026", "ANN001", "ANN401", "ANN202", "D107", "D102", "D103", "E731", "UP006",
"UP035", "ANN002", "PLW2901"
]
fixable = ["ALL"]
unfixable = []

[tool.ruff.format]
docstring-code-format = true
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"**/{test_docs}/*" = ["ALL"]
"**__init__.py" = ["F401"]
"""


