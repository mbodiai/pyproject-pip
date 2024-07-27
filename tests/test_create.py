import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, call
from pyproject_pip.create import create_project

@pytest.fixture
def mock_cwd(tmp_path):
    with patch('pyproject_pip.create.getcwd', return_value=str(tmp_path)):
        yield tmp_path

def test_create_project(mock_cwd):
    project_name = "test_project"
    author = "Test Author"
    description = "Test Description"
    deps = ["pytest", "numpy"]

    with patch('pyproject_pip.create.Path.mkdir') as mock_mkdir, \
         patch('pyproject_pip.create.Path.write_text') as mock_write_text, \
         patch('pyproject_pip.create.Path.touch') as mock_touch, \
         patch('pyproject_pip.create.create_pyproject_toml', return_value="mock_pyproject_content") as mock_create_pyproject:

        create_project(project_name, author, description, deps)

        # Check if directories were created
        assert mock_mkdir.call_count == 8  # 5 dirs + 1 for tests
        mock_mkdir.assert_has_calls([
            call(exist_ok=True) for _ in range(7)
        ], any_order=True)

        # Check if files were created with correct content
        assert mock_write_text.call_count == 6  # LICENSE, README.md, pyproject.toml, __about__.py
        mock_write_text.assert_has_calls([
            call(''),  # LICENSE
            call(f'# {project_name}\n\n{description}\n\n## Installation\n\n```bash\npip install {project_name}\n```\n'),  # README.md
            call('mock_pyproject_content'),  # pyproject.toml
            call('__version__ = "0.1.0"')  # __about__.py
        ], any_order=True)

        # Check if __init__.py was touched
        assert mock_touch.call_count == 7

        # Check if create_pyproject_toml was called with correct arguments
        mock_create_pyproject.assert_called_once_with(project_name, author, deps)

def test_create_project_with_local_deps(mock_cwd):
    with patch('pyproject_pip.create.Path.mkdir'), \
         patch('pyproject_pip.create.Path.write_text'), \
         patch('pyproject_pip.create.Path.touch'), \
         patch('pyproject_pip.create.create_pyproject_toml') as mock_create_pyproject:

        create_project("local_project", "Local Author", deps="local")
        mock_create_pyproject.assert_called_once_with("local_project", "Local Author", "local")

def test_create_project_no_deps(mock_cwd):
    with patch('pyproject_pip.create.Path.mkdir'), \
         patch('pyproject_pip.create.Path.write_text'), \
         patch('pyproject_pip.create.Path.touch'), \
         patch('pyproject_pip.create.create_pyproject_toml') as mock_create_pyproject:

        create_project("no_deps_project", "No Deps Author")
        mock_create_pyproject.assert_called_once_with("no_deps_project", "No Deps Author", None)

def test_create_project_existing_directory(mock_cwd):
    with patch('pyproject_pip.create.Path.mkdir') as mock_mkdir, \
         patch('pyproject_pip.create.Path.write_text'), \
         patch('pyproject_pip.create.Path.touch'):

        create_project("existing_project", "Existing Author")
        
        # All mkdir calls should have exist_ok=True
        for call in mock_mkdir.call_args_list:
            assert call[1].get('exist_ok', False) is True