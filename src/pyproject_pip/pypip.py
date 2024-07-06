"""Synchronizes requirements and hatch pyproject."""

import logging
import os
import subprocess
import sys
from pathlib import Path
import tomlkit
import click
import requests
import tomlkit


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


def modify_requirements(package_name, package_version=None, action="install") -> None:
    """Modify the requirements.txt file to install or uninstall a package.

    Args:
        package_name (str): The name of the package to install or uninstall.
        package_version (str, optional): The version of the package to install. Defaults to None.
        action (str): The action to perform, either 'install' or 'uninstall'.

    Raises:
        FileNotFoundError: If the requirements.txt file does not exist when attempting to read.
    """
    try:
        with open("requirements.txt") as f:
            lines = f.readlines()
    except FileNotFoundError:
        logging.warning("requirements.txt file not found, creating a new file.")
        lines = []

    # Filter out comments and empty lines
    lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]

    # Extract the base package name and optional extras
    base_package_name, *extras = package_name.split("[")
    extras_str = "[" + ",".join(extras) if extras else ""
    package_line = next((line for line in lines if base_package_name == line.split("[")[0].split("==")[0]), None)

    if action == "install" and package_version:
        new_line = f"{base_package_name}{extras_str}=={package_version}"
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
    if "[" in line and ("]" not in line or "," not in line):
        start = line.index("[")
        output_lines.append(line[:start + 1])
        line = line[start + 1:]

    deps = line.split(",")
    for dep in deps:
        if dep.endswith("]"):
            dep = dep.replace("]", "")
            output_lines.append(dep)
            output_lines.append("]")
            continue
        new_dep = dep + "," if dep != deps[-1] else dep
        if new_dep.strip():
            output_lines.append(new_dep)

    

def write_pyproject(data):
    with open("pyproject.toml", "w") as f:
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

            if "]" in line and inside_dependencies and not "[" in line:
                inside_dependencies = False

            if inside_optional_dependencies:
                process_dependencies(line, output_lines)
    
            if "dependencies" in line and not "optional-dependencies" in line and not "extra-dependencies" in line and not inside_optional_dependencies:
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

def base_name(package_name):
    """Extract the base package name from a package name with optional extras.

    Args:
        package_name (str): The package name with optional extras.

    Returns:
        str: The base package name without extras.
    """
    return package_name.split("[")[0].split("==")[0]

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


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("-v", "--hatch-env", default=None, help="Specify the Hatch environment to use")
def cli(ctx, hatch_env) -> None:
    """Main CLI entry point. If no subcommand is provided, it shows the dependencies.

    Args:
        ctx (click.Context): Click context object.
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
    """
    if ctx.invoked_subcommand is None:
        show_command(hatch_env)


def get_pip_freeze():
    """Get the list of installed packages as a set.

    Returns:
        set: Set of installed packages with their versions.
    """
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=subprocess.PIPE, check=False)
    return set(result.stdout.decode().splitlines())


