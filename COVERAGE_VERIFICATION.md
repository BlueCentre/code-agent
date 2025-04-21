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
