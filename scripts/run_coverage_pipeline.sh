#!/bin/bash
set -e

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
  echo "Loading environment variables from .env file"
  set -a # automatically export all variables
  source .env
  set +a
fi

echo "======= Installing dependencies ======="
poetry config virtualenvs.create false
poetry install --no-interaction
python -m pip install --upgrade pip pytest pytest-cov

echo "======= Running tests with coverage ======="
python -m pytest tests/ --cov=code_agent --cov-report=xml --cov-report=term --cov-fail-under=80

echo "======= Extracting version ======="
VERSION=$(python -c "from importlib.metadata import version; print(version('cli-code-agent'))")
echo "PROJECT_VERSION=$VERSION"
echo "Extracted version: $VERSION"

echo "======= Running SonarQube scan ======="
# Install sonar-scanner if needed
# apt-get install sonar-scanner or equivalent for your OS

# Set default to SonarCloud
SONAR_HOST_URL=${SONAR_HOST_URL:-"https://sonarcloud.io"}
SONAR_PROPERTIES=${SONAR_PROPERTIES:-"sonar-project.properties"}

# Check if properties file exists
if [ ! -f "$SONAR_PROPERTIES" ]; then
  echo "Error: Properties file $SONAR_PROPERTIES not found!"
  exit 1
fi

# Run the scanner with the properties file and additional parameters
if [ -z "$SONAR_TOKEN" ]; then
  echo "Warning: SONAR_TOKEN not set. SonarQube scan will not be performed."
  echo "Set the SONAR_TOKEN environment variable to run the scan."
  echo "Example: export SONAR_TOKEN=your_token_here"
else
  echo "Running sonar-scanner with properties file: $SONAR_PROPERTIES"
  sonar-scanner \
    -Dproject.settings=$SONAR_PROPERTIES \
    -Dsonar.projectVersion=$VERSION \
    -Dsonar.host.url=$SONAR_HOST_URL \
    -Dsonar.login=$SONAR_TOKEN
fi

echo "======= Pipeline complete ======="
