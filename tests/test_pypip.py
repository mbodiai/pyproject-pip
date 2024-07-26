import pytest
from pyproject_pip.pypip import (
    get_latest_version,
    base_name,
    modify_dependencies,
    is_group,
    process_dependencies,
    search_package,
    find_and_sort
)

def test_get_latest_version():
    assert get_latest_version("pytest") is not None
    # Test with a non-existent package
    assert get_latest_version("non_existent_package_12345") is None

def test_base_name():
    assert base_name("package") == "package"
    assert base_name("package[extra]") == "package"
    assert base_name("package==1.0.0") == "package"

def test_modify_dependencies():
    dependencies = ["package1==1.0.0", "package2==2.0.0"]
    
    # Test install action
    result = modify_dependencies(dependencies, "package3==3.0.0", "install")
    assert "package3==3.0.0" in result
    assert len(result) == 3

    # Test uninstall action
    result = modify_dependencies(dependencies, "package1==1.0.0", "uninstall")
    assert "package1==1.0.0" not in result
    assert len(result) == 1

def test_is_group():
    assert is_group("[group]") is True
    assert is_group("not_a_group") is False
    assert is_group('[group with "quotes"]') is False

def test_process_dependencies():
    output_lines = []
    process_dependencies("dep1, dep2, dep3]", output_lines)
    assert output_lines == ['  dep1,', '  dep2,', '  dep3', '  ]']

    output_lines = []
    process_dependencies("dep1, dep2, dep3", output_lines)
    assert output_lines == ['  dep1,', '  dep2,', '  dep3']

    output_lines = []
    process_dependencies("dep1[extra1,extra2], dep2, dep3", output_lines)
    assert output_lines == ['  dep1[extra1,extra2],', '  dep2,', '  dep3']

    output_lines = []
    process_dependencies("dep1[extra1,extra2], dep2[extra3], dep3", output_lines)
    assert output_lines == ['  dep1[extra1,extra2],', '  dep2[extra3', '  ]', '  dep3']

def test_process_dependencies_multiline():
    output_lines = []
    process_dependencies("dep1,\ndep2,\ndep3", output_lines)
    assert output_lines == ['  dep1,', '  dep2,', '  dep3']

def test_process_dependencies_extras_at_end():
    output_lines = []
    process_dependencies("dep1, dep2[extra1,extra2]", output_lines)
    assert output_lines == ['  dep1,', '  dep2[extra1,extra2],']

def test_process_dependencies_remove_extra_quotes():
    output_lines = []
    process_dependencies('"dep1", "dep2"', output_lines)
    assert output_lines == ['  "dep1",', '  "dep2"']

def test_process_dependencies_trailing_comma():
    output_lines = []
    process_dependencies("dep1, dep2,", output_lines)
    assert output_lines == ['  dep1,', '  dep2,']

def test_search_package():

    # Test with a known package
    package_info = search_package("pytest")
    assert len(package_info["description"]) > 0
    assert len(package_info["details"]) > 0
    assert package_info["github_url"] == "https://github.com/pytest-dev/pytest"

    # Test with a non-existent package
    package_info = search_package("non_existent_package_12345")
    assert package_info == {}

def test_find_and_sort():
    # Test with a valid query key
    packages = find_and_sort("pytest")
    assert isinstance(packages, list)
    assert len(packages) > 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])