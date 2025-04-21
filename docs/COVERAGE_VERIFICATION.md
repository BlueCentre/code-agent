# Coverage Verification

This document describes how code coverage is verified in the CLI Code Agent project.

## Coverage Requirements

The project requires at least 80% test coverage, as defined in the following configuration files:
- `.coveragerc` - Sets coverage configuration for the Python `coverage` library
- `pyproject.toml` - Includes coverage settings in the `[tool.coverage]` section

## Running Coverage Tests

There are two scripts available to run the coverage pipeline:

1. `scripts/run_coverage_pipeline.sh` - Runs coverage tests using system-wide dependencies
2. `scripts/run_coverage_pipeline_venv.sh` - Runs coverage tests in a virtual environment (recommended)

Both scripts perform the following steps:
- Install necessary dependencies
- Run tests with coverage reporting
- Extract the project version
- Run a SonarQube scan (if configured)

## Version Extraction

The project version is extracted using `scripts/extract_version.sh`, a robust script that:
1. Checks `pyproject.toml` for the version number
2. Falls back to `setup.py` if needed
3. Searches `__init__.py` files for `__version__` variables
4. Provides a sensible default if no version is found

This approach is more reliable than using `importlib.metadata`, which requires the package to be installed and can fail if the package isn't found or properly installed.

## SonarQube Integration

The coverage pipeline integrates with SonarQube for code quality analysis:
- Coverage results are uploaded to SonarQube
- The project version is included in the SonarQube scan
- A SonarQube token must be provided via the `SONAR_TOKEN` environment variable

## Running Coverage Locally

To run coverage tests locally:

```bash
# Run in a virtual environment (recommended)
./scripts/run_coverage_pipeline_venv.sh

# Or using system-wide dependencies
./scripts/run_coverage_pipeline.sh
```

The tests will fail if coverage drops below 80%.

## Coverage Reports

After running the coverage tests, reports will be available in:
- `coverage.xml` - XML format for integration with tools
- Terminal output - A summary of coverage is shown in the console
- `htmlcov/` directory - HTML reports for detailed browsing (if generated)
