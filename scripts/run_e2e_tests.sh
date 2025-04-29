#!/bin/bash
# Simple script to run basic e2e tests from testing.md

set -e  # Exit on any error

# Create directories for logs
mkdir -p logs

echo "Running basic command tests..."

# Test version command
echo "Testing version command..."
code-agent --version

# Test basic run command
echo "Testing basic run command..."
code-agent run "What is your name?"

# Test config command
echo "Testing config command..."
code-agent config show

# Test memory integration
echo "Testing memory integration..."
python tests/integration/test_memory_integration.py

echo "All end-to-end tests completed successfully!"
