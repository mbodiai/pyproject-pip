"""Synchronizes requirements and hatch pyproject."""

import logging
import re
import subprocess
import sys
from pathlib import Path
import markdown2
import tomlkit
import requests

def clean_text(md_text):
    """Convert Markdown to clean plain text."""
    # Convert Markdown to HTML using markdown2
    html_description = markdown2.markdown(md_text)

    # Function to remove HTML tags
    def strip_html_tags(html):
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)

    # Strip HTML tags to get plain text
    plain_text_description = strip_html_tags(html_description)

    # Function to remove reStructuredText (reST) directives and roles
    def strip_rst(text):
        # Remove reST directives and roles
        text = re.sub(r'\.\. .*:: .*', '', text)  # remove directives like .. image:: URL
        text = re.sub(r':\w+:.*', '', text)  # remove roles like :target: URL
        text = re.sub(r'\.\. _.*: .*', '', text)  # remove hyperlink targets like .. _name: URL
        return text

    # Clean the plain text description from reST and other special characters
    clean_text = strip_rst(plain_text_description)
    clean_text = re.sub(r'&nbsp;', ' ', clean_text)  # Replace HTML entities
    # clean_text = re.sub(r'\n{2,}', '\n\n', clean_text)  # Replace multiple newlines with a single newline
    clean_text = clean_text.strip()
    # clean_text = clean_text.replace("\n", " ")

    return clean_text

def get_latest_version(package_name):
    """Gets the latest version of the specified package from PyPI.

    Args:
        package_name (str): The name of the package to fetch the latest version for.

    Returns:
        str or None: The latest version of the package, or None if not found or on error.
    """
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        response.raise_for_status()  # Raises stored HTTPError, if one occurred.
        data = response.json()
        releases = data.get("releases", {})
        if releases:
            filtered_versions = [version for version in releases if all(part.isdigit() for part in version.split("."))]
            sorted_versions = sorted(filtered_versions, key=lambda x: tuple(map(int, x.split("."))), reverse=True)
            return sorted_versions[0] if sorted_versions else None
    except Exception:
        pass
    return None

def search_package(package_name):
    """Search for a package on PyPI and return the description, details, and GitHub URL if available.

    Args:
        package_name (str): The name of the package to search for.
    
    Returns:
        dict: The package information.
    """
    package_info = {}
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        response.raise_for_status()  # Raises stored HTTPError, if one occurred.
        data = response.json()
        info = data.get("info", {})
        
        package_info["description"] = info.get("summary", "")
        package_info["details"] = info.get("description", "")
        
        # Get GitHub URL if available
        project_urls = info.get("project_urls", {})
        package_info["github_url"] = next(
            (url for _, url in project_urls.items() if "github.com" in url.lower()), None
        )
    except requests.RequestException as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return package_info


def get_package_names(query_key):
    """Fetch package names from PyPI search results."""
    search_url = f"https://pypi.org/search/?q={query_key}"
    response = requests.get(search_url)
    response.raise_for_status()
    page_content = response.text
    
    # Extract package names from search results
    start_token = '<a class="package-snippet"'
    end_token = '</a>'
    name_token = '<span class="package-snippet__name">'
    
    package_names = []
    start = 0
    while True:
        start = page_content.find(start_token, start)
        if start == -1:
            break
        end = page_content.find(end_token, start)
        snippet = page_content[start:end]
        name_start = snippet.find(name_token)
        if name_start != -1:
            name_start += len(name_token)
            name_end = snippet.find('</span>', name_start)
            package_name = snippet[name_start:name_end]
            package_names.append(package_name)
        start = end
    
    return package_names


def get_package_info(package_name, verbose=False):
    """Retrieve detailed package information from PyPI JSON API."""
    package_url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(package_url)
    response.raise_for_status()
    package_data = response.json()
    
    info = package_data.get("info", {})

    downloads = package_data.get("downloads", {}).get("last_month", 0)
    

    package_info = {
        "name": info.get("name", ""),
        "version": info.get("version", ""),
        "summary": info.get("summary", ""),
        "downloads": downloads
    }
    if verbose:
        package_info["description"] = clean_text(info.get("description", ""))
    project_urls = info.get("project_urls", {})
    try:
        package_info["github_url"] = next(
            (url for _, url in project_urls.items() if "github.com" in url.lower()), None
        )
    except (StopIteration, TypeError, AttributeError):
        package_info["github_url"] = None

    return package_info


