# Code Agent Testing Guide

This document provides comprehensive guidance on testing the Code Agent CLI application, including general end-to-end testing procedures and historical test records.

## Table of Contents
- [Introduction](#introduction)
- [End-to-End Testing Guide](#end-to-end-testing-guide)
  - [Basic Test Examples](#basic-test-examples)
  - [Testing File Operations](#testing-file-operations)
  - [Testing Shell Commands](#testing-shell-commands)
  - [Testing Web Search Functionality](#testing-web-search-functionality)
  - [Testing Error Handling](#testing-error-handling)
  - [Testing Configuration](#testing-configuration)
- [Automated End-to-End Testing](#automated-end-to-end-testing)
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
echo "Tell me a joke?\nexit" | code-agent chat

# Test multiple interactions and exit
echo "What is Python?\nWhat is a list in Python?\nexit" | code-agent chat

# Test with system commands
echo "List files in this directory\nexit" | code-agent chat

# Test special commands in chat
echo "What is your name?\n/help\n/clear\nTell me another joke\n/exit" | code-agent chat
```

#### Testing the `run` Command

Test single prompt processing:

```bash
# Basic question
code-agent run "What is your name?"

# Code-related query
code-agent run "Write a Python function to check if a string is a palindrome"

# Using with different providers
code-agent --provider openai run "Explain quantum computing in simple terms"
code-agent --provider groq --model llama3-70b-8192 run "Write a Dockerfile for a Node.js app"
code-agent --provider anthropic run "Compare Python and JavaScript for web development"
```

#### Testing Ollama Commands

Test integration with local Ollama models:

```bash
# List available models
code-agent ollama list

# List models in JSON format
code-agent ollama list --json

# Run command with a local model
code-agent ollama run llama3 "Tell me a short joke"

# Chat with system prompt
code-agent ollama chat codellama:13b "Write a sorting algorithm" --system "You are a helpful coding assistant"
```

### Testing File Operations

Test file reading and editing capabilities:

```bash
# Read a file
code-agent run "Show me the contents of README.md"

# Create a new file
code-agent run "Create a new file called hello.py with a simple Hello World program"

# Edit an existing file
code-agent run "Add a docstring to hello.py"
```

### Testing Shell Commands

Test executing shell commands through the agent:

```bash
# Directory listing
code-agent run "List all files in the current directory"

# System information
code-agent run "Show system information"

# Git operations
code-agent run "Show git status of this repository"
```

### Testing Web Search Functionality

Test the agent's ability to search the web for information:

```bash
# Basic web search
code-agent run "What is the current weather in London?"

# Technical documentation search
code-agent run "Find the documentation for Python's requests library and summarize the key features"

# Current events search
code-agent run "What were the major tech announcements in the last month?"

# Combined search and local operation
code-agent run "Search for best Python logging practices and create a logging_example.py file implementing them"

# Search with disabled functionality
code-agent config set security.enable_web_search false
code-agent run "What is the population of Tokyo?"
code-agent config set security.enable_web_search true  # Re-enable after test
```

### Testing Error Handling

Test how the application handles errors:

```bash
# Invalid provider
code-agent --provider invalid_provider run "Hello"

# Non-existent model
code-agent --provider openai --model nonexistent_model run "Hello"

# Missing API keys
OPENAI_API_KEY="" code-agent --provider openai run "Hello"

# Reading non-existent file
code-agent run "Show me the contents of non_existent_file.txt"

# Web search connection errors (can be simulated by disconnecting from network)
code-agent run "What is the current exchange rate between USD and EUR?"
```

### Testing Configuration

Test configuration management:

```bash
# Show current configuration
code-agent config show

# Provider-specific configuration
code-agent config openai
code-agent config ollama

# Enable/disable web search
code-agent config set security.enable_web_search false
code-agent config show  # Verify setting changed
code-agent config set security.enable_web_search true  # Restore default
```

## Automated End-to-End Testing

For automated testing, create shell scripts that run various commands and check the output:

```bash
#!/bin/bash
# Example automated end-to-end test script

# Test version command
output=$(code-agent --version)
if [[ $output != *"Code Agent version"* ]]; then
  echo "Version test failed"
  exit 1
fi

# Test help command
output=$(code-agent --help)
if [[ $output != *"CLI agent for interacting with"* ]]; then
  echo "Help test failed"
  exit 1
fi

# Test simple run command with mock response
output=$(echo "What is 2+2?" | CODE_AGENT_TEST_MODE=1 code-agent chat)
if [[ $output != *"4"* ]]; then
  echo "Simple math test failed"
  exit 1
fi

echo "All tests passed!"
```

## Performance Testing

Test performance aspects of the application:

```bash
# Measure response time
time code-agent run "What is the capital of France?"

# Test with large prompts
code-agent run "$(cat large_prompt.txt)"

# Measure web search response time
time code-agent run "What are the latest developments in quantum computing?"
```

## Security Testing

Test security constraints:

```bash
# Test allowlist enforcement
code-agent run "Execute rm -rf /"  # Should be blocked or require confirmation

# Test path validation
code-agent run "Read the file /etc/passwd"  # Should be restricted

# Test web search security
code-agent run "Search for information about <insert sensitive info here>"  # Should sanitize query
```

## Troubleshooting Failed Tests

When end-to-end tests fail, check the following:

1. Ensure all required dependencies are installed
2. Verify that API keys are properly configured
3. Check that Ollama service is running (for local model tests)
4. Examine logs for detailed error messages
5. Confirm network connectivity for cloud API calls and web searches
6. Verify that duckduckgo-search package is installed correctly

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
        uses: actions/upload-artifact@v3
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

echo "Running web search tests..."
./scripts/test_web_search.sh

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

Remember that end-to-end tests complement unit and integration tests but do not replace them. Use all testing approaches for comprehensive quality assurance.

## Historical Test Records

This section contains records of specific test campaigns performed during major updates to the Code Agent.

### Gemini 2.0 Migration Testing

The following tests were performed after updating the default model to Gemini 2.0 Flash and fixing the API key access methods.

#### Configuration Tests

##### 1. Default Configuration Verification

```bash
code-agent config show
```

**Purpose**: Verify that the configuration reflects the updated default model.

**Result**: ✅ Configuration showed `gemini-2.0-flash` as the default model, confirming the update was successful.

##### 2. Provider List Verification

```bash
code-agent providers list
```

**Purpose**: Confirm the default provider and model in the providers list.

**Result**: ✅ Output confirmed `ai_studio / gemini-2.0-flash` as the current default.

##### 3. AI Studio Configuration Details

```bash
code-agent config aistudio
```

**Purpose**: Verify AI Studio configuration has been updated with the correct model information.

**Result**: ✅ Displayed correct model information with Gemini 2.0 Flash listed as the default and also included Gemini 2.0 Pro as an available model.

#### Basic Functionality Tests

##### 4. Simple Query Test

```bash
code-agent run "What is the Python version and how can I check it in the terminal?"
```

**Purpose**: Test basic query handling without tool execution.

**Result**: ✅ Agent responded correctly with information on how to check Python version.

##### 5. Command Execution with Approval

```bash
code-agent run "List all Python files in the code_agent directory"
```

**Purpose**: Test that the agent requests approval before executing commands.

**Result**: ✅ Agent correctly asked for permission to execute the command.

##### 6. Command Execution with Auto-Approval

```bash
echo y | code-agent run "Find all Python files in the code_agent directory and its subdirectories"
```

**Purpose**: Test command execution workflow when approval is provided.

**Result**: ✅ Command executed successfully after approval, listing Python files.

##### 7. File Reading Test

```bash
code-agent run "Show me the first 10 lines of the README.md file"
```

**Purpose**: Verify file reading functionality.

**Result**: ✅ Agent successfully read and displayed the beginning of the README.md file.

##### 8. Web Search Functionality Test

```bash
code-agent run "What is the Model Context Protocol (MCP)?"
```

**Purpose**: Test the agent's ability to search the web for information not available in the local context.

**Result**: ✅ Agent successfully used the web_search tool to find information about MCP and provided a well-summarized response.

##### 9. Web Search Error Handling

```bash
# Temporarily disable web search in configuration
code-agent config set security.enable_web_search false
code-agent run "What is the latest version of Python?"
code-agent config set security.enable_web_search true  # Re-enable after test
```

**Purpose**: Test how the agent handles web search when the feature is disabled.

**Result**: ✅ Agent correctly reported that web search is disabled and offered alternative ways to find the information.

#### Chat Mode Tests

##### 10. Basic Chat Interaction

```bash
echo -e "Hello, what is your default model?\n/exit" | code-agent chat
```

**Purpose**: Test chat mode functionality with a simple interaction.

**Result**: ✅ Chat session initialized properly, though the response about the default model was generic.

##### 11. Web Search in Chat Mode

```bash
echo -e "What happened in the latest SpaceX launch?\n/exit" | code-agent chat
```

**Purpose**: Test web search functionality in chat mode for current events.

**Result**: ✅ Agent searched the web and provided up-to-date information about the latest SpaceX launch.

#### Advanced Use Case Tests

These complex scenarios test multiple capabilities together and reflect real-world usage patterns.

##### 12. Code Analysis and Explanation

```bash
code-agent run "Analyze the code_agent/agent/agent.py file and explain what the CodeAgent class does, including its main methods and how it uses tools"
```

**Purpose**: Test the agent's ability to analyze more complex code structures, understand class relationships, and provide clear explanations.

**Result**: The agent read the file, identified key components of the CodeAgent class, explained the tool-calling mechanism, and provided a comprehensive overview of the agent framework.

##### 13. Multi-Step File Operation

```bash
code-agent chat
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
code-agent run "Analyze our error handling in code_agent/tools/*.py files and suggest a consistent approach to improve error handling. Include a specific code example of how we could refactor one of the error handling sections."
```

**Purpose**: Test code analysis across multiple files, pattern recognition, and ability to generate improvement suggestions with concrete examples.

**Result**: The agent identified current error handling patterns across the tool files, recognized inconsistencies, and provided a specific refactoring example with code.

##### 15-20. Additional Advanced Tests

Additional advanced tests were conducted to validate functionality around:
- Command chaining with dynamic inputs
- Configuration file analysis
- Documentation generation
- Web search for implementation
- Error simulation and debugging
- Configuration validation and security checks

#### Model-Specific Tests

##### 21. Alternative Model Test

```bash
code-agent --model gemini-1.5-flash run "Tell me a short joke about programming"
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
   - Web search capabilities
3. Model selection and overrides are working properly.
4. Chat mode functions correctly.

These tests provided confidence that the changes made to update the default model and fix the API key access methods were implemented correctly and didn't break any existing functionality. 