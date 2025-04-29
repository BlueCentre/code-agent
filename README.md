# Code Agent CLI

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=coverage)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=BlueCentre_code-agent&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=BlueCentre_code-agent)

**Code Agent** is a versatile Command-Line Interface (CLI) tool designed to enhance developer productivity by leveraging AI language models directly within the terminal.

It allows interaction with various AI providers (OpenAI, Groq, etc. via LiteLLM) and empowers the agent with capabilities to interact with the local environment, such as reading files, applying edits (with confirmation), and executing native commands (with confirmation and allowlisting).

DISCLAIMER: This repo and the tool itself is 99.95% built by LLM models such as Gemini 2.5 Pro and Claude 3.7 Sonnet! The remaining 0.05% goes to my prompts, designs, and gaurdrails to keep the agents in-check. 😜

*(Work in progress)*

## Repository Structure

```
.
├── code_agent/       # Main package source code
│   ├── agent/        # Core agent logic and ADK agent implementations
│   ├── adk/          # Google ADK specific integration components
│   ├── cli/          # Command-Line Interface setup (Typer)
│   ├── config/       # Configuration management
│   ├── tools/        # Native tool implementations for the agent
│   └── verbosity/    # Verbosity and logging setup
├── sandbox/          # Experimentation and ADK testing environment
│   ├── agent_adk_runner/ # Simple ADK runner for testing
│   └── ...           # ADK test scripts
├── tests/            # Unit and integration tests
├── docs/             # Documentation files
│   ├── CONTRIBUTING.md
│   ├── architecture.md
│   ├── testing.md
│   └── ...           # Other guides and documentation
├── scripts/          # Utility scripts (testing, setup, etc.)
├── .githooks/        # Git hooks for quality checks
├── .github/          # GitHub Actions workflows
├── .venv/            # Virtual environment (typically excluded)
├── .gitignore        # Specifies intentionally untracked files
├── .pre-commit-config.yaml # Pre-commit hook configurations
├── .python-version   # Specifies Python version for pyenv
├── CHANGELOG.md      # Log of changes per version
├── LICENSE           # Project license file
├── Makefile          # Make commands for development tasks
├── pyproject.toml    # Project metadata, dependencies (PEP 621), and tool configs
├── README.md         # This file
├── sonar-project.properties # SonarCloud analysis configuration
├── uv.lock           # Pinned dependencies for UV
└── uv.toml           # UV project configuration (if used)

```

### Key Directories

