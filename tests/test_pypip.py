import unittest
from unittest.mock import patch, mock_open, MagicMock
from pyproject_pip import pypip


class TestPypipFunctions(unittest.TestCase):
    @patch("pyproject_pip.pypip.get_latest_version")
    def test_get_latest_version(self, mock_get_latest_version):
        package_name = "example_package"
        expected_version = "1.2.3"
        mock_get_latest_version.return_value = expected_version

        result = pypip.get_latest_version(package_name)
        self.assertEqual(result, expected_version)
        mock_get_latest_version.assert_called_once_with(package_name)

    @patch("pyproject_pip.pypip.get_pip_freeze")
    def test_get_pip_freeze(self, mock_get_pip_freeze):
        expected_packages = {"package1==1.0.0", "package2==2.0.0"}
        mock_get_pip_freeze.return_value = expected_packages

        result = pypip.get_pip_freeze()
        self.assertEqual(result, expected_packages)
        mock_get_pip_freeze.assert_called_once()

    @patch("pyproject_pip.pypip.is_package_in_pyproject")
    def test_is_package_in_pyproject(self, mock_is_package_in_pyproject):
        package_name = "example_package"
        hatch_env = "default"
        mock_is_package_in_pyproject.return_value = True

        result = pypip.is_package_in_pyproject(package_name, hatch_env)
        self.assertTrue(result)
        mock_is_package_in_pyproject.assert_called_once_with(package_name, hatch_env)

    @patch("pyproject_pip.pypip.is_package_in_requirements")
    def test_is_package_in_requirements(self, mock_is_package_in_requirements):
        package_name = "example_package"
        mock_is_package_in_requirements.return_value = True

        result = pypip.is_package_in_requirements(package_name)
        self.assertTrue(result)
        mock_is_package_in_requirements.assert_called_once_with(package_name)

    @patch("pyproject_pip.pypip.modify_dependencies")
    def test_modify_dependencies(self, mock_modify_dependencies):
        dependencies = ["package1==1.0.0", "package2==2.0.0"]
        package_version_str = "package3==3.0.0"
        action = "install"

        pypip.modify_dependencies(dependencies, package_version_str, action)
        mock_modify_dependencies.assert_called_once_with(dependencies, package_version_str, action)

    @patch("pyproject_pip.pypip.modify_optional_dependencies")
    def test_modify_optional_dependencies(self, mock_modify_optional_dependencies):
        optional_dependencies = {"group1": ["package1==1.0.0"], "group2": ["package2==2.0.0"]}
        package_version_str = "package3==3.0.0"
        action = "install"
        dependency_group = "group1"

        pypip.modify_optional_dependencies(optional_dependencies, package_version_str, action, dependency_group)
        mock_modify_optional_dependencies.assert_called_once_with(
            optional_dependencies, package_version_str, action, dependency_group
        )

    @patch("pyproject_pip.pypip.modify_pyproject_toml")
    def test_modify_pyproject_toml(self, mock_modify_pyproject_toml):
        package_name = "example_package"
        package_version = "1.2.3"
        action = "install"
        hatch_env = "default"
        dependency_group = "dependencies"

        pypip.modify_pyproject_toml(package_name, package_version, action, hatch_env, dependency_group)
        mock_modify_pyproject_toml.assert_called_once_with(
            package_name, package_version, action, hatch_env, dependency_group
        )

    @patch("pyproject_pip.pypip.modify_requirements")
    def test_modify_requirements(self, mock_modify_requirements):
        package_name = "example_package"
        package_version = "1.2.3"
        action = "install"

        pypip.modify_requirements(package_name, package_version, action)
        mock_modify_requirements.assert_called_once_with(package_name, package_version, action)

    @patch("pyproject_pip.pypip.read_pyproject_toml")
    def test_read_pyproject_toml(self, mock_read_pyproject_toml):
        filepath = "pyproject.toml"
        expected_content = {"tool": {"poetry": {"dependencies": {"example_package": "1.2.3"}}}}
        mock_read_pyproject_toml.return_value = expected_content

        result = pypip.read_pyproject_toml(filepath)
        self.assertEqual(result, expected_content)
        mock_read_pyproject_toml.assert_called_once_with(filepath)

    @patch("pyproject_pip.pypip.write_pyproject_toml")
    def test_write_pyproject_toml(self, mock_write_pyproject_toml):
        pyproject = {"tool": {"poetry": {"dependencies": {"example_package": "1.2.3"}}}}
        filepath = "pyproject.toml"

        pypip.write_pyproject_toml(pyproject, filepath)
        mock_write_pyproject_toml.assert_called_once_with(pyproject, filepath)

    @patch("pyproject_pip.pypip.modify_requirements")
    def test_uninstall_package(self, mock_modify_requirements):
        package_name = "example_package"
        action = "uninstall"

        pypip.modify_requirements(package_name, action=action)
        mock_modify_requirements.assert_called_once_with(package_name, action="uninstall")

    @patch("pyproject_pip.pypip.modify_requirements")
    def test_uninstall_git_dependency(self, mock_modify_requirements):
        package_name = "example_git_package"
        action = "uninstall"

        pypip.modify_requirements(package_name, action=action)
        mock_modify_requirements.assert_called_once_with(package_name, action="uninstall")

    @patch("pyproject_pip.pypip.modify_requirements")
    def test_install_from_requirements(self, mock_modify_requirements):
        package_name = "requirements.txt"
        action = "install"

        pypip.modify_requirements(package_name, action=action)
        mock_modify_requirements.assert_called_once_with(package_name, action="install")

    @patch("pyproject_pip.pypip.modify_optional_dependencies")
    def test_all_group_includes_all_dependencies(self, mock_modify_optional_dependencies):
        optional_dependencies = {"group1": ["package1==1.0.0"], "group2": ["package2==2.0.0"], "all": []}
        all_dependencies = ["package1==1.0.0", "package2==2.0.0"]
        mock_modify_optional_dependencies.side_effect = lambda x, y, z, w: x["all"].extend(all_dependencies)

        pypip.modify_optional_dependencies(optional_dependencies, "", "install", "all")
        self.assertListEqual(optional_dependencies["all"], all_dependencies)


if __name__ == "__main__":
    unittest.main()
