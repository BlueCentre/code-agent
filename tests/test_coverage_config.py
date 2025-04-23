import configparser
import os
from pathlib import Path

import tomli


def test_coverage_includes_all_packages():
    """Ensure that all Python packages are included in all coverage configurations."""
    # Find the project root directory (where .coveragerc is located)
    project_root = Path(__file__).parent.parent

    # Get all top-level directories that contain __init__.py (Python packages)
    python_packages = []
    for item in os.listdir(project_root):
        item_path = project_root / item
        if item_path.is_dir() and not item.startswith(".") and not item == "tests":
            if (item_path / "__init__.py").exists():
                python_packages.append(item)

    # Check .coveragerc file
    config = configparser.ConfigParser()
    config.read(project_root / ".coveragerc")

    # Get the 'source' value from the config
    coverage_sources = [s.strip() for s in config["run"]["source"].split(",")]

    # Check if all Python packages are included in the sources
    missing_in_coverage = [pkg for pkg in python_packages if pkg not in coverage_sources]

    # If there are missing packages, fail the test with an informative message
    assert not missing_in_coverage, f"The following Python packages are not included in .coveragerc: {missing_in_coverage}"

    # Check sonar-project.properties file
    sonar_config_path = project_root / "sonar-project.properties"
    if sonar_config_path.exists():
        sonar_sources = None
        with open(sonar_config_path, "r") as f:
            for line in f:
                if line.startswith("sonar.sources="):
                    sonar_sources = [s.strip() for s in line.replace("sonar.sources=", "").strip().split(",")]
                    break

        if sonar_sources:
            missing_in_sonar = [pkg for pkg in python_packages if pkg not in sonar_sources]
            assert not missing_in_sonar, f"The following Python packages are not included in sonar-project.properties: {missing_in_sonar}"

    # Check pyproject.toml file
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomli.load(f)

            if "tool" in pyproject_data and "coverage" in pyproject_data["tool"] and "run" in pyproject_data["tool"]["coverage"]:
                pyproject_sources = pyproject_data["tool"]["coverage"]["run"].get("source", [])

                missing_in_pyproject = [pkg for pkg in python_packages if pkg not in pyproject_sources]
                assert not missing_in_pyproject, f"The following Python packages are not included in pyproject.toml [tool.coverage.run]: {missing_in_pyproject}"

            # Also check if packages are properly defined in the tool.poetry.packages section
            if "tool" in pyproject_data and "poetry" in pyproject_data["tool"] and "packages" in pyproject_data["tool"]["poetry"]:
                poetry_packages = [pkg.get("include") for pkg in pyproject_data["tool"]["poetry"]["packages"]]

                missing_in_poetry = [pkg for pkg in python_packages if pkg not in poetry_packages]
                assert not missing_in_poetry, f"The following Python packages are not included in pyproject.toml [tool.poetry.packages]: {missing_in_poetry}"

        except Exception as e:
            # If there's an error reading the TOML file, we should report it
            raise AssertionError(f"Error checking pyproject.toml: {e!s}") from e


def test_all_modules_have_tests():
    """Ensure that all Python modules have corresponding test files."""
    # Find the project root directory
    project_root = Path(__file__).parent.parent

    # Get all Python files in the source directories (excluding __init__.py)
    source_files = []
    for pkg_dir in project_root.iterdir():
        if not pkg_dir.is_dir() or pkg_dir.name.startswith(".") or pkg_dir.name in ["tests", "scripts", "venv", ".venv"]:
            continue

        if not (pkg_dir / "__init__.py").exists():
            continue

        # Walk the directory to find all Python files
        for dirpath, _, files in os.walk(pkg_dir):
            root_path = Path(dirpath)
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_path = os.path.relpath(root_path / file, project_root)
                    # Get the base name without .py extension
                    module_name = os.path.splitext(file)[0]
                    source_files.append((module_name, module_path))

    # Get all Python test files
    test_files = []
    test_path = project_root / "tests"
    for _, _, files in os.walk(test_path):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(file)

    # Check if each module has a corresponding test file
    modules_without_tests = []
    for module_name, module_path in source_files:
        # Check if there's a test file that targets this module
        if not any(test.startswith(f"test_{module_name}") for test in test_files):
            modules_without_tests.append(module_path)

    # We use a warning rather than a hard failure, as there might be legitimate cases
    # of modules without direct test files (helpers, utilities, etc.)
    if modules_without_tests:
        print("WARNING: The following modules don't have corresponding test files:")
        for module in modules_without_tests:
            print(f"  - {module}")

        # Check if any excluded modules should actually be tested
        critical_patterns = ["api", "provider", "command", "tool", "model", "client", "service"]
        critical_modules = [m for m in modules_without_tests if any(pattern in m for pattern in critical_patterns)]

        if critical_modules:
            # For critical modules, we do want to fail the test
            assert not critical_modules, f"Critical modules missing tests: {critical_modules}"
