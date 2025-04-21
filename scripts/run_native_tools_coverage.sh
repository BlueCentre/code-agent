#!/bin/bash

# Script to run coverage tests specifically for the native_tools module
# This script creates a virtual environment, installs dependencies,
# and runs tests with coverage for the native_tools module

set -e

VENV_DIR=".venv"
echo "Starting coverage pipeline for native_tools module..."

# Check for .env file and load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Create and activate virtual environment
echo "Setting up virtual environment..."
python -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install required dependencies
echo "Installing dependencies in virtual environment..."
pip install --quiet --upgrade pip
pip install --quiet pytest pytest-cov
pip install --quiet -e .

# Run tests with coverage specifically for native_tools
echo "Running tests with coverage for native_tools module..."
python -m pytest tests/test_native_tools.py tests/test_native_tools_additional.py -v --cov=code_agent.tools.native_tools --cov-report=term --cov-report=xml --cov-report=html --cov-fail-under=80

# Deactivate virtual environment
deactivate

echo "Coverage pipeline for native_tools module completed successfully!"
