# Code Agent CLI

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=coverage)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)

**Code Agent** is a versatile Command-Line Interface (CLI) tool designed to enhance developer productivity by leveraging AI language models directly within the terminal.

It allows interaction with various AI providers (OpenAI, Groq, etc. via LiteLLM) and empowers the agent with capabilities to interact with the local environment, such as reading files, applying edits (with confirmation), and executing native commands (with confirmation and allowlisting).

*(Work in progress)*

## Repository Structure

```
cli-agent/
├── code_agent/       # Main package source code
├── cli_agent/        # Ollama integration and extensions
│   ├── providers/    # Provider implementations (Ollama)
│   ├── commands/     # CLI commands for providers
│   └── main.py       # CLI entry point for extensions
├── tests/            # Unit and integration tests
├── docs/             # Documentation files
│   ├── architecture.md
│   ├── CONTRIBUTING.md
│   ├── development_testing.md
│   ├── feature_*.md          # Feature-specific documentation
│   ├── getting_started_*.md  # Getting started guides
│   ├── planning_*.md         # Planning documents
│   └── ...                   # Other documentation
├── scripts/          # Utility scripts
│   ├── run_coverage_pipeline.sh
│   ├── run_coverage_pipeline_venv.sh
│   └── run_tests.sh
├── .github/          # GitHub Actions workflows
├── .venv/            # Virtual environment directory (if using venv)
├── pyproject.toml    # Project dependencies and configuration
└── README.md         # Project documentation
```

### Key Directories

