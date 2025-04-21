# Coverage Verification

This document explains how test coverage is measured and verified in this project.

## Coverage Requirements

The project aims to maintain at least 80% code coverage for all code in the `code_agent` package. This helps ensure that the codebase is reliable and that most functionality is tested.

## Coverage Pipeline

The coverage pipeline is implemented in the `scripts/run_coverage_pipeline_venv.sh` script, which:

1. Sets up a Python virtual environment
2. Installs all dependencies
3. Runs pytest with coverage reporting
4. Verifies that coverage meets the required threshold (80%)
5. Generates coverage XML report for further analysis
6. Optionally runs SonarQube analysis

## Running the Coverage Pipeline

You can run the coverage pipeline using:

```bash
./scripts/run_coverage_pipeline_venv.sh
```

For environments without virtual environments already set up:

```bash
./scripts/run_coverage_pipeline.sh
```

## Coverage Report Interpretation

The coverage report looks like this:

```
Name                                         Stmts   Miss  Cover
----------------------------------------------------------------
code_agent/__init__.py                           3      0   100%
code_agent/agent/agent.py                      202     82    59%
code_agent/cli/main.py                         350     18    95%
code_agent/config/__init__.py                    2      0   100%
code_agent/config/config.py                    131     20    85%
code_agent/config/settings_based_config.py      92     18    80%
code_agent/config/validation.py                 87      6    93%
code_agent/llm.py                               27      4    85%
code_agent/tools/file_tools.py                 113     10    91%
code_agent/tools/native_tools.py                50     35    30%
code_agent/tools/simple_tools.py               127     19    85%
----------------------------------------------------------------
TOTAL                                         1184    212    82%
```

- **Stmts**: Total number of statements in the file
- **Miss**: Number of statements not covered by tests
- **Cover**: Percentage of statements covered by tests

## Improving Coverage

If coverage falls below the 80% threshold, you can improve it by:

1. Adding tests for uncovered functions and methods
2. Adding tests for error handling paths in existing functions
3. Adding edge case tests (boundary values, invalid inputs, etc.)

Focus on the modules with the lowest coverage percentage first, as they will give the biggest improvement for the least effort.

## Troubleshooting

If tests are failing or coverage is unexpectedly low:

1. Check test imports to ensure they match the current codebase structure
2. Verify that mock objects correctly simulate the behavior of real objects
3. Use `pytest --no-cov -xvs tests/test_specific_file.py::TestClass::test_specific_function` to run failing tests with more detailed output

## CI/CD Integration

Coverage verification is part of the continuous integration pipeline. Pull requests that reduce coverage below the 80% threshold will be flagged for improvement before they can be merged.
