#!/bin/bash

# Script to run coverage pipeline using system-wide Python dependencies
# This script runs tests with coverage and reports to SonarCloud

set -e

echo "Starting coverage pipeline..."

# Check for .env file and load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
fi

# Ensure uv is available (user should install it: https://github.com/astral-sh/uv)
if ! command -v uv &> /dev/null
then
    echo "ERROR: uv command not found!"
    exit 1
else
    echo "Installing dependencies using uv..."
    # Install required dependencies using uv
    uv sync --all-extras --dev
fi

# Run tests with coverage
echo "Running tests with coverage..."
uv run python -m pytest tests/ --cov=code_agent --cov-report=term --cov-report=xml --cov-report=html --cov-fail-under=80

# Extract project version
echo "Extracting project version..."
VERSION=$(grep "^version" pyproject.toml | sed -E 's/version = "(.*)"/\1/g')
echo "Project version: $VERSION"

# Run SonarQube scan if properties file exists
if [ -f sonar-project.properties ]; then
    echo "Running SonarQube scan..."

    if [ -z "$SONAR_TOKEN" ]; then
        echo "Error: SONAR_TOKEN not set. Cannot run SonarQube scan."
        exit 1
    fi

    sonar-scanner \
      -Dsonar.projectVersion=$VERSION \
      -Dsonar.login=$SONAR_TOKEN
else
    echo "No sonar-project.properties file found. Skipping SonarQube scan."
fi

echo "Coverage pipeline completed successfully!"