@cli.command("install")
@click.argument("packages", nargs=-1)
@click.option(
    "-r", "--requirements", type=click.Path(exists=True), help="Install packages from the given requirements file",
)
@click.option("-U", "--upgrade", is_flag=True, help="Upgrade the package(s)")
@click.option("-e", "--editable", is_flag=True, help="Install a package in editable mode")
@click.option("--hatch-env", default=None ,help="Specify the Hatch environment to use")
@click.option("-g", "--dependency-group", default="dependencies", help="Specify the dependency group to use")
def install_command(packages, requirements, upgrade, editable, hatch_env, dependency_group) -> None:
    """Install packages and update requirements.txt and pyproject.toml accordingly.

    Args:
        packages (tuple): Packages to install.
        requirements (str, optional): Path to requirements file. If provided, install packages from this file.
        upgrade (bool, optional): Whether to upgrade the packages. Defaults to False.
        editable (bool, optional): Whether to install a package in editable mode. Defaults to False.
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
        dependency_group (str, optional): The dependency group to use. Defaults to "dependencies".
    """
    try:
        if requirements:
            with open(requirements) as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        initial_packages = get_requirements_packages()


        for package in packages:
            package_install_cmd = [sys.executable, "-m", "pip", "install"]
            if editable:
                package_install_cmd.append("-e")
            if upgrade:
                package_install_cmd.append("-U")
            package_install_cmd.append(package)
            subprocess.check_call(package_install_cmd)
            modify_requirements(package, action="install")

            # Determine the newly installed package by comparing pip freeze output
            final_packages = get_requirements_packages()
            new_packages = final_packages - initial_packages
            if new_packages:
                for new_package in new_packages:
                    package_name, package_version = new_package.split("==")
                    modify_requirements(package_name, package_version, action="install")
                    modify_pyproject_toml(package_name, package_version, action="install", hatch_env=hatch_env, dependency_group=dependency_group)
            else:
                package_version = get_latest_version(package)
                modify_pyproject_toml(package,package_version, action="install", hatch_env=hatch_env, dependency_group=dependency_group)

    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to install {package}.", err=True)
        click.echo(f"Reason: {e}", err=True)
        sys.exit(e.returncode)


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

def get_requirements_packages():
    """Get the list of packages from the requirements.txt file.

    Returns:
        set: Set of packages listed in the requirements.txt file.
    """
    with open("requirements.txt") as f:
        return set(line.strip() for line in f if line.strip() and not line.strip().startswith("#"))


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


@cli.command("uninstall")
@click.argument("packages", nargs=-1)
@click.option("--hatch-env", default=None, help="Specify the Hatch environment to use")
@click.option("-g", "--dependency-group", default="dependencies", help="Specify the dependency group to use")
def uninstall_command(packages, hatch_env, dependency_group) -> None:
    """Uninstall packages and update requirements.txt and pyproject.toml accordingly.

    Args:
        packages (tuple): Packages to uninstall.
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
    """
    for package in packages:
        package_name = package.split("==")[0].split("[")[0]  # Handle extras
        in_requirements = is_package_in_requirements(package_name)
        in_pyproject = is_package_in_pyproject(package_name, hatch_env)

        # if not in_requirements and not in_pyproject:
        #     click.echo(f"Package '{package_name}' is not listed in requirements.txt or pyproject.toml, skipping.")
        #     continue

        try:
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", package_name, "-y"])
            modify_requirements(package_name, action="uninstall")
            modify_pyproject_toml(package_name, action="uninstall", hatch_env=hatch_env, dependency_group=dependency_group)
            click.echo(f"Successfully uninstalled {package_name}")
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Failed to uninstall {package_name}.", err=True)
            click.echo(f"Reason: {e}", err=True)
            sys.exit(e.returncode)
        except Exception as e:
            click.echo(f"Unexpected error occurred while trying to uninstall {package_name}:", err=True)
            click.echo(f"{e}", err=True)
            sys.exit(1)


@cli.command("show")
@click.option("--hatch-env", default=None, help="Specify the Hatch environment to use")
def show_command(hatch_env) -> None:
    """Show the dependencies from the pyproject.toml file.

    Args:
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
    """
    try:
        with open("pyproject.toml") as f:
            content = f.read()
            pyproject = tomlkit.parse(content)

        # Determine if we are using Hatch or defaulting to project dependencies
        if "tool" in pyproject and "hatch" in pyproject["tool"] and hatch_env is not None:
            dependencies = pyproject.get("tool", {}).get("hatch", {}).get("envs", {}).get(hatch_env, {}).get("dependencies", [])   
        else:
            dependencies = pyproject.get("project", {}).get("dependencies", [])

        if dependencies:
            click.echo("Dependencies:")
            for dep in dependencies:
                click.echo(f"  {dep}")
    except FileNotFoundError:
        click.echo("pyproject.toml file not found.")
        sys.exit(1)
    finally:
        sys.exit(0)

if __name__ == "__main__":
    cli()
