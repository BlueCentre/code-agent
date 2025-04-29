# Code Agent Testing Guide

This document provides comprehensive guidance on testing the Code Agent CLI application, including general end-to-end testing procedures and historical test records.

## Table of Contents
- [Introduction](#introduction)
- [End-to-End Testing Guide](#end-to-end-testing-guide)
  - [Basic Test Examples](#basic-test-examples)
  - [Testing File Operations](#testing-file-operations)
  - [Testing Shell Commands](#testing-shell-commands)
  - [Testing Google Search Functionality](#testing-google-search-functionality)
  - [Testing Memory Functionality](#testing-memory-functionality)
  - [Testing Error Handling](#testing-error-handling)
  - [Testing Configuration](#testing-configuration)
- [Automated End-to-End Testing](#automated-end-to-end-testing)
- [Comprehensive Test Scenarios](#comprehensive-test-scenarios)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Continuous Integration](#continuous-integration)
- [Recommended Test Scenarios](#recommended-test-scenarios)
- [Historical Test Records](#historical-test-records)
  - [Gemini 2.0 Migration Testing](#gemini-20-migration-testing)

## Introduction

End-to-end testing validates the entire application workflow from user input to output, ensuring that all components work together correctly. This document provides guidance on performing various types of tests for the Code Agent CLI.

## End-to-End Testing Guide

### Basic Test Examples

#### Testing the `chat` Command

Test basic chat functionality with piped input:

```bash
# Test single interaction and exit
echo "Tell me a joke?" | uv run code-agent chat

# Test multiple interactions and exit
echo "What is Python?\nWhat is a list in Python?" | uv run code-agent chat

# Test with system commands
echo "List files in this directory\nexit" | uv run code-agent chat

# Test special commands in chat
echo "What is your name?\n/help\n/clear\nTell me another joke\n/exit" | uv run code-agent chat
```

#### Testing the `run` Command

Test single prompt processing:

```bash
# Basic question
uv run code-agent run "What is your name?"

# Code-related query
uv run code-agent run "Write a Python function to check if a string is a palindrome"

# Using with different providers
uv run code-agent --provider openai run "Explain quantum computing in simple terms"
uv run code-agent --provider groq --model llama3-70b-8192 run "Write a Dockerfile for a Node.js app"
uv run code-agent --provider anthropic run "Compare Python and JavaScript for web development"
```

#### Testing Ollama Commands

Test integration with local Ollama models:

```bash
# List available models
uv run code-agent ollama list

# List models in JSON format
uv run code-agent ollama list --json

# Run command with a local model
uv run code-agent ollama run llama3 "Tell me a short joke"

# Chat with system prompt
uv run code-agent ollama chat codellama:13b "Write a sorting algorithm" --system "You are a helpful coding assistant"
```

### Testing File Operations

Test file reading and editing capabilities:

```bash
# Read a file
uv run code-agent run "Show me the contents of README.md"

# Create a new file
uv run code-agent run "Create a new file called hello.py with a simple Hello World program"

# Edit an existing file
uv run code-agent run "Add a docstring to hello.py"

# Test path validation
uv run code-agent run "Try to read a file outside the workspace like /etc/passwd"

# Test large file handling
uv run code-agent run "Create a large test file with 10,000 lines of text"
uv run code-agent run "Read the first 50 lines of the large test file"

# Test file operation with auto-approve
uv run code-agent --auto-approve-edits run "Create a file named autotest.py with a simple hello world function"
```

### Testing Shell Commands

Test executing shell commands through the agent:

```bash
# Directory listing
uv run code-agent run "List all files in the current directory"

# System information
uv run code-agent run "Show system information"

# Git operations
uv run code-agent run "Show git status of this repository"

# Test command allowlist functionality
uv run code-agent run "Run 'ls -la' to list files"  # Should be allowlisted

# Test dangerous command protection
uv run code-agent run "Run 'rm -rf /'"  # Should be blocked by security

# Test with working directory parameter
uv run code-agent run "Run 'pwd' in the /tmp directory"

# Test command with auto-approve flag
uv run code-agent --auto-approve-native-commands run "List all processes running on this machine"
```

### Testing Google Search Functionality

Test the agent's ability to search the web for information:

```bash
# Basic Google search
uv run code-agent run "What is the current weather in London?"

# Technical documentation search
uv run code-agent run "Find the documentation for Python's requests library and summarize the key features"

# Current events search
uv run code-agent run "What were the major tech announcements in the last month?"

# Combined search and local operation
uv run code-agent run "Search for best Python logging practices and create a logging_example.py file implementing them"

# Test complex search queries
uv run code-agent run "Find information about 'generative AI agent architectures' and summarize the key approaches"

# Test search with follow-up analysis
uv run code-agent run "Search for information about Python's asyncio library and explain how it relates to our codebase"
```

### Testing Memory Functionality

Test the agent's ability to store and retrieve information across sessions using the memory system:

```bash
# Test storing and retrieving information within the same session
echo "My name is Alex and I'm working on a Python project.\nWhat was my name again?\nexit" | uv run code-agent chat

# Test storing and retrieving information across multiple sessions
# Session 1: Store information
echo "My favorite programming language is Rust.\nexit" | uv run code-agent chat
# Session 2: Retrieve information
echo "What was my favorite programming language?\nexit" | uv run code-agent chat

# Test memory with specific queries
uv run code-agent run "Remember that my team is working on Project Phoenix"
uv run code-agent run "What project was my team working on?"

# Test memory with technical information
uv run code-agent run "The API endpoint for our service is https://api.example.com/v2/data"
uv run code-agent run "What was our API endpoint?"

# Test memory with complex, multi-turn dialog
echo "I need to install TensorFlow version 2.10.\nWhat version of CUDA is compatible with that?\nOK please note that for my documentation.\nWhat was the TensorFlow version I wanted to install?\nexit" | uv run code-agent chat
```

#### Testing Memory Integration with Other Tools

Test how memory works in combination with other agent capabilities:

```bash
# Test memory + file operations
uv run code-agent run "Create a file called project_notes.md with the text 'Project Phoenix starts on January 15, 2025'"
uv run code-agent run "When does Project Phoenix start? Include this information in your answer."

# Test memory + web search
uv run code-agent run "The latest version of PyTorch is 2.1.0"
uv run code-agent run "Compare the version of PyTorch I mentioned earlier with the current latest release"

# Test memory in problem-solving context
echo "I'm having an issue with my Dockerfile where the build fails with error 'standard_init_linux.go:228: exec user process caused: no such file or directory'\nHow can I fix this?\nThanks! I'll try that. If I encounter this issue again, what was the solution?\nexit" | uv run code-agent chat
```

#### Testing Memory Persistence

Test the persistence and durability of memory:

```bash
# Test memory persistence across process restarts (note: InMemoryMemoryService doesn't persist across process restarts)
uv run code-agent run "Remember that my database password is DB_PASSWORD_123"
# Restart the uv run code-agent process
uv run code-agent run "What was my database password?" # Should not remember with InMemoryMemoryService

# Test memory with different users
CODE_AGENT_USER=user1 uv run code-agent run "My name is Alice"
CODE_AGENT_USER=user2 uv run code-agent run "My name is Bob"
CODE_AGENT_USER=user1 uv run code-agent run "What is my name?" # Should respond with Alice
CODE_AGENT_USER=user2 uv run code-agent run "What is my name?" # Should respond with Bob
```

### Testing Error Handling

Test how the application handles errors:

```bash
# Invalid provider
uv run code-agent --provider invalid_provider run "Hello"

# Non-existent model
uv run code-agent --provider openai --model nonexistent_model run "Hello"

# Missing API keys
OPENAI_API_KEY="" uv run code-agent --provider openai run "Hello"

# Reading non-existent file
uv run code-agent run "Show me the contents of non_existent_file.txt"

# Connection errors (can be simulated by disconnecting from network)
uv run code-agent run "What is the current exchange rate between USD and EUR?"

# Path traversal attempts
uv run code-agent run "Read the file at ../../../etc/passwd"

# Recovery from errors
uv run code-agent run "Try to read a non-existent file, then create it if it doesn't exist"
```

### Testing Configuration

Test configuration management:

```bash
# Show current configuration
uv run code-agent config show

# Provider-specific configuration
uv run code-agent config openai
uv run code-agent config ollama

# Test configuration reset
uv run code-agent config reset
uv run code-agent config show

# Test verbosity settings
uv run code-agent --verbosity 3 run "Run with debug verbosity"

# Test configuration via environment variables
AI_STUDIO_API_KEY="test_key" uv run code-agent config show
```

## Automated End-to-End Testing

For automated testing, create shell scripts that run various commands and check the output:

```bash
#!/bin/bash
# Example automated end-to-end test script

# Test version command
output=$(uv run code-agent --version)
if [[ $output != *"Code Agent version"* ]]; then
  echo "Version test failed"
  exit 1
fi

# Test help command
output=$(uv run code-agent --help)
if [[ $output != *"CLI agent for interacting with"* ]]; then
  echo "Help test failed"
  exit 1
fi

# Test simple run command with mock response
output=$(echo "What is 2+2?" | CODE_AGENT_TEST_MODE=1 uv run code-agent chat)
if [[ $output != *"4"* ]]; then
  echo "Simple math test failed"
  exit 1
fi

echo "All tests passed!"
```

## Comprehensive Test Scenarios

### Multi-Turn Conversation Test

```bash
# Create a test script for multi-turn conversational flow
cat > test_conversation.txt << EOL
What files are in this project?
What Python modules are imported in code_agent/agent/agent.py?
Create a summary of the main classes and their relationships in this codebase
exit
EOL

# Run the test
cat test_conversation.txt | uv run code-agent chat
```

### Tool Chaining Test

```bash
# Test complex reasoning with multiple tool steps
uv run code-agent run "Analyze the code in the code_agent/tools directory, identify all functions, and create a markdown report with a table listing each function name, its purpose, and parameter list"
```

### Integration with Development Workflow Test

```bash
# Test code generation
uv run code-agent run "Create a Python script that uses argparse to handle CLI arguments for a simple file conversion tool"

# Test code review capabilities
uv run code-agent run "Review the code in code_agent/tools/security.py and suggest improvements"

# Test documentation generation
uv run code-agent run "Generate API documentation for the functions in code_agent/tools/simple_tools.py"
```

### Comprehensive End-to-End Workflow Test Script

```bash
#!/bin/bash
# e2e_test.sh - Comprehensive workflow test

set -e  # Exit on any error

echo "Starting comprehensive E2E test"

# Clean test directory
rm -rf /tmp/code-agent-test
mkdir -p /tmp/code-agent-test
cd /tmp/code-agent-test

# Test project analysis
echo "Running project analysis..."
uv run code-agent run "What are the key components of this codebase?" > analysis.txt

# Test file creation
echo "Testing file creation..."
uv run code-agent --auto-approve-edits run "Create a Python file called math_utils.py with functions for add, subtract, multiply and divide" > file_creation.txt

# Test file reading
echo "Testing file reading..."
uv run code-agent run "Show me the content of math_utils.py" > file_reading.txt

# Test file modification
echo "Testing file modification..."
uv run code-agent --auto-approve-edits run "Add docstrings to all functions in math_utils.py" > file_modification.txt

# Test command execution
echo "Testing command execution..."
uv run code-agent --auto-approve-native-commands run "Run 'python3 -c \"from math_utils import add; print(add(5, 3))\"'" > command_execution.txt

# Test error handling
echo "Testing error handling..."
uv run code-agent run "Try to read a file that doesn't exist" > error_handling.txt

# Test all outputs
echo "Test results:"
for file in *.txt; do
  echo "==== $file ===="
  cat "$file"
  echo ""
done

echo "E2E test completed successfully"
```

## Performance Testing

Test performance aspects of the application:

```bash
# Measure response time
time uv run code-agent run "What is the capital of France?"

# Test with large prompts
uv run code-agent run "$(cat large_prompt.txt)"

# Generate a large test file
dd if=/dev/zero bs=1M count=10 | tr '\0' 'X' > large_file.txt

# Test memory usage with large files
uv run code-agent run "Read large_file.txt and count the number of lines"

# Test rapid successive requests
for i in {1..5}; do 
  uv run code-agent run "Quick test $i: What is 2+2?"
  sleep 2
done
```

## Security Testing

Test security constraints:

```bash
# Test allowlist enforcement
uv run code-agent run "Execute rm -rf /"  # Should be blocked or require confirmation

# Test path validation
uv run code-agent run "Read the file /etc/passwd"  # Should be restricted

# Test security boundaries
uv run code-agent run "Try to access environment variables or system configuration files"
```

## Troubleshooting Failed Tests

When end-to-end tests fail, check the following:

1. Ensure all required dependencies are installed
2. Verify that API keys are properly configured
3. Check that Ollama service is running (for local model tests)
4. Examine logs for detailed error messages
5. Confirm network connectivity for cloud API calls and search functionality

## Continuous Integration

### Post-Merge End-to-End Testing

For comprehensive CI/CD implementation, set up your end-to-end tests to run only after PRs are merged to main, rather than during PR checks. This prevents long-running tests from slowing down the PR process while still ensuring quality after merge.

Create a GitHub Actions workflow file at `.github/workflows/e2e-tests.yml`:

```yaml
name: End-to-End Tests

on:
  push:
    branches:
      - main  # Only run on main branch after merges
  workflow_dispatch:  # Allow manual triggering

# Cancel in-progress runs when a new commit is pushed
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test-e2e:
    name: Run End-to-End Tests
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Run E2E tests
        run: ./scripts/run_e2e_tests.sh
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_TEST }}

      - name: Archive test artifacts
        if: always()  # Run even if tests fail
        uses: actions/upload-artifact@v4
        with:
          name: e2e-test-results
          path: |
            logs/
            test-reports/

      - name: Send Slack notification
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "End-to-End tests failed on main branch! See details: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Implementation Notes:

1. **Trigger Configuration**: The workflow only runs when changes are pushed to the main branch or manually triggered.

2. **Concurrency Management**: The `concurrency` section ensures that if a new merge occurs while tests are running, the previous test run will be canceled, and only the latest code will be tested.

3. **Test Artifacts**: Test logs and reports are saved as artifacts, allowing you to investigate failures even after the workflow completes.

4. **Notifications**: A Slack notification is sent if tests fail, alerting the team to issues in the main branch.

### Setting Up the Test Script

Create a comprehensive test script at `./scripts/run_e2e_tests.sh`:

```bash
#!/bin/bash
set -e  # Exit on any error

# Create directories for logs and reports
mkdir -p logs test-reports

echo "Running basic command tests..."
./scripts/test_basic_commands.sh

echo "Running file operation tests..."
./scripts/test_file_operations.sh

echo "Running model provider tests..."
./scripts/test_providers.sh

echo "Running Google search tests..."
./scripts/test_google_search.sh

echo "Running Ollama integration tests..."
# Only if Ollama is installed in the CI environment
if command -v ollama &> /dev/null; then
  ollama pull llama3:latest --insecure
  ./scripts/test_ollama.sh
else
  echo "Skipping Ollama tests (not installed)"
fi

echo "All end-to-end tests completed successfully!"
```

## Recommended Test Scenarios

When developing new features, always include end-to-end tests for:

1. Happy path scenarios (expected inputs, expected behavior)
2. Edge cases (minimum/maximum values, boundary conditions)
3. Error cases (invalid inputs, missing dependencies)
4. Performance aspects (large inputs, many operations)
5. Security boundaries (permissions, restrictions)
6. Provider-specific behavior (test across different LLM providers)
7. Tool integration (test proper functioning of all tools)
8. Complex multi-step reasoning (test ability to solve complex problems)

Remember that end-to-end tests complement unit and integration tests but do not replace them. Use all testing approaches for comprehensive quality assurance.

## Historical Test Records

This section contains records of specific test campaigns performed during major updates to the Code Agent.

### Gemini 2.0 Migration Testing

The following tests were performed after updating the default model to Gemini 2.0 Flash and fixing the API key access methods.

#### Configuration Tests

##### 1. Default Configuration Verification

```bash
uv run code-agent config show
```

**Purpose**: Verify that the configuration reflects the updated default model.

**Result**: ✅ Configuration showed `gemini-2.0-flash` as the default model, confirming the update was successful.

##### 2. Provider List Verification

```bash
uv run code-agent providers list
```

**Purpose**: Confirm the default provider and model in the providers list.

**Result**: ✅ Output confirmed `ai_studio / gemini-2.0-flash` as the current default.

##### 3. AI Studio Configuration Details

```bash
uv run code-agent config aistudio
```

**Purpose**: Verify AI Studio configuration has been updated with the correct model information.

**Result**: ✅ Displayed correct model information with Gemini 2.0 Flash listed as the default and also included Gemini 2.0 Pro as an available model.

#### Basic Functionality Tests

##### 4. Simple Query Test

```bash
uv run code-agent run "What is the Python version and how can I check it in the terminal?"
```

**Purpose**: Test basic query handling without tool execution.

**Result**: ✅ Agent responded correctly with information on how to check Python version.

##### 5. Command Execution with Approval

```bash
uv run code-agent run "List all Python files in the code_agent directory"
```

**Purpose**: Test that the agent requests approval before executing commands.

**Result**: ✅ Agent correctly asked for permission to execute the command.

##### 6. Command Execution with Auto-Approval

```bash
echo y | uv run code-agent run "Find all Python files in the code_agent directory and its subdirectories"
```

**Purpose**: Test command execution workflow when approval is provided.

**Result**: ✅ Command executed successfully after approval, listing Python files.

##### 7. File Reading Test

```bash
uv run code-agent run "Show me the first 10 lines of the README.md file"
```

**Purpose**: Verify file reading functionality.

**Result**: ✅ Agent successfully read and displayed the beginning of the README.md file.

##### 8. Google Search Functionality Test

```bash
uv run code-agent run "What is the Model Context Protocol (MCP)?"
```

**Purpose**: Test the agent's ability to search the web for information not available in the local context.

**Result**: ✅ Agent successfully used the google_search tool to find information about MCP and provided a well-summarized response.

#### Chat Mode Tests

##### 10. Basic Chat Interaction

```bash
echo -e "Hello, what is your default model?\n/exit" | uv run code-agent chat
```

**Purpose**: Test chat mode functionality with a simple interaction.

**Result**: ✅ Chat session initialized properly, though the response about the default model was generic.

##### 11. Google Search in Chat Mode

```bash
echo -e "What happened in the latest SpaceX launch?\n/exit" | uv run code-agent chat
```

**Purpose**: Test google search functionality in chat mode for current events.

**Result**: ✅ Agent searched the web and provided up-to-date information about the latest SpaceX launch.

#### Advanced Use Case Tests

These complex scenarios test multiple capabilities together and reflect real-world usage patterns.

##### 12. Code Analysis and Explanation

```bash
uv run code-agent run "Analyze the code_agent/agent/agent.py file and explain what the CodeAgent class does, including its main methods and how it uses tools"
```

**Purpose**: Test the agent's ability to analyze more complex code structures, understand class relationships, and provide clear explanations.

**Result**: The agent read the file, identified key components of the CodeAgent class, explained the tool-calling mechanism, and provided a comprehensive overview of the agent framework.

##### 13. Multi-Step File Operation

```bash
uv run code-agent chat
# Enter the following prompts:
# 1. "Find Python files in the code_agent directory that import the 'rich' library"
# 2. "For the files you found, identify which 'rich' components each file is using"
# 3. "Create a summary report of rich library usage in our codebase and save it as docs/rich_usage.md"
# 4. "/exit"
```

**Purpose**: Test sequential reasoning, memory of previous responses, and file creation.

**Result**: The agent maintained context across multiple turns, executed searches for imports, analyzed component usage patterns, and generated a structured markdown document with its findings.

##### 14. Code Refactoring Suggestion

```bash
uv run code-agent run "Analyze our error handling in code_agent/tools/*.py files and suggest a consistent approach to improve error handling. Include a specific code example of how we could refactor one of the error handling sections."
```

**Purpose**: Test code analysis across multiple files, pattern recognition, and ability to generate improvement suggestions with concrete examples.

**Result**: The agent identified current error handling patterns across the tool files, recognized inconsistencies, and provided a specific refactoring example with code.

##### 15-20. Additional Advanced Tests

Additional advanced tests were conducted to validate functionality around:
- Command chaining with dynamic inputs
- Configuration file analysis
- Documentation generation
- Google search for implementation
- Error simulation and debugging
- Configuration validation and security checks

#### Model-Specific Tests

##### 21. Alternative Model Test

```bash
uv run code-agent --model gemini-1.5-flash run "Tell me a short joke about programming"
```

**Purpose**: Verify the ability to override the default model for a specific query.

**Result**: ✅ Successfully used the specified model instead of the default, generating a programming joke.

#### Test Summary

The Gemini 2.0 migration tests confirmed that:

1. Configuration changes were successful across all parts of the system.
2. Basic functionality works correctly, including:
   - Text query processing
   - Command execution with approval
   - File operations
   - Google search capabilities
3. Model selection and overrides are working properly.
4. Chat mode functions correctly.

These tests provided confidence that the changes made to update the default model and fix the API key access methods were implemented correctly and didn't break any existing functionality. 