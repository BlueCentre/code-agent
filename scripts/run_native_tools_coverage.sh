#!/bin/bash

# Script to run coverage tests specifically for the native_tools module (using uv)
# This script creates a virtual environment, installs dependencies,
# and runs tests with coverage for the native_tools module

set -e

VENV_DIR=".venv"
echo "Starting coverage pipeline for native_tools module using uv..."

# Check for .env file and load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Ensure uv is available (user should install it: https://github.com/astral-sh/uv)
if ! command -v uv &> /dev/null
then
    echo "Error: uv command not found. Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Create and activate virtual environment using uv
echo "Setting up virtual environment using uv..."
uv venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install required dependencies using uv
echo "Installing dependencies in virtual environment using uv..."
# Use the same command as run_coverage_pipeline_venv.sh for consistency
uv pip install --quiet -e '.[dev]' pytest pytest-cov pytest-mock tomli

# Run tests with coverage specifically for native_tools
echo "Running tests with coverage for native_tools module..."
python -m pytest tests/test_native_tools.py tests/test_native_tools_additional.py -v --cov=code_agent.tools.native_tools --cov-report=term --cov-report=xml --cov-report=html --cov-fail-under=80

# Deactivate virtual environment
deactivate

echo "Coverage pipeline for native_tools module completed successfully!"
