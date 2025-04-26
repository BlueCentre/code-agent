#!/bin/bash
# Script to test file operations as described in testing.md

set -e  # Exit on any error

echo "Running file operation tests..."

# Create a test file
echo "Creating test file..."
echo "This is a test file content" > test_file.txt

# Test reading the file
echo "Testing reading a file..."
code-agent run "Show me the contents of test_file.txt"

# Test creating a new file
echo "Testing creating a new file..."
code-agent run "Create a new file called hello.py with a simple Hello World program"

# Check if the file was created
if [ -f "hello.py" ]; then
  echo "Successfully created hello.py"
  cat hello.py
else
  echo "Failed to create hello.py"
fi

# Test editing an existing file
echo "Testing editing an existing file..."
code-agent run "Add a docstring to hello.py if it exists"

# Clean up test files
echo "Cleaning up test files..."
rm -f test_file.txt hello.py

echo "File operation tests completed!" 