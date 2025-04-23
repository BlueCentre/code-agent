#!/bin/bash

# Run tests with coverage for both code_agent and cli_agent modules
# Usage: ./scripts/run_tests_with_coverage.sh [additional pytest args]

set -e

# Set Python path
export PYTHONPATH=$PWD

# Run tests with coverage
python -m pytest tests/ --cov=code_agent --cov=cli_agent --cov-report=term --cov-report=xml --cov-report=html --cov-fail-under=80 $@

echo "Coverage report generated successfully!"
echo "HTML report available at: htmlcov/index.html" 