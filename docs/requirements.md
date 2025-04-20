# Code Agent Requirements

## 1. Introduction & Vision

This document outlines the requirements for the Code Agent Command-Line Interface (CLI) tool.

**Vision:** To create a powerful, flexible CLI tool that allows users to leverage various AI language models for tasks such as code generation, explanation, refactoring, terminal command assistance, and general question answering, directly within their terminal environment.

**Core Goal:** Provide a unified interface to interact with multiple AI model providers (supporting the OpenAI API standard) and empower the agent with capabilities to interact with the user's local environment (files, terminal commands) in a controlled and secure manner.

**Key Differentiators:**

*   **Multi-Provider Support:** Seamlessly switch between different LLM providers (OpenAI, Groq, Ollama, Anthropic, Azure OpenAI, etc.) using LiteLLM.
*   **Agentic Capabilities:** Go beyond simple Q&A to perform actions like editing local files (with user consent) and executing terminal commands (securely).
*   **Flexible Configuration:** Allow users to configure API keys, default models, and agent behavior via CLI arguments, environment variables, and a dedicated configuration file.
*   **Dual Interaction Modes:** Support both quick, single-shot commands and persistent interactive chat sessions.

## 2. Core Requirements

### 2.1 Functionality

*   **Code Assistance:** Generate code snippets, explain existing code, refactor code based on prompts.
*   **Command-Line Assistance:** Suggest relevant terminal commands, execute commands (with user consent).
*   **General Q&A:** Answer general knowledge or technical questions.
*   **File Editing:** Propose changes to local files, display differences (diffs), and apply edits only after explicit user confirmation or if an auto-approve flag is enabled.

### 2.2 Interaction Modes

*   **Single-Shot Command:** Execute a specific prompt and exit (e.g., `code-agent --model gpt-4o "Refactor this python code" < file.py`).
*   **Interactive Chat:** Start a persistent session where conversation history is maintained (e.g., `code-agent chat`).

### 2.3 Model Provider Management

*   **Multi-Provider Integration:** Utilize LiteLLM to connect to any OpenAI API-compatible endpoint.
*   **Configuration Hierarchy:** Prioritize configuration settings: CLI flags > Environment Variables > config.yaml file (e.g., `~/.code-agent/config.yaml`).
*   **Provider/Model Selection:** Allow users to specify the provider and model per request using CLI flags (e.g., `--provider ollama --model llama3`), falling back to configured defaults.
*   **List Providers:** Include a command to list currently configured providers (`code-agent providers list`).

### 2.4 Agent Capabilities

*   **Tool Use:**
    *   **Internal Tools:** Define and use tools implemented in Python for interacting with the local system (e.g., `read_file`, `apply_edit`).
    *   **Native Terminal Tools:** Allow the agent to request the execution of native terminal commands (configurable allowlist, user confirmation required by default).
    *   **Tool Definition:** Use the OpenAI function calling/tool use standard (as supported by the chosen agent framework, ADK).
*   **Rule-Based Guidance:** Allow users to specify custom rules (e.g., "always use TDD", "prefer functional programming style") via config or prompt to influence agent behavior.
*   **Context & Memory:**
    *   Maintain conversation history within interactive sessions for contextual responses.
    *   (Future) Explore more advanced memory techniques if needed (e.g., summarization, vector stores via ADK).

### 2.5 User Experience

*   **Rich Terminal Output:** Utilize libraries like `rich` for Markdown rendering, syntax highlighting for code, clear diff views, and formatted tables.
*   **Confirmation Prompts:** Implement clear yes/no prompts before executing potentially destructive actions like file editing or command execution.
*   **Session Management:** Manage distinct chat histories for interactive sessions (saving/loading).

### 2.6 Error Handling

*   Handle errors gracefully (API errors, network issues, configuration problems, file access errors, tool execution failures).
*   Provide informative error messages and suggest potential fixes where possible.

## 3. Technology Stack

*   **Programming Language:** Python 3.x (>= 3.10)
*   **Core Agent Framework:** Google Agent Development Kit (`google-adk`)
*   **LLM API Abstraction:** LiteLLM (`litellm`)
*   **CLI Framework:** Typer (`typer`)
*   **Terminal Rendering:** Rich (`rich`)
*   **Configuration Parsing:** PyYAML (`pyyaml`), Pydantic (`pydantic`)
*   **Standard Libraries:** `pathlib`, `subprocess`, `difflib`, `json`, `os`, `datetime`

## 5. Security Considerations

*   **File System Access:** Modifying local files carries inherent risks. The `apply_edit` tool must default to requiring user confirmation, showing a clear diff beforehand. The `--auto-approve` flag (or `auto_approve_edits` config) should be used with extreme caution.
*   **Command Execution:** Executing arbitrary terminal commands suggested by an LLM is highly dangerous. The `run_native_command` tool must default to requiring user confirmation. A configurable `native_command_allowlist` is strongly recommended. Input sanitization (via `shlex.split`) is used. `--auto-approve` for native commands (`auto_approve_native_commands` config) should be used with extreme caution.
*   **API Keys:** Sensitive credentials should be handled securely, preferably loaded from environment variables or a config file with restricted permissions (`~/.code-agent/config.yaml`), not hardcoded. 