- **code_agent/**: Contains the main source code for the CLI tool
- **cli_agent/**: Contains the Ollama integration and extensions
- **tests/**: Test suite for ensuring code quality and functionality
- **docs/**: Project documentation and guides
- **scripts/**: Utility scripts for development, testing, and CI/CD pipelines

### Documentation

- **README.md**: Project overview, installation, and usage instructions
- **docs/**: Detailed documentation about architecture, implementation, and specific features
- **docs/COVERAGE_VERIFICATION.md**: Guide for verifying test coverage

## Quick Start

### Installation

First, install the UV package manager (optional but recommended for faster installation):

```bash
# Install UV on macOS/Linux
curl -fsSL https://astral.sh/uv/install.sh | bash

# Or with pip
pip install uv
```

Then, install the CLI Code Agent:

```bash
# Using pip
pip install cli-code-agent

# Or using uv (faster)
uv pip install cli-code-agent

# For using Ollama features, ensure you have requests and rich:
pip install requests rich
```

## Upgrading

To upgrade Code Agent to the latest version:

```bash
# Using pip
pip install --upgrade cli-code-agent

# Or using uv (faster)
uv pip install --upgrade cli-code-agent
```

After upgrading, verify your installation:

```bash
code-agent --version
```

If you're using Ollama integration, ensure your local Ollama installation is also up to date:

```bash
# On macOS with Homebrew
brew upgrade ollama

# Or download the latest version from https://ollama.ai/download
```

### Verify Installation

After installation, make sure the executable is in your PATH. If you can't run the `code-agent` command, you may need to add the installation directory to your PATH:

```bash
# Find where the package was installed
pip show cli-code-agent

# Add the bin directory to your PATH (example for ~/.local/bin)
export PATH="$HOME/.local/bin:$PATH"

# For permanent addition, add to your shell profile (.bashrc, .zshrc, etc.)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### First Run

After installation, set up your API key (for OpenAI in this example):

```bash
export OPENAI_API_KEY=sk-your-key-here
code-agent run "Hello! What can you help me with today?"
```

## Features

*   **Multi-Provider Support:**
    * Connect to different LLM providers using LiteLLM
    * Supports OpenAI, Google AI Studio, Groq, Anthropic, and more
    * Local model support via Ollama integration
    * Easily switch between providers with command-line flags

*   **Versatile Interaction Modes:**
    * **Single-Shot Mode:** Run individual prompts (`code-agent run "..."`)
    * **Interactive Chat:** Engage in conversational sessions (`code-agent chat`)
    * Special chat commands: `/help`, `/clear`, `/exit`, `/quit`

*   **Local Environment Integration:**
    * **Read files:** Agent can access and analyze local files
    * **Apply Edits:** Propose file changes with diff preview and confirmation
    * **Execute Commands:** Run native terminal commands with safety checks
    * **Search Capabilities:** Find files, locate code patterns, and analyze codebases

*   **Advanced Security Controls:**
    * Path validation to prevent path traversal attacks
    * Workspace restrictions to limit file operations
    * Command validation and allowlisting to prevent dangerous operations
    * Optional auto-approval settings with clear security warnings

*   **Rich Configuration System:**
    * Hierarchical configuration (CLI > Environment > Config file)
    * Dynamic validation of settings
    * Provider-specific configuration options

*   **User Experience Features:**
    * Rich text output with Markdown rendering
    * Syntax highlighting for code
    * Clear error messages and troubleshooting information
    * Interactive confirmation prompts for system modifications

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

    **Faster Alternative using `uv`:**

    If you have `uv` installed (see [Quick Start](#quick-start)), you can use it for a much faster setup:

    ```bash
    # 1. Create the virtual environment
    uv venv .venv

    # 2. Activate the environment (Linux/macOS)
    source .venv/bin/activate
    #    Activate the environment (Windows - Command Prompt/PowerShell)
    #    .venv\Scripts\activate

    # 3. Install dependencies
    uv pip install '.[dev]'
    ```

## Configuration

Code Agent uses a hierarchical configuration system:

1.  **CLI Flags:** (e.g., `--provider`, `--model`) - Highest priority.
2.  **Environment Variables:** (e.g., `OPENAI_API_KEY`, `GROQ_API_KEY`) - Medium priority.
3.  **Configuration File:** (`~/.config/code-agent/config.yaml`) - Lowest priority.

A default configuration file is created automatically if it doesn't exist. You **must** edit `~/.config/code-agent/config.yaml` or set environment variables to add your API keys for the desired providers.

**Example `~/.config/code-agent/config.yaml`:**

```yaml
# Default LLM provider and model
default_provider: "ai_studio"  # Options: "ai_studio", "openai", "groq", "anthropic", etc.
default_model: "gemini-2.0-flash"  # For AI Studio, use Gemini models

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
     # In ~/.config/code-agent/config.yaml
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

## Using Ollama for Local Models

Code Agent includes integration with [Ollama](https://ollama.ai/) to run open-source models locally on your machine:

1. **Install Ollama**:
   - Download and install Ollama from [https://ollama.ai/download](https://ollama.ai/download)
   - Start the Ollama service with `ollama serve`

2. **Pull Models**:
   - Pull the models you want to use:
     ```bash
     ollama pull llama3
     ollama pull codellama:13b
     ```

3. **Use the Ollama Commands**:
   - List available models:
     ```bash
     code-agent ollama list
     ```
   - Chat with a model:
     ```bash
     code-agent ollama chat llama3:latest "Explain how to use async/await in JavaScript"
     ```
   - Add a system prompt:
     ```bash
     code-agent ollama chat codellama:13b "Write a sorting algorithm" --system "You are a helpful coding assistant"
     ```

4. **Advantages of Local Models**:
   - No API key required
   - Complete privacy - all data stays on your machine
   - No usage costs
   - Customizable with fine-tuning options

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
    code-agent config ollama    # Instructions for local Ollama models
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

## Contributors

We welcome contributions to the Code Agent project! Whether you're fixing bugs, adding features, improving documentation, or reporting issues, your help is appreciated.

Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details on:

- Setting up your development environment
- Our coding standards and requirements
- The branch naming convention and git workflow
- Pull request process and requirements
- Testing guidelines

The project maintains high standards for code quality with:
- Minimum 80% test coverage requirement
- Comprehensive CI/CD pipeline
- Conventional commit message format
- Squash merging for a clean history

### Development Workflow

This project follows a standardized Git workflow to ensure code quality and maintainability:

- All new features, bug fixes, and changes are implemented in feature branches
- Branch names follow the convention: `<type>/<description>` (e.g., `feat/user-auth`, `fix/login-bug`)
- Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format
- Pull requests include automated test results and coverage reports as comments
- See [Git Workflow Documentation](docs/GIT_WORKFLOW.md) for complete details

### Quick Example: Creating a Feature Branch

```bash
# Create a new feature branch
./scripts/create-branch.sh feat new-feature

# Make changes and commit with conventional format
git commit -m "feat: add new feature"

# Push and create a PR
git push -u origin feat/new-feature
```

### Running Tests

The project maintains a minimum of 80% test coverage. You can run tests using:

```bash
# Run tests using the test script
./scripts/run_tests.sh

# Run tests with coverage report
./scripts/run_coverage_pipeline_venv.sh

# Run tests for a specific module
./scripts/run_native_tools_coverage.sh
```

Test coverage can also be viewed in HTML format with:

```bash
./scripts/run_tests.sh --html
```

### Testing Development Code

After checking out the repository, follow these steps to test your development version:

```bash
# Set up your virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install poetry
poetry install

# Install the package in development mode
pip install -e .
```

Now you can run the development version directly:

```bash
# Test the development version with a simple command
code-agent --version

# Run a simple prompt to test functionality
code-agent run "Hello, world"

# Run unit tests to ensure your changes don't break existing functionality
./scripts/run_tests.sh
```

When making changes to the code:
1. Make your changes in a feature branch
2. Run tests to ensure functionality is preserved
3. Run the linter to ensure code quality standards are met
4. Test the development version with relevant commands

If you add new commands or features, be sure to add appropriate tests to maintain code coverage.

### Pull Request Process

When submitting a PR:

1. The GitHub Actions CI pipeline will automatically run tests
2. Coverage reports are posted as comments on the PR
3. All checks must pass and coverage cannot drop below 80%
4. At least one reviewer must approve the PR
5. Use "Squash and merge" to maintain a clean history
