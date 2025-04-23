# Code Coverage Verification

This document explains how to verify code coverage for the project.

## Requirements

- Python 3.8 or higher
- pip package manager
- SonarQube account (for SonarCloud integration)

## Coverage Pipeline Options

The project includes two scripts for running the coverage pipeline:

1. `scripts/run_coverage_pipeline.sh` - Uses system-wide Python dependencies
2. `scripts/run_coverage_pipeline_venv.sh` - Creates and uses a Python virtual environment

## Setup

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
SONAR_TOKEN=your_sonar_token_here
```

This token is required for uploading coverage results to SonarCloud.

## Running Coverage Tests

### Using System Dependencies

```bash
./scripts/run_coverage_pipeline.sh
```

### Using Virtual Environment

```bash
./scripts/run_coverage_pipeline_venv.sh
```

## Understanding Coverage Reports

Both scripts will:

1. Run tests with coverage tracking
2. Generate a terminal report showing coverage percentages
3. Create an XML report (`coverage.xml`) for SonarCloud integration
4. Create an HTML report in the `htmlcov/` directory for detailed inspection

The minimum required coverage is set to 80%. If coverage falls below this threshold, the pipeline will fail.

## Viewing Coverage Reports

- Terminal report: Shows a basic summary during script execution
- HTML report: Open `htmlcov/index.html` in a browser for detailed file-by-file coverage
- SonarCloud: Visit your project dashboard on SonarCloud to see integrated coverage reports

## Troubleshooting

### Missing Coverage Data

If coverage data seems incomplete:
- Ensure all test files are properly named with the `test_` prefix
- Check that tests are importing the correct modules
- Verify that the `--cov=code_agent` parameter matches your module structure

### SonarQube Scan Failures

If the SonarQube scan fails:
- Verify that your `SONAR_TOKEN` is correctly set
- Check that the `sonar-project.properties` file exists and is properly configured
- Ensure the coverage XML report was generated successfully

## Test Coverage Verification

This document provides guidance on how to run tests with proper coverage reporting.

### Common Issues

#### Comma in Coverage Module Parameter

A common issue when running coverage tests is putting a comma after module names, like:

```bash
python -m pytest tests/ --cov=code_agent, --cov-report=term
```

This will cause the coverage tool to generate a warning like:
```
CoverageWarning: Module code_agent was never imported. (module-not-imported)
CoverageWarning: No data was collected. (no-data-collected)
WARNING: Failed to generate report: No data to report.
```

And will result in 0% code coverage.

### Correct Way to Run Coverage Tests

To run tests with proper coverage, use the following formats:

For a single module:
```bash
python -m pytest tests/ --cov=code_agent --cov-report=term
```

For multiple modules:
```bash
python -m pytest tests/ --cov=code_agent --cov=cli_agent --cov-report=term
```

### Using the Coverage Script

For convenience, a script is provided to run tests with coverage:

```bash
./scripts/run_tests_with_coverage.sh
```

This script correctly sets up coverage for both `code_agent` and `cli_agent` modules and generates HTML, XML, and terminal reports.

You can pass additional pytest arguments to the script:

```bash
./scripts/run_tests_with_coverage.sh -v  # For verbose output
./scripts/run_tests_with_coverage.sh -k test_agent  # To run only specific tests
```

**Note:** When running with specific test patterns (using -k), coverage might be below the 80% threshold because you're only testing a subset of the code. To bypass the coverage failure in this case, add `--no-cov-on-fail` to your command:

```bash
./scripts/run_tests_with_coverage.sh -k test_agent_ollama --no-cov-on-fail
```

### Coverage Requirements

The project requires at least 80% test coverage. The coverage check will fail if coverage falls below this threshold.

Current coverage for `code_agent/agent/agent.py` is 86.25% and the overall project coverage is 91.05% (as of the last verification).

### Troubleshooting

If you're seeing unexpectedly low coverage:

1. Make sure your command doesn't have commas between module names
2. Verify that you're using the correct module names (`code_agent` and `cli_agent`)
3. Try using the provided script: `./scripts/run_tests_with_coverage.sh`
4. Check `.coveragerc` for any exclusion patterns that might be affecting your modules
