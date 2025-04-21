# Coverage Verification

This document outlines how code coverage is measured, verified, and reported in this project.

## Coverage Configuration

Coverage is configured using the `.coveragerc` file in the project root, which specifies:

- Source directories to measure
- Files and patterns to exclude
- Required minimum coverage threshold (80%)
- Output formats and locations

## Running Coverage Locally

### Using System Python

To run coverage with system-wide Python dependencies:

```bash
./scripts/run_coverage_pipeline.sh
```

### Using Virtual Environment

To run coverage within a Python virtual environment:

```bash
./scripts/run_coverage_pipeline_venv.sh
```

### Running Coverage for Specific Modules

To run coverage tests for the `native_tools` module only:

```bash
./scripts/run_native_tools_coverage.sh
```

This script runs tests specifically for the `native_tools.py` module and verifies that it meets the 80% coverage threshold.

## Coverage Pipeline

The coverage pipeline performs the following steps:

1. Sets up the environment (system Python or virtual environment)
2. Installs required dependencies (`pytest`, `pytest-cov`)
3. Runs tests with coverage options:
   - Measures coverage for the `code_agent` package
   - Generates reports in terminal, XML, and HTML formats
   - Enforces minimum coverage threshold of 80%
4. Extracts project version from `pyproject.toml`
5. Runs SonarQube scan if configured (requires `SONAR_TOKEN` environment variable)

## SonarCloud Integration

Coverage results are reported to SonarCloud using the `sonar-scanner` tool. The scan uses:

- Coverage data from the generated `coverage.xml` file
- Project configuration from `sonar-project.properties`
- Authentication via the `SONAR_TOKEN` environment variable

## Improving Coverage

To improve coverage:

1. Identify code with insufficient coverage using:
   - HTML report in the `htmlcov` directory
   - SonarCloud dashboard
2. Write additional tests focusing on uncovered code paths
3. Run the coverage pipeline to verify improvements

## CI/CD Integration

Coverage verification is integrated into CI/CD workflows to ensure:

- New code meets minimum coverage requirements
- Overall project coverage does not decrease
- Coverage results are tracked over time
