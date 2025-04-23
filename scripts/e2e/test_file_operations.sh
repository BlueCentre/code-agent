#!/bin/bash
set -e

# Create a test file
echo "Creating test file..."
echo "Test content" > test_e2e_file.txt

# Verify file was created correctly
if [ ! -f "test_e2e_file.txt" ]; then
  echo "❌ Failed to create test file"
  exit 1
fi

echo "Test file content:"
cat test_e2e_file.txt

# Test file reading (test mode)
echo "Testing file reading..."
output=$(CODE_AGENT_TEST_MODE=1 code-agent run "Show me the contents of test_e2e_file.txt")
echo "Command output:"
echo "$output"

if [[ $output != *"Test content"* ]]; then
  echo "❌ File reading test failed - 'Test content' not found in output"
  # Continue with test but record failure for logging
  test_failed=1
else
  echo "✅ File reading test passed"
fi

# Clean up
rm -f test_e2e_file.txt

# Exit with appropriate code
if [ "$test_failed" = "1" ]; then
  exit 1
fi
exit 0