- **code_agent/**: Contains the core source code for the CLI tool and agent logic.
- **sandbox/**: Environment for experimentation and testing, particularly ADK features.
- **tests/**: Test suite covering unit and integration tests.
- **docs/**: Project documentation, guides, and architectural information.
- **scripts/**: Utility scripts aiding development, testing, and CI/CD.
- **.github/**: Contains GitHub Actions workflow definitions.
- **.githooks/**: Local Git hooks to enforce standards before committing/pushing.

### Documentation

- **README.md**: Project overview, installation, and usage instructions
- **docs/**: Detailed documentation about architecture, implementation, and specific features
- **docs/COVERAGE_VERIFICATION.md**: Guide for verifying test coverage

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

*   **Local Environment Integration (Agent Tools):**
    * **File System Access:** Read file contents (`read_file`), list directory contents (`list_dir`).
    * **Code Manipulation:** Propose file edits with diff preview and confirmation (`edit_file`).
    * **Command Execution:** Run native terminal commands with safety checks and allowlisting (`run_terminal_cmd`).
    * **Code Search:** Semantic search across the codebase (`codebase_search`).
    * **Text/Pattern Search:** Find exact text or regex patterns within files (`grep_search`).
    * **File Search:** Locate files using fuzzy path matching (`file_search`).
    * **Web Search:** Access up-to-date online information (`web_search`).

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

## Quick Start

This section describes how to quickly install and run Code Agent as a user. For development or contribution, please see the [Development & Contributing](#development--contributing) section.

### Installation

1.  **Install UV:** Code Agent uses [UV](https://github.com/astral-sh/uv) for package management. Install it first:
    ```bash
    # Install UV on macOS/Linux
    curl -fsSL https://astral.sh/uv/install.sh | sh
    ```
    *See the [UV documentation](https://astral.sh/uv/install) for other installation methods.*

2.  **Install Code Agent:**
    ```bash
    # Install using UV
    uv pip install cli-code-agent
    ```
    *(Assuming the package is published as `cli-code-agent` on PyPI)*

    **Alternative (Run directly from GitHub without installing):**
    ```bash
    # Using uvx to run the latest version from the main branch
    uvx --from git+https://github.com/BlueCentre/code-agent.git@main code-agent --help
    ```

### Verify Installation

After installation, check that the command is available:

```bash
code-agent --help
```

*If the `code-agent` command is not found, you may need to ensure the installation location's `bin` directory (where UV installs packages, often similar to pip's locations like `~/.local/bin`) is included in your system's `PATH` environment variable.*

### First Run

Code Agent requires API keys for the LLM providers you want to use. Google AI Studio is the default provider.

1.  **Set API Key:** Get your AI Studio API key (starting with `aip-`) from [Google AI Studio](https://ai.google.dev/) and set it as an environment variable:
    ```bash
    # Replace with your actual key
    export AI_STUDIO_API_KEY=aip-your-key-here
    ```
    *(See the [Configuration](#configuration) section for setting keys for other providers or using the config file).*

2.  **Run a command:**
    ```bash
    code-agent run "Hello! What can you help me with today?"

    # Or start an interactive chat session
    code-agent chat
    ```

## Usage

**Core Commands:**

*   **Run a single prompt:**
    ```bash
    # Using default provider (AI Studio)
    code-agent run "Explain the difference between a list and a tuple in Python."

    # Specifying provider and model
    code-agent --provider groq --model llama3-70b-8192 run "Write a Dockerfile for a simple Flask app."
    ```
*   **Start interactive chat:**
    ```bash
    # Using default provider
    code-agent chat

    # Specifying provider
    code-agent --provider openai chat
    ```
    (Type `quit` or `exit` to leave the chat)

    **Special Commands in Chat Mode:**
    - `/help` - Show available commands
    - `/clear` - Clear the conversation history
    - `/exit` or `/quit` - Exit the chat session

*   **Interact with local Ollama models:**
    ```bash
    code-agent ollama list # List available local models
    code-agent ollama chat llama3 "Ask a question..." # Chat with a specific model
    ```
    *(See the [Using Ollama](#using-ollama-for-local-models) section for details)*

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

### Using AI Studio Provider

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

### Using Ollama for Local Models

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

## Development & Contributing

We welcome contributions to the Code Agent project! Whether you're fixing bugs, adding features, improving documentation, or reporting issues, your help is appreciated.

Please see our [Contributing Guide](docs/CONTRIBUTING.md) for detailed contribution guidelines, including coding standards, branch naming conventions, and the pull request process.

The project maintains high standards for code quality with:
- Minimum 80% test coverage requirement
- Comprehensive CI/CD pipeline using GitHub Actions
- Conventional commit message format
- Squash merging for a clean history

### Setting Up Development Environment

1.  **Prerequisites:**
    *   Python 3.11+
    *   [UV](https://github.com/astral-sh/uv) installed (See [UV installation guide](https://astral.sh/uv/install))

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/BlueCentre/code-agent.git
    cd code-agent
    ```

3.  **Set up the environment:**
    *   **Recommended (Quick Setup):** Run the setup script. This creates a virtual environment, installs dependencies using UV, and installs Git hooks.
        ```bash
        ./scripts/setup_dev_env.sh
        ```
    *   **Manual Setup (using UV):**
        ```bash
        # Create virtual environment
        uv venv
        # Install dependencies (including development dependencies)
        uv sync --all-extras
        # Install pre-commit hooks
        uv run pre-commit install
        ```

### Development Commands

The project includes a Makefile for common tasks, leveraging UV for execution. Activate your virtual environment (`source .venv/bin/activate`) before running these.

| Command             | Description                                                      |
| ------------------- | ---------------------------------------------------------------- |
| `make test`         | Run all tests using pytest.                                       |
| `make test-unit`    | Run only unit tests (`@pytest.mark.unit`).                       |
| `make test-coverage`  | Run tests with coverage report (fails if below 80%).             |
| `make test-report`  | Run tests with coverage and open the HTML report.                |
| `make lint`         | Check code style and formatting using Ruff.                      |
| `make format`       | Format code using Ruff.                                          |
| `make clean`        | Remove build artifacts, caches, and coverage reports.            |
| `make code-agent-chat`| Start the interactive chat using the development version.        |
| `make swe-run-chat` | Run the Software Engineer ADK agent (console mode).              |
| `make swe-web-chat` | Run the Software Engineer ADK agent (web UI mode).               |

### Git Workflow

This project follows a standardized Git workflow:

- **Branches:** All changes are made in feature branches named `<type>/<description>` (e.g., `feat/user-auth`, `fix/login-bug`). Use the script:
  ```bash
  ./scripts/create-branch.sh feat new-feature
  ```
- **Commits:** Messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) format.
  ```bash
  git commit -m "feat: add new feature"
  ```
- **Pushing:**
  ```bash
  git push -u origin feat/new-feature
  ```
- See [Git Development Documentation](docs/git_development.md#git-workflow) for complete details.

### Git Hooks

This project uses [pre-commit](https://pre-commit.com/) to manage Git hooks and ensure code quality before commits. The hooks are defined in `.pre-commit-config.yaml`.

Hooks (like linting and formatting) are automatically run on `git commit`.

**Installation:** The hooks are installed automatically when you run the setup script (`./scripts/setup_dev_env.sh`). If you set up the environment manually, ensure you run:
```bash
uv run pre-commit install
```
*This command only needs to be run once after cloning.*

### Testing

Tests are located in the `tests/` directory (structured into `unit`, `integration`, and `fixtures`) and use the `pytest` framework. UV automatically uses the `.venv` virtual environment for the commands below.

**Running Tests:**

Use the Makefile targets:

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run tests with coverage (fails below 80%)
make test-coverage

# Run tests with coverage and open HTML report
make test-report
```
*See `Makefile` or `docs/testing.md` for more details or specific test runs.*

**Development Workflow & Testing:**

When developing:

1.  Make your changes in a feature branch.
2.  Test the development version directly using `uv run` or `make`:
    ```bash
    # Example: Check version
    uv run code-agent --version
    # Example: Run a command
    uv run code-agent run "Test prompt for my new feature"
    # Example: Use a make target
    make code-agent-chat
    ```
3.  Run the test suite to check for regressions:
    ```bash
    make test
    # Or run specific tests like 'make test-unit'
    ```
4.  Run the linter/formatter:
    ```bash
    make lint
    make format # If needed
    ```
5.  If adding new features, ensure you add corresponding tests to maintain coverage >= 80%.

### Pull Request Process

When submitting a PR:

1. The GitHub Actions CI pipeline automatically runs tests, linting, and checks coverage.
2. Coverage reports are posted as comments on the PR.
3. All checks must pass, and coverage must remain >= 80%.
4. At least one reviewer must approve.
5. Use "Squash and merge" for a clean `main` branch history.

### GitHub Actions Workflows

This project uses GitHub Actions for automation:

- **Pull Request Checks (`pr-workflow.yml`, `test-coverage.yml`, `test-e2e.yml`):** Automatically run on every pull request and push to the `main` branch. These workflows perform:
    - Linting and code formatting checks.
    - Unit and integration tests across Python versions.
    - End-to-end tests.
    - Code coverage calculation and reporting (including posting results to the PR).
- **Manual Trigger (`test-coverage.yml`):** The test coverage workflow can also be manually triggered via the GitHub Actions tab (`workflow_dispatch`), useful for testing changes on demand.
- **Publish (`publish.yml`):** Automatically publishes the package to PyPI when a new release tag is pushed.
- **Nightly (`nightly.yml`):** Runs scheduled tasks (e.g., checks, updates). *(Verify exact purpose if needed)*

### PR Validation & Monitoring

- **Validation:** An optional feature provides immediate feedback on CI/CD checks after pushing changes. See [PR Validation Documentation](docs/PR_VALIDATION.md) for setup.
- **Monitoring:** Since Git lacks a reliable post-push hook, use a script to monitor PR status:
  ```bash
  # Run after pushing to check CI status
  ./scripts/monitor-pr.sh
  ```
  See the [PR Monitoring Script Documentation](./docs/git_development.md#pr-monitoring-and-validation) for details.

### Running ADK Agents

This project includes agents compatible with the Google Agent Development Kit (ADK). Ensure you have installed the ADK (`uv add google-adk` or add to `pyproject.toml` and run `uv sync`).

Run agents using `uv run adk run ...` or `uvx ... adk run ...` within the activated environment.

Available agents and example commands:

*   **Software Engineer Agent:**
    ```bash
    # Run scoped to agent dir
    cd code_agent/agent/software_engineer && uvx --from git+https://github.com/google/adk-python.git@main adk run software_engineer
    # Run web mode scoped to agent dir
    cd code_agent/agent/software_engineer && uvx --from git+https://github.com/google/adk-python.git@main adk web
    # Run scoped to top level
    uvx --from git+https://github.com/google/adk-python.git@main adk run code_agent/agent/software_engineer/software_engineer
    # Run web mode scoped to top level
    uvx --from git+https://github.com/google/adk-python.git@main adk web code_agent/agent/software_engineer
    ```
*   **Travel Concierge Agent:** (Assuming similar structure)
    ```bash
    cd code_agent/agent/travel-concierge && ./start_run.sh
    ```
*   **Sandbox ADK Runner:**
    ```bash
    uv run adk run sandbox/agent_adk_runner
    ```

## Upgrading

To upgrade Code Agent to the latest published version:

```bash
# Using UV
uv pip install --upgrade cli-code-agent
```

After upgrading, verify the new version:

```bash
code-agent --version
```

If you're using the Ollama integration, ensure your local Ollama installation is also up-to-date:

```bash
# Example: On macOS with Homebrew
brew upgrade ollama

# Or download the latest version from https://ollama.ai/download
```