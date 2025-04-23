#!/bin/bash

# Run tests with coverage for both code_agent and cli_agent modules
# Usage: ./scripts/run_tests_with_coverage.sh [additional pytest args]
#
# Environment variables:
#   NO_COV_FAIL=1    # Add --no-cov-on-fail flag to bypass coverage failures

set -e

# Set Python path
export PYTHONPATH=$PWD

# Set coverage options
COV_OPTS="--cov=code_agent --cov=cli_agent --cov-report=term --cov-report=xml --cov-report=html --cov-fail-under=80"

# Add --no-cov-on-fail if requested
if [ "${NO_COV_FAIL}" = "1" ]; then
    COV_OPTS="${COV_OPTS} --no-cov-on-fail"
    echo "Running with --no-cov-on-fail to bypass coverage failures"
fi

# Run tests with coverage
python -m pytest tests/ ${COV_OPTS} $@

echo "Coverage report generated successfully!"
echo "HTML report available at: htmlcov/index.html"
