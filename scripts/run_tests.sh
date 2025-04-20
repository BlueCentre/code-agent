#!/bin/bash
set -e

# Activate virtual environment if it exists and not already activated
if [ -d ".venv" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest tests/ --cov=code_agent --cov-report=term --cov-report=html --cov-fail-under=80

# Display coverage report
echo -e "\nCoverage report summary:"
python -m coverage report

# Check if we need to show HTML report
if [ "$1" = "--html" ]; then
    echo -e "\nOpening HTML coverage report..."
    open htmlcov/index.html
fi

echo -e "\nTests completed!"
