from pathlib import Path
from pyproject_pip.pypip import (
    get_requirements_packages,
    modify_requirements,
    modify_pyproject_toml,
    name_and_version,
    find_and_sort,
    get_package_info,
)
import subprocess
import sys
import tomlkit
import click

@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "-v", "--hatch-env", default=None, help="Specify the Hatch environment to use"
)
def cli(ctx, hatch_env) -> None:
    if ctx.invoked_subcommand is None:
        show_command(hatch_env)


@cli.command("install")
@click.argument("packages", nargs=-1)
@click.option(
    "-r",
    "--requirements",
    type=click.Path(exists=True),
    help="Install packages from the given requirements file",
)
@click.option("-U", "--upgrade", is_flag=True, help="Upgrade the package(s)")
@click.option(
    "-e", "--editable", is_flag=True, help="Install a package in editable mode"
)
@click.option("--hatch-env", default=None, help="Specify the Hatch environment to use")
@click.option(
    "-g",
    "--dependency-group",
    default="dependencies",
    help="Specify the dependency group to use",
)
def install_command(
    packages, requirements, upgrade, editable, hatch_env, dependency_group
) -> None:
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
            if not Path(requirements).exists():
                click.echo(f"Requirements file {requirements} not found. Creating it.")
                Path(requirements).touch()
            packages = get_requirements_packages(requirements)



        for package in packages:
            package_install_cmd = [sys.executable, "-m", "pip", "install"]
            if editable:
                package_install_cmd.append("-e")
            if upgrade:
                package_install_cmd.append("-U")
            package_install_cmd.append(package)
            subprocess.check_call(package_install_cmd)

            package_name, package_version = name_and_version(package, upgrade=upgrade)
            modify_pyproject_toml(
                package,
                package_version,
                action="install",
                hatch_env=hatch_env,
                dependency_group=dependency_group,
            )
            modify_requirements(package_name, package_version, action="install")

    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to install {package}.", err=True)
        click.echo(f"Reason: {e}", err=True)
        sys.exit(e.returncode)


@cli.command("uninstall")
@click.argument("packages", nargs=-1)
@click.option("--hatch-env", default=None, help="Specify the Hatch environment to use")
@click.option(
    "-g",
    "--dependency-group",
    default="dependencies",
    help="Specify the dependency group to use",
)
def uninstall_command(packages, hatch_env, dependency_group) -> None:
    """Uninstall packages and update requirements.txt and pyproject.toml accordingly.

    Args:
        packages (tuple): Packages to uninstall.
        hatch_env (str, optional): The Hatch environment to use. Defaults to "default".
    """
    for package in packages:
        package_name = package.split("==")[0].split("[")[0]  # Handle extras

        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "uninstall", package_name, "-y"]
            )
            modify_requirements(package_name, action="uninstall")
            modify_pyproject_toml(
                package_name,
                action="uninstall",
                hatch_env=hatch_env,
                dependency_group=dependency_group,
            )
            click.echo(f"Successfully uninstalled {package_name}")
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Failed to uninstall {package_name}.", err=True)
            click.echo(f"Reason: {e}", err=True)
            sys.exit(e.returncode)
        except Exception as e:
            click.echo(
                f"Unexpected error occurred while trying to uninstall {package_name}:",
                err=True,
            )
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
        if (
            "tool" in pyproject
            and "hatch" in pyproject["tool"]
            and hatch_env is not None
        ):
            dependencies = (
                pyproject.get("tool", {})
                .get("hatch", {})
                .get("envs", {})
                .get(hatch_env, {})
                .get("dependencies", [])
            )
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

@cli.command("find")
@click.argument("package")
@click.option("--limit", default=5, help="Limit the number of results")
@click.option("--sort", default="downloads", help="Sort key to use")
def find_command(package, limit, sort) -> None:
    """Find a package on PyPI and optionally sort the results.

    Args:
        package (str): The package to search for.
        sort (str, optional): Sort key to use. Defaults to "downloads".
    """
    try:
        packages = find_and_sort(package, limit, sort)
        click.echo("Packages found:")
        print(packages)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command("info")
@click.argument("package")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def info_command(package, verbose) -> None:
    """Get information about a package from PyPI.

    Args:
        package (str): The package to get information about.
    """
    try:
        package_info = get_package_info(package, verbose)
        click.echo("Package info:")
        click.echo(package_info)
        description = package_info.pop("description", " ")
        if verbose:
            for line in description.split("\n"):
                click.echo(line)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
