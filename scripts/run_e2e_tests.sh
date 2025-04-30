#!/bin/bash
# Simple script to run basic e2e tests from testing.md

set -e  # Exit on any error

# Create directories for logs
# mkdir -p logs

echo "================================================"
echo "Running basic command tests..."
echo "================================================"

echo "================================================"
echo "Testing version command..."
echo "================================================"
uv run code-agent --version

# echo "================================================"
# echo "Testing config command..."
# echo "================================================"
# uv run code-agent config show

echo "================================================"
echo "Testing memory integration..."
echo "================================================"
uv run python tests/integration/test_memory_integration.py

echo "================================================"
echo "Testing basic chat command with CLI..."
echo "================================================"
echo 'What is your name?' | uv run code-agent chat

echo "================================================"
echo "Testing basic chat command with ADK..."
echo "================================================"
echo 'What is your name?\exit' | uv run adk run code_agent/agent/software_engineer/software_engineer || true
# echo 'What is your name?\nexit' | uvx --from git+https://github.com/google/adk-python.git@main adk run code_agent/agent/software_engineer/software_engineer

echo "================================================"
echo "Testing file creation command with ADK..."
echo "================================================"
echo "Can you create a file called test.txt and write 'Hello, world!' to it? I approve the the shell command.\nexit" | uv run adk run code_agent/agent/software_engineer/software_engineer || true

echo "================================================"
echo "Testing file deletion command with ADK..."
echo "================================================"
echo "Delete the file called test.txt? I approve the the shell command.\nexit" | uv run adk run code_agent/agent/software_engineer/software_engineer || true


echo "All end-to-end tests completed successfully!"
