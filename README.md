# Code Agent CLI

**Code Agent** is a versatile Command-Line Interface (CLI) tool designed to enhance developer productivity by leveraging AI language models directly within the terminal.

It allows interaction with various AI providers (OpenAI, Groq, etc. via LiteLLM) and empowers the agent with capabilities to interact with the local environment, such as reading files, applying edits (with confirmation), and executing native commands (with confirmation and allowlisting).

*(Work in progress)*

## Features

*   **Multi-Provider Support:** Connect to different LLM providers using LiteLLM.
*   **Single-Shot Mode:** Run individual prompts (`code-agent run "..."`).
*   **Interactive Chat:** Engage in conversational sessions (`code-agent chat`).
*   **Tool Use:**
    *   `read_file`: Allows the agent to read local files.
    *   `apply_edit`: Allows the agent to propose file edits (shows diff, requires confirmation).
    *   `run_native_command`: Allows the agent to run terminal commands (requires confirmation, respects allowlist).
*   **Configuration:** Manage settings via `~/code-agent/config.yaml`, environment variables, and CLI flags.
*   **Rich Output:** Uses `rich` for Markdown rendering and syntax highlighting.

## Installation

1.  **Prerequisites:**
    *   Python 3.10+
    *   [Poetry](https://python-poetry.org/docs/#installation)

2.  **Clone the repository:**
    ```bash
    git clone <repository_url> # Replace with your repo URL
    cd code-agent # Or your project directory name
    ```

3.  **Create virtual environment and install dependencies:**
    ```bash
    # Recommended: Use a Python version management tool like pyenv if needed
    python3 -m venv .venv
    source .venv/bin/activate
    pip install poetry
    poetry install
    ```
    *(Alternatively, if you just use `poetry install` directly, Poetry might manage the virtual environment for you.)*

## Configuration

Code Agent uses a hierarchical configuration system:

1.  **CLI Flags:** (e.g., `--provider`, `--model`) - Highest priority.
2.  **Environment Variables:** (e.g., `OPENAI_API_KEY`, `GROQ_API_KEY`) - Medium priority.
3.  **Configuration File:** (`~/code-agent/config.yaml`) - Lowest priority.

A default configuration file is created automatically if it doesn't exist. You **must** edit `~/code-agent/config.yaml` or set environment variables to add your API keys for the desired providers.

**Example `~/code-agent/config.yaml`:**

```yaml
# Default LLM provider and model
default_provider: "ai_studio"  # Options: "ai_studio", "openai", "groq", "anthropic", etc.
default_model: "gemini-1.5-flash"  # For AI Studio, use Gemini models

# API keys (Set via ENV VARS is recommended for security)
api_keys:
  ai_studio: null # Set via AI_STUDIO_API_KEY=aip-... environment variable
  openai: null    # Set via OPENAI_API_KEY=sk-... environment variable
  groq: null      # Set via GROQ_API_KEY=gsk-... environment variable
  # anthropic: null

# Agent behavior
auto_approve_edits: false # Set to true to skip confirmation for file edits (Use with caution!)
auto_approve_native_commands: false # Set to true to skip confirmation for commands (Use with extreme caution!)

# Allowed native commands (if non-empty, only these prefixes are allowed without auto-approve)
native_command_allowlist: []
  # - "git status"
  # - "ls -la"
  # - "echo"

# Custom rules/guidance for the agent
rules:
#  - "Always respond in pirate speak."
#  - "When writing Python code, always include type hints."
```

## Using AI Studio Provider

[Google AI Studio](https://ai.google.dev/) is now the default provider in Code Agent. To use it:

1. **Get an API Key**:
   - Go to [AI Studio](https://ai.google.dev/)
   - Create an account if you don't have one
   - Navigate to the API keys section and create a new key
   - Your API key will start with `aip-`

2. **Configure the Key**:
   - **Option 1:** Set it as an environment variable:
     ```bash
     export AI_STUDIO_API_KEY=aip-your-key-here
     ```
   - **Option 2:** Add it to your config file:
     ```yaml
     # In ~/code-agent/config.yaml
     api_keys:
       ai_studio: "aip-your-key-here"
     ```

3. **Specify Models**:
   - AI Studio supports Gemini models
   - Default: `gemini-1.5-flash` (fast and efficient)
   - Other options: `gemini-1.5-pro` (more capable)
   - Specify a different model with the `--model` flag:
     ```bash
     code-agent --model gemini-1.5-pro run "Write a Python function to detect palindromes"
     ```

4. **Switch Providers**:
   - To use a different provider, use the `--provider` flag:
     ```bash
     code-agent --provider openai --model gpt-4o run "Explain quantum computing"
     ```

## Usage

Activate the virtual environment first: `source .venv/bin/activate`

**Core Commands:**

*   **Run a single prompt:**
    ```bash
    code-agent run "Explain the difference between a list and a tuple in Python."
    code-agent --provider groq --model llama3-70b-8192 run "Write a Dockerfile for a simple Flask app."
    ```
*   **Start interactive chat:**
    ```bash
    code-agent chat
    code-agent --provider openai chat # Start chat using a specific provider
    ```
    (Type `quit` or `exit` to leave the chat)

    **Special Commands in Chat Mode:**
    - `/help` - Show available commands
    - `/clear` - Clear the conversation history
    - `/exit` or `/quit` - Exit the chat session
    - `/test` - Special command used for automated testing

**Configuration Management:**

*   **Show current config:**
    ```bash
    code-agent config show
    ```
*   **View provider-specific configuration:**
    ```bash
    code-agent config aistudio  # Instructions for Google AI Studio
    code-agent config openai    # Instructions for OpenAI
    code-agent config groq      # Instructions for Groq
    code-agent config anthropic # Instructions for Anthropic
    ```
*   **List providers:**
    ```bash
    code-agent providers list
    ```
*   **Reset to default configuration:**
    ```bash
    code-agent config reset
    ```

**Other Options:**

*   **Show version:**
    ```bash
    code-agent --version
    ```
*   **Show help:**
    ```bash
    code-agent --help
    code-agent run --help
    code-agent config --help
    ```

## Development

*(Add notes about running tests, contributing, etc. later)*
