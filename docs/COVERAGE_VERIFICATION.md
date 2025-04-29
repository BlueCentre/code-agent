# Coverage Verification

This document outlines how code coverage is measured, verified, and reported in this project.

## Setup

### Environment Variables (for SonarCloud)

If you intend to upload results to SonarCloud, create a `.env` file in the project root with your SonarQube token:

```plaintext
SONAR_TOKEN=your_sonar_token_here
```

This token is required by the `sonar-scanner` during the pipeline execution.

## Coverage Configuration

Coverage is configured using the `[tool.coverage.*]` sections in the `pyproject.toml` file, which specify:

- Source directories to measure (`source = ["code_agent"]`)
- Files and patterns to exclude (`omit = [...]`)
- Lines to exclude based on pragmas or patterns (`exclude_lines = [...]`)
- Required minimum coverage threshold (`fail_under = 80`)
- Output formats and locations (e.g., `htmlcov/` for HTML report)

## Running Coverage Locally

Use the provided Makefile targets (UV will automatically use the `.venv` environment):

```bash
# Run tests and check coverage (fails if below threshold)
make test-coverage

# Run tests, check coverage, and open the HTML report
make test-report
```

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

## Troubleshooting

### Missing Coverage Data

If coverage data seems incomplete:
- Ensure all test files are properly named with the `test_` prefix (e.g., `test_my_module.py`).
- Check that tests are importing the correct modules they intend to test.
- Verify that the `--cov=code_agent` parameter (or similar) in the test execution command accurately targets your source code directories.

### SonarQube Scan Failures

If the SonarQube scan (part of the pipeline) fails:
- **Verify Token:** Ensure your `SONAR_TOKEN` is correctly set in the `.env` file (if running locally) or as a CI/CD secret.
- **Check Properties File:** Confirm that the `sonar-project.properties` file exists in the root directory and is properly configured with the correct project key and organization.
- **Check XML Report:** Ensure the `coverage.xml` report was generated successfully by the `pytest --cov` command before the scanner runs. Check the pipeline logs for errors during test execution or report generation.
