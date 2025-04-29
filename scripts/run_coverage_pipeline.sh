#!/bin/bash

# Script to run coverage pipeline using system-wide Python dependencies
# This script runs tests with coverage and reports to SonarCloud

set -e

echo "Starting coverage pipeline..."

# Check for .env file and load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    # export $(grep -v '^#' .env | xargs)
    source .env
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
uv run pytest --cov=code_agent \
        --cov-config=pyproject.toml \
        --cov-report=xml --cov-report=html --cov-report=term --cov-fail-under=80

# Extract project version
echo "Extracting project version..."
VERSION=$(grep "^version" pyproject.toml | sed -E 's/version = "(.*)"/\1/g')
echo "Project version: $VERSION"

# Get current Git branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Run SonarQube scan if properties file exists
if [ -f sonar-project.properties ]; then
    echo "Running SonarQube scan..."

    if [ -z "$SONAR_TOKEN" ]; then
        echo "Error: SONAR_TOKEN not set. Cannot run SonarQube scan."
        exit 1
    fi

    sonar-scanner \
      -Dsonar.projectVersion=$VERSION \
      -Dsonar.branch.name=$CURRENT_BRANCH \
      -Dsonar.login=$SONAR_TOKEN
else
    echo "No sonar-project.properties file found. Skipping SonarQube scan."
fi

echo "Coverage pipeline completed successfully!"
