#!/bin/bash
set -e

# Enable debug output if DEBUG=1 is set
if [ "${DEBUG}" = "1" ]; then
    set -x
fi

# Determine script directory for better path handling
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "Running from directory: $(pwd)"

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
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        open htmlcov/index.html
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        # Linux
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open htmlcov/index.html
        else
            echo "Cannot open HTML report: xdg-open not found"
        fi
    else
        echo "Cannot open HTML report: Unsupported platform"
    fi
fi

echo -e "\nTests completed!"
