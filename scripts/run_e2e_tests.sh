#!/bin/bash
# Simple script to run basic e2e tests from testing.md

set -e  # Exit on any error

# --- Clean up previous memory file ---
rm -f ./.e2e_memory_store.json

# --- Helper Functions ---
assert_output() {
    local output="$1"
    local expected="$2"
    local test_name="$3"
    echo "Asserting output for: $test_name"
    if echo "$output" | grep -q -F -- "$expected"; then
        echo "  [PASS] Output contains '$expected'"
    else
        echo "  [FAIL] Output did not contain '$expected'"
        echo "--- Output ---"
        echo "$output"
        echo "--------------"
        # Optionally exit script on failure: exit 1
        exit 1
    fi
}

# --- Configuration for Memory Service (Modify as needed for persistent tests) ---
export E2E_LOG_LEVEL="INFO" # Set to DEBUG for verbose output

# --- Option 1: Vertex AI RAG (Cloud-based, requires setup) ---
# export ADK_E2E_MEMORY_SERVICE="vertex_ai_rag"
# export ADK_E2E_GCP_PROJECT="your-gcp-project-id"
# export ADK_E2E_GCP_LOCATION="us-central1"
# export ADK_E2E_RAG_CORPUS_ID="your-rag-corpus-id"
# export ADK_E2E_APP_NAME="e2e_vertex_rag_test_app" # Optional: Distinct app name
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json" # Ensure ADC is set up for Vertex AI

# --- Option 2: JSON File (Local, simple persistence) ---
# Uncomment these lines to use the local JSON file for memory persistence
export ADK_E2E_MEMORY_SERVICE="json_file"
export ADK_E2E_JSON_MEMORY_PATH="./.e2e_memory_store.json" # Path relative to workspace root
export ADK_E2E_APP_NAME="e2e_json_file_test_app" # Optional: Distinct app name

# Default remains InMemoryMemoryService if nothing else is configured

# Ensure google-adk[vertexai] is installed if using Vertex AI RAG service
# uv pip install "google-adk[vertexai]"

# --- Test Execution --- Function to run agent command
run_agent_cmd() {
    echo "------------------------------------------------"
    echo "COMMAND: $1"
    echo "------------------------------------------------"
    # Pipe the command (including the \nexit) into the custom runner script
    # Pass the log level to the Python script
    echo -e "$1\nexit" | uv run python scripts/run_e2e.py --log-level="$E2E_LOG_LEVEL"
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
# Run using pytest to execute the test functions within the file
uv run pytest tests/integration/test_memory_integration.py

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

# === Memory Recall Tests (REQUIRES PERSISTENT MEMORY SERVICE) ===
# The following tests invoke the agent multiple times. For memory
# to persist between these runs, you MUST configure and export
# environment variables for a persistent MemoryService (e.g., Vertex AI RAG)
# at the top of this script. Using the default InMemoryMemoryService
# will cause these assertions to FAIL.

echo "================================================"
echo "TEST: Memory Recall - Simple Fact (Requires Persistent Memory)"
echo "================================================"

# Run 1: Store the fact
store_cmd="My favorite language is Python."
echo "Storing fact: $store_cmd"
export ADK_E2E_SESSION_ID="e2e_memory_store_fact_1"
run_agent_cmd "$store_cmd"

# Run 2: Recall the fact
recall_cmd="What did I say my favorite language was?"
echo "Recalling fact: $recall_cmd"
export ADK_E2E_SESSION_ID="e2e_memory_recall_fact_1"
recall_output=$(run_agent_cmd "$recall_cmd")
assert_output "$recall_output" "Python" "Simple Fact Recall"

echo "================================================"
echo "TEST: Memory Recall - File Context (Requires Persistent Memory)"
echo "================================================"

# Ensure sample_code.py exists from previous steps

# Run 1: Discuss the file
store_file_cmd="Read the file sample_code.py"
echo "Storing file context: $store_file_cmd"
export ADK_E2E_SESSION_ID="e2e_memory_store_file_1"
run_agent_cmd "$store_file_cmd"

# Run 2: Ask about the file context
recall_file_cmd="What was the name of the function in the file we just discussed?"
echo "Recalling file context: $recall_file_cmd"
export ADK_E2E_SESSION_ID="e2e_memory_recall_file_1"
recall_file_output=$(run_agent_cmd "$recall_file_cmd")
# Check for the function name 'add' which should be recalled
assert_output "$recall_file_output" "add" "File Context Recall"

# === End Memory Recall Tests ===

echo "================================================"

echo "All end-to-end tests completed!"
