# Code Agent Implementation Plan & Roadmap

This document outlines the implementation steps taken and the future roadmap.

## Implementation Steps (Based on Initial Plan)

*   [x] **Project Setup & Foundation:**
    *   [x] Create directory structure (`code-agent/cli`, `code-agent/agent`, `code-agent/config`, `code-agent/tools`, `tests/`).
    *   [x] Initialize Git repository.
    *   [x] Set up `pyproject.toml` with Poetry.
    *   [x] Create virtual environment (`.venv`).
    *   [x] Install base dependencies (`typer`, `litellm`, `pyyaml`, `rich`, `google-adk`, `pydantic`).
*   [x] **Configuration Management:**
    *   [x] Define `config.yaml` structure (`~/.code-agent/config.yaml`).
    *   [x] Implement `config.py` to load settings (File > Env > Defaults - *Note: CLI override not fully implemented yet*).
    *   [x] Implement validation using Pydantic.
*   [x] **Basic CLI Structure (Typer):**
    *   [x] Set up main entry point (`code_agent/cli/main.py`).
    *   [x] Define basic commands (`--version`, `config show`, `providers list`).
    *   [x] Parse global options (`--provider`, `--model`).
*   [x] **Core LLM Interaction (LiteLLM):**
    *   [x] Create `llm.py` wrapper around `litellm.completion` (Initially used, now superseded by ADK agent).
    *   [x] Implement basic single-shot command (`code-agent run "prompt"`) using LiteLLM initially.
*   [x] **ADK Integration (Basic Agent):**
    *   [x] Structure the LLM call within an ADK `Agent` (`code_agent/agent/agent.py`).
    *   [x] Pass user input, configuration (implicitly via imports), and system prompt to the agent.
    *   [x] Updated `code-agent run` to use the ADK agent.
*   [x] **Interactive Chat Mode:**
    *   [x] Implement `code-agent chat` command using a loop.
    *   [x] Implement basic in-memory history tracking.
    *   [x] Implement saving/loading history to timestamped JSON files (`~/.code-agent/history/`).
    *   [x] Use `rich` for formatted input/output.
*   [x] **Output Formatting:**
    *   [x] Integrate `rich` for Markdown rendering and code syntax highlighting in both single-shot and chat modes.
*   [x] **Tool Use - Internal Tools (File I/O):**
    *   [x] Define `read_file(path)` tool (`code_agent/tools/file_tools.py`).
    *   [x] Format tool definition for ADK (`@function_tool`).
    *   [x] Update agent logic to pass tool definitions to `Agent`.
    *   [x] Update agent instruction.
    *   [x] Rely on ADK runtime to handle tool execution loop.
*   [x] **Tool Use - File Editing:**
    *   [x] Define `apply_edit(path, proposed_content)` tool (`code_agent/tools/file_tools.py`).
    *   [x] Implement logic: calculate diff (`difflib`), display diff (`rich`), prompt for confirmation (`rich.prompt.Confirm`), apply changes if confirmed or `auto_approve_edits` is set.
    *   [x] Handle file errors.
    *   [x] Add tool to agent and update instruction.
*   [x] **Tool Use - Native Commands (Secure Execution):**
    *   [x] Define `run_native_command(command_string)` tool (`code_agent/tools/native_tools.py`).
    *   [x] Implement security: Check `native_command_allowlist`, prompt for confirmation (respecting `auto_approve_native_commands`), use `subprocess.run` safely (`shlex.split`), capture output.
    *   [x] Add tool to agent and update instruction.
*   [x] **Rule-Based Guidance:**
    *   [x] Load rules from `config.yaml`.
    *   [x] Inject rules into the system prompt passed to the ADK `Agent`.
*   [x] **Refinement & Error Handling:**
    *   [x] Add some `try...except` blocks for API calls, file ops, tool execution.
    *   [x] Add basic user feedback (`rich.status`).
    *   [x] Write initial unit tests (`pytest`) for config and tools.
    *   [x] Write initial integration tests for CLI (`typer.testing.CliRunner`).
*   [x] **Documentation & Packaging:**
    *   [x] Create `README.md` with setup, config, usage.
    *   [x] Set up packaging using `pyproject.toml` and Poetry.
    *   [x] Create initial `docs` folder structure.

## Roadmap / Next Steps

*   **Testing:** 
    *   Improve test coverage, especially for edge cases in tools.
    *   Implement integration tests for the `chat` command (mocking input/output).
    *   Test ADK interaction with mocked LLM responses/tool calls.
*   **Error Handling:** Refine error handling and user feedback for API errors, tool failures, configuration issues, and ADK runtime errors.
*   **Configuration Hierarchy:** Fully implement the CLI > Env > File hierarchy for all relevant configuration options (e.g., auto-approve flags, rules).
*   **ADK Integration:** 
    *   Verify and potentially refine the handling of conversational history within the ADK agent structure.
    *   Investigate ADK's built-in memory features as an alternative to manual history passing.
    *   Confirm robust integration with LiteLLM provider strings.
*   **Tool Refinement:** 
    *   Enhance security checks for `apply_edit` and `run_native_command` (e.g., stricter path validation, absolute path handling, more robust allowlist matching).
    *   Add size limits to `read_file`.
*   **Chat History:** Add option to load specific history files or clear history.
*   **Packaging & Distribution:** Finalize packaging for distribution (e.g., PyPI).
*   **Advanced Features:** Explore optional enhancements like long-term memory, dynamic tool discovery, etc. (See `PLAN.md` section 6). 