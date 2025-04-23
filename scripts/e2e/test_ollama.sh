#!/bin/bash
set -e

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
  echo "Ollama not installed, skipping tests"
  exit 0
fi

# Check if Ollama is running
if ! curl --silent --fail http://localhost:11434/api/tags &> /dev/null; then
  echo "Ollama service not running, skipping tests"
  exit 0
fi

echo "Testing Ollama list command..."
output=$(code-agent ollama list)
if [[ $output != *"Ollama Models"* ]]; then
  echo "❌ Ollama list test failed"
  exit 1
fi
echo "✅ Ollama list test passed"

echo "Testing Ollama list with JSON format..."
output=$(code-agent ollama list --json)
if ! echo "$output" | jq . &> /dev/null; then
  echo "❌ Ollama JSON list test failed"
  exit 1
fi
echo "✅ Ollama JSON list test passed"

exit 0
