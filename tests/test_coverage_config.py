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