def find_and_sort(query_key, limit=5, sort_key="downloads") -> list:
    """Find and sort potential packages by a specified key.

    Args:
        query_key (str): The key to query for.
        sort_key (str): The key to sort by. Defaults to "downloads".
        
    Returns:
        list: List of packages sorted by the specified key.
    """
    try:
        package_names = get_package_names(query_key)
        packages = []
        for package_name in package_names:
            package_info = get_package_info(package_name)
            packages.append(package_info)
        # Sort the packages by the specified key
        sorted_packages = sorted(packages, key=lambda x: x.get(sort_key, 0), reverse=True)
        return sorted_packages[:limit]

    except requests.RequestException as e:
        print(f"HTTP error occurred: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def modify_requirements(package_name, package_version=None, action="install") -> None:
    """Modify the requirements.txt file to install or uninstall a package.

    Args:
        package_name (str): The name of the package to install or uninstall.
        package_version (str, optional): The version of the package to install. Defaults to None.
        action (str): The action to perform, either 'install' or 'uninstall'.

    Raises:
        FileNotFoundError: If the requirements.txt file does not exist when attempting to read.
    """
    lines = get_requirements_packages(as_set=False)

    # Extract the base package name and optional extras
    base_package_name, *extras = package_name.split("[")
    extras_str = "[" + ",".join(extras) if extras else ""
    package_line = next((line for line in lines if base_package_name == line.split("[")[0].split("==")[0]), None)

    if action == "install":
        if package_version is not  None:
            new_line = f"{base_package_name}{extras_str}=={package_version}"
        else:
            new_line = f"{base_package_name}{extras_str}"

        if package_line:
            # Replace the line with the same base package name
            lines = [line if base_package_name != line.split("[")[0].split("==")[0] else new_line for line in lines]
        else:
            lines.append(new_line)

    elif action == "uninstall":
        # Remove lines with the same base package name
        lines = [line for line in lines if base_package_name != line.split("[")[0].split("==")[0]]

    # Ensure each line ends with a newline character
    lines = [line + "\n" for line in lines]
    with open("requirements.txt", "w") as f:
        f.writelines(lines)


def is_group(line):
    return "[" in line and "]" in line and "\"" not in line[line.index("["):line.index("]")]


def process_dependencies(line, output_lines):
    lines = []
    if "[" in line and ("]" not in line or "," not in line):
        start = line.index("[")
        lines.append(line[:start + 1])
        line = line[start + 1:]

    deps = line.split(",")
    i = 0
    while i < len(deps):
        dep = deps[i]
        if "[" in dep and "]" not in dep:
            while "]" not in dep:
                dep += "," + deps[i+1]
                i += 1
            lines.append(dep + ",")
            i += 1
            continue
        if dep.endswith("]"):
            dep = dep.replace("]", "")
            lines.append(dep)
            lines.append("]")
            i += 1
            continue
        new_dep = dep + "," if dep != deps[-1] else dep
        if new_dep.strip():
            lines.append(new_dep)
        i += 1
    
    for line in lines:
        output_lines.append("  " + line.strip() if not line.strip().startswith("[") else line.strip())

def write_pyproject(data, filename="pyproject.toml"):
    """Write the modified pyproject.toml data back to the file."""
    original_data = Path(filename).read_text()
    try:
        with Path(filename).open("w") as f:
            toml_str = tomlkit.dumps(data)
            inside_dependencies = False
            inside_optional_dependencies = False

            input_lines = toml_str.splitlines()
            output_lines = []
            for input_line in input_lines:
                line = input_line.rstrip()
                if is_group(line):
                    inside_dependencies = False
                    inside_optional_dependencies = "optional-dependencies" in line
                    output_lines.append(line)
                    continue

                if "]" in line and inside_dependencies and "[" not in line:
                    inside_dependencies = False

                if inside_optional_dependencies:
                    process_dependencies(line, output_lines)
        
                if "dependencies" in line and "optional-dependencies" not in line and "extra-dependencies" not in line and not inside_optional_dependencies:
                    inside_dependencies = True
                    inside_optional_dependencies = False
                    output_lines.append(line[:line.index("[") + 1])
                    line = line[line.index("[") + 1:]

                if inside_dependencies and not inside_optional_dependencies:
                    inside_optional_dependencies = False
                    process_dependencies(line, output_lines)

                elif not inside_dependencies and not inside_optional_dependencies:
                    output_lines.append(line)

            written = []
            for line in output_lines:
                if is_group(line) and written and not written[-1].endswith("\n"):
                    f.write("\n")
                    written.append("\n")
                written.append(line + "\n")
                f.write(line + "\n")
    except Exception as e:
        print(f"An error occurred while writing to {filename}: {e}")
        with Path(filename).open("w") as f:
            f.write(original_data)

def base_name(package_name):
    """Extract the base package name from a package name with optional extras.

    Args:
        package_name (str): The package name with optional extras.

    Returns:
        str: The base package name without extras.
    """
    return package_name.split("[")[0].split("==")[0]

def name_and_version(package_name, upgrade=False):
    if upgrade:
        version = get_latest_version(base_name(package_name))
        return base_name(package_name), version
    if "==" in package_name:
        return package_name.split("==")
    return package_name, None

def modify_dependencies(dependencies, package_version_str, action):
    """Modify the dependencies list for installing or uninstalling a package.

    Args:
        dependencies (list): List of current dependencies.
        package_version_str (str): Package with version string.
        action (str): Action to perform, either 'install' or 'uninstall'.

    Returns:
        list: Modified list of dependencies.
    """
    dependencies = [dep.strip() for dep in dependencies if base_name(dep) != base_name(package_version_str)]
    if action == "install":
        dependencies.append(package_version_str.strip())
    dependencies.sort(key=lambda x: x.lower())  # Sort dependencies alphabetically
    return dependencies

def modify_pyproject_toml(
    package_name,
    package_version="",
    action="install",
    hatch_env=None,
    dependency_group="dependencies",
) -> None:
    """Modify the pyproject.toml file to update dependencies based on action.

    Args:
        package_name (str): The name of the package to install or uninstall.
        package_version (str, optional): The version of the package. Defaults to "".
        action (str): The action to perform, either 'install' or 'uninstall'.
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
        dependency_group (str, optional): The group of dependencies to modify. Defaults to "dependencies".
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        action = input("pyproject.toml not found. Do you want to create it? (y/n): ").lower()
        if "y" in action.lower():
            create_pyproject_toml()
        elif "n" in action.lower() and "y" in input("Check parent dirs? (y/n): ").lower():
            for _ in range(3):
                if pyproject_path.exists():
                    break
                pyproject_path = Path("../pyproject.toml")

            if not pyproject_path.exists():
                print("\033pyproject.toml not found in parent directories.\033[0m")
                sys.exit(1)
   

    with open("pyproject.toml") as f:
        content = f.read()
        pyproject = tomlkit.parse(content)

    is_optional = dependency_group != "dependencies"
    is_hatch_env = hatch_env and "tool" in pyproject and "hatch" in pyproject["tool"]
    if hatch_env and not is_hatch_env:
        raise ValueError("Hatch environment specified but hatch tool not found in pyproject.toml.")

    # Prepare the package string with version if provided
    package_version_str = f"{package_name}{('==' + package_version) if package_version else ''}"
    base_project =  pyproject.get("tool", {}).get("hatch", {}).get("envs", {}).get(hatch_env, {}) if is_hatch_env else pyproject.get("project", {})
    optional_base = pyproject.get("project").get("optional-dependencies", {})
    
    if is_optional:
        dependencies = optional_base.get(dependency_group, [])
        optional_base[dependency_group] = modify_dependencies(dependencies, package_version_str, action)

        all_group = optional_base.get("all", [])
        optional_base["all"] = modify_dependencies(all_group, package_version_str, action)
        pyproject["project"]["optional-dependencies"] = optional_base
    else:
        dependencies = base_project.get("dependencies", [])
        base_project["dependencies"] = modify_dependencies(dependencies, package_version_str, action)
    if is_hatch_env:
        pyproject["tool"]["hatch"]["envs"][hatch_env] = base_project
    else:
        pyproject["project"] = base_project

    write_pyproject(pyproject)


def get_pip_freeze():
    """Get the list of installed packages as a set.

    Returns:
        set: Set of installed packages with their versions.
    """
    result = subprocess.run([sys.executable, "-m", "pip", "freeze", "--local"], stdout=subprocess.PIPE, check=False)
    return set(result.stdout.decode().splitlines())


def is_package_in_requirements(package_name) -> bool:
    """Check if a package is listed in the requirements.txt file.

    Args:
        package_name (str): The name of the package.

    Returns:
        bool: True if the package is listed in requirements.txt, False otherwise.
    """
    if not Path("requirements.txt").exists():
        raise FileNotFoundError("requirements.txt file not found.")
    with open("requirements.txt") as f:
        return any(base_name(package_name) == base_name(line) for line in f)

def get_requirements_packages(requirements="requirements.txt", as_set=True):
    """Get the list of packages from the requirements.txt file.

    Returns:
        set: Set of packages listed in the requirements.txt file.
    """
    with open(requirements) as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    return set(lines) if as_set else lines


def is_package_in_pyproject(package_name, hatch_env=None) -> bool:
    """Check if a package is listed in the pyproject.toml file for a given Hatch environment.

    Args:
        package_name (str): The name of the package.
        hatch_env (str): The Hatch environment to check in. Defaults to "default".

    Returns:
        bool: True if the package is listed in pyproject.toml, False otherwise.
    """
    if not Path("pyproject.toml").exists():
        raise FileNotFoundError("pyproject.toml file not found.")
    with open("pyproject.toml") as f:
        content = f.read()
        pyproject = tomlkit.parse(content)
    is_hatch_env = hatch_env and "tool" in pyproject and "hatch" in pyproject["tool"]
    if hatch_env and not is_hatch_env:
        raise ValueError("Hatch environment specified but hatch tool not found in pyproject.toml.")
    if is_hatch_env:
        dependencies = pyproject["tool"]["hatch"]["envs"][hatch_env]["dependencies"]
    else:
        dependencies = pyproject.get("dependencies", [])
    return any(package_name in dep for dep in dependencies)

def create_pyproject_toml(project_name, author, desc="", deps=None, python_version="3.11"):
    """Create a pyproject.toml file for a Hatch project."""

    authors = ",".join(['{' + f'name="{a}"' + '}' for a in author.split(",")])
    test_docs = "{tests,docs}"
    deps = ",\n     ".join([f'"{dep}"' for dep in deps]) if deps else ""
    python_version = f'"{python_version}"' if not python_version.startswith('"') else python_version
    return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
dynamic = ["version"]
description = "{desc}"
readme = "README.md"
requires-python = {python_version}
license = "apache-2.0"
keywords = []
authors = [{authors}]
classifiers = [
"Development Status :: 4 - Beta",
"Programming Language :: Python",
"Programming Language :: Python :: {python_version}",
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

[tool.hatch.version]
path = "{project_name}/__about__.py"

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.targets.wheel.force-include]
"resources" = "{project_name}/resources"

[tool.hatch.envs.default]
python = {python_version}
path = ".{project_name}/envs/{project_name}"
dependencies = [
"pytest",
"pytest-mock",
"pytest-asyncio",
]

[tool.hatch.envs.default.env-vars]

[tool.hatch.envs.conda]
type = "conda"
python = {python_version}
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
target-version = "py310"

[tool.ruff.lint]
extend-unsafe-fixes = ["ALL"]
select = [
"A", "COM812", "C4", "D", "E", "F", "UP", "B", "SIM", "ISC", "N", "ANN", "ASYNC",
"S", "T20", "RET", "SIM", "ARG", "PTH", "ERA", "PD", "I", "PLW",
]
ignore = [
"D100", "D101", "D104", "D106", "ANN101", "ANN102", "ANN003", "UP009", "ANN204",
"B026", "ANN001", "ANN401", "ANN202", "D107", "D102", "D103", "E731", "UP006",
"UP035", "ANN002",
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
'''


