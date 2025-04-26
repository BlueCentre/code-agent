#!/bin/bash

# Script to set up development environment for code-agent
# Will use UV if available for faster dependency installation, otherwise falls back to Poetry

set -e

echo "Setting up development environment for code-agent..."

# Check if .venv directory exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists in .venv"
fi

# Activate the virtual environment
source .venv/bin/activate

# Check for UV availability
if command -v uv &> /dev/null; then
    echo "UV detected, using it for faster dependency installation"
    uv pip install -e ".[dev]"
else
    echo "Using pip for installation"
    pip install -e ".[dev]"
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

echo ""
echo "Development environment setup complete!"
echo "To activate the environment, run: source .venv/bin/activate"
echo ""
echo "Development Commands:"
echo "  make test         - Run all tests"
echo "  make test-unit    - Run only unit tests"
echo "  make test-coverage - Run tests with coverage report"
echo "  make lint         - Check code style"
echo "  make format       - Format code"
echo ""
echo "If you have UV installed:"
echo "  make uv-test      - Run tests using UV (faster)"
echo "  make uv-lint      - Check code style using UV"
echo "  make uv-format    - Format code using UV" 