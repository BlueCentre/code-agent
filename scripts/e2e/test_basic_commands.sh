#!/bin/bash
set -e

echo "Testing version command..."
output=$(code-agent --version)
if [[ $output != *"version"* ]]; then
  echo "❌ Version test failed"
  exit 1
fi
echo "✅ Version test passed"

echo "Testing help command..."
output=$(code-agent --help)
if [[ $output != *"CLI agent"* ]]; then
  echo "❌ Help test failed"
  exit 1
fi
echo "✅ Help test passed"

echo "Testing config show command..."
output=$(code-agent config show)
if [[ $output != *"Configuration"* ]]; then
  echo "❌ Config show test failed"
  exit 1
fi
echo "✅ Config show test passed"

exit 0
