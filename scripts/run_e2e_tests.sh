#!/bin/bash
# Simple script to run basic e2e tests from testing.md

set -e  # Exit on any error

# Function to run agent command
run_agent_cmd() {
    echo "------------------------------------------------"
    echo "COMMAND: $1"
    echo "------------------------------------------------"
    # Pipe the command (including the \nexit) into the adk runner
    # Use || true to continue script even if the agent interaction fails
    echo -e "$1\nexit" | uv run adk run code_agent/agent/software_engineer/software_engineer || true
    echo "================================================"
    # Add a small delay to allow logs to flush if needed
    sleep 1
}


echo "================================================"
echo "Running basic command tests..."
echo "================================================"

echo "================================================"
echo "Testing version command..."
echo "================================================"
uv run code-agent --version

echo "================================================"
echo "Testing memory integration..."
echo "================================================"
uv run python tests/integration/test_memory_integration.py

# echo "================================================"
echo "Testing basic chat command with ADK..."
echo "================================================"
run_agent_cmd 'What is your name?'

# --- New Test Cases ---

# Passed
echo "================================================"
echo "SETUP: Creating a sample Python file..."
echo "================================================"
run_agent_cmd "Create a simple python file named sample_code.py with just a function 'def add(a, b): return a + b'. I approve creating the file."

# Passed
echo "================================================"
echo "TEST: Code Review Delegation & File Reading"
echo "================================================"
run_agent_cmd 'Can you review the code in sample_code.py and give me a summary of the code quality please?'

# Passed
echo "================================================"
echo "TEST: Testing Agent - Test Generation & File Write"
echo "================================================"
run_agent_cmd "Generate a basic pytest test function for the add function in sample_code.py and save it to a new file named test_sample.py. I approve writing the file."

# Passed
echo "================================================"
echo "TEST: Documentation Agent - Docstring Generation & In-place Edit"
echo "================================================"
run_agent_cmd "Add a standard Python docstring to the 'add' function in sample_code.py explaining what it does. I approve editing the file."

# Passed, but improve reponse format?
echo "================================================"
echo "TEST: Debugging Agent - Conceptual Analysis"
echo "================================================"
run_agent_cmd "I'm getting a TypeError if I call the add function in sample_code.py with strings like add('hello', 'world'). How could I fix the function to handle numbers only or raise a specific error?"

# Passed
echo "================================================"
echo "TEST: Design Pattern Agent - Conceptual Suggestion"
echo "================================================"
run_agent_cmd "Considering the 'add' function in sample_code.py, if this module grew much larger with many similar arithmetic functions, what design patterns might help organize it?"

# Passed, but on the 2nd run because of pending approval
echo "================================================"
echo "TEST: DevOps Agent - Dockerfile Generation"
echo "================================================"
run_agent_cmd "Create a very basic Dockerfile that could run a simple Python script, perhaps assuming python:3.11-slim as a base. Name it Dockerfile. I approve creating the file."

# Does not fail, but it does not meet the expectation
echo "================================================"
echo "TEST: Shell Command via Sub-Agent (Code Review + Flake8)"
echo "================================================"
# This assumes flake8 is installed in the environment where the agent runs
# Tests check_command_exists, check_shell_command_safety, execute_vetted_shell_command
run_agent_cmd "Can you run flake8 on sample_code.py to check for style issues? I approve running the command if needed."

echo "================================================"
echo "CLEANUP: Removing generated test files..."
echo "================================================"
# Use standard rm, potentially run via agent if testing deletion itself
rm -f sample_code.py test_sample.py Dockerfile || echo "Cleanup: No files to remove or error during removal."

echo "All end-to-end tests completed!"
