#!/bin/bash
set -e

echo "Testing provider configuration..."
output=$(code-agent config openai)
if [[ $output != *"OpenAI"* ]]; then
  echo "❌ Provider config test failed"
  exit 1
fi
echo "✅ Provider config test passed"

# Skip actual API calls in CI unless specifically enabled
if [ "$RUN_PROVIDER_API_TESTS" = "true" ]; then
  echo "Testing OpenAI API (with mock in test mode)..."
  output=$(CODE_AGENT_TEST_MODE=1 code-agent run "What is 2+2?")
  if [[ $output != *"4"* ]]; then
    echo "❌ Basic model response test failed"
    exit 1
  fi
  echo "✅ Basic model response test passed"
else
  echo "Skipping provider API tests (set RUN_PROVIDER_API_TESTS=true to enable)"
fi

exit 0
