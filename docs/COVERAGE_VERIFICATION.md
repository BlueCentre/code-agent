# Coverage Pipeline Verification

This document explains how to manually verify the test coverage pipeline that runs in GitHub Actions.

## Prerequisites

1. Python 3.10+
2. Poetry
3. For SonarQube scanning (optional):
   - SonarQube/SonarCloud account
   - SonarScanner CLI tool
   - API token for SonarCloud or your SonarQube instance

## Steps to Run the Pipeline

### Option 1: System-wide Dependencies

1. Make sure you're in the project root directory
2. Run the script: `./scripts/run_coverage_pipeline.sh`

### Option 2: Using Virtual Environment (Recommended)

1. Make sure you're in the project root directory
2. Run the script: `./scripts/run_coverage_pipeline_venv.sh`
3. This will create a `.venv` directory and install all dependencies there

## What the Scripts Do

Both scripts replicate the GitHub Actions workflow steps:

1. **Install Dependencies**: Uses Poetry to install project dependencies
2. **Run Tests with Coverage**: Runs pytest with coverage reporting
   - Generates XML report for SonarQube
   - Shows terminal report for quick feedback
   - Enforces 80% minimum coverage
3. **Extract Version**: Gets the package version using importlib.metadata
4. **SonarQube Scan**: Uses settings from sonar-project.properties file

## Configuring SonarQube

By default, the scripts are configured to use SonarCloud. To run the scan:

1. Set your SonarCloud API token using one of these methods:

   **Option A**: Using environment variable:
   ```bash
   export SONAR_TOKEN=your-token-here
   ```

   **Option B**: Using a .env file:
   ```
   # .env file in project root
   SONAR_TOKEN=your-token-here
   ```

2. Run one of the pipeline scripts:
   ```bash
   ./scripts/run_coverage_pipeline_venv.sh
   ```

### Custom Configuration Options

You can customize the SonarQube scan by setting these environment variables (either directly or in .env):

- `SONAR_HOST_URL`: Override the default SonarCloud URL
  ```bash
  # For SonarCloud (default)
  SONAR_HOST_URL=https://sonarcloud.io

  # For self-hosted SonarQube
  SONAR_HOST_URL=http://your-sonarqube-server:9000
  ```

- `SONAR_PROPERTIES`: Specify a custom properties file
  ```bash
  SONAR_PROPERTIES=path/to/custom-sonar.properties
  ```

## Verifying Results

- **Coverage Report**: Check the terminal output for coverage percentage
- **XML Report**: The file `coverage.xml` will be generated for SonarQube
- **SonarQube Dashboard**: If configured, check your SonarCloud (or SonarQube instance) for the uploaded results

## Troubleshooting

- If the version extraction fails, make sure the package is properly installed
- For SonarQube issues, verify your connection settings and token permissions
- If the scan fails, check that sonar-scanner is installed and in your PATH
