Google Doc Content: CLI Agent Project Plan
1. Introduction & Vision
This document outlines the plan for building a versatile Command-Line Interface (CLI) agent designed to enhance developer productivity and interaction with AI models.
Vision: To create a powerful, flexible CLI tool that allows users to leverage various AI language models for tasks such as code generation, explanation, refactoring, terminal command assistance, and general question answering, directly within their terminal environment.
Core Goal: Provide a unified interface to interact with multiple AI model providers (supporting the OpenAI API standard) and empower the agent with capabilities to interact with the user's local environment (files, terminal commands) in a controlled and secure manner.
Key Differentiators:
Multi-Provider Support: Seamlessly switch between different LLM providers (OpenAI, Groq, Ollama, Anthropic, Azure OpenAI, AI Studio, etc.) using LiteLLM.
Agentic Capabilities: Go beyond simple Q&A to perform actions like editing local files (with user consent) and executing terminal commands (securely).
Flexible Configuration: Allow users to configure API keys, default models, and agent behavior via CLI arguments, environment variables, and a dedicated configuration file.
Dual Interaction Modes: Support both quick, single-shot commands and persistent interactive chat sessions.
2. Core Requirements
2.1 Functionality
Code Assistance: Generate code snippets, explain existing code, refactor code based on prompts.
Command-Line Assistance: Suggest relevant terminal commands, execute commands (with user consent).
General Q&A: Answer general knowledge or technical questions.
File Editing: Propose changes to local files, display differences (diffs), and apply edits only after explicit user confirmation or if an auto-approve flag is enabled.
2.2 Interaction Modes
Single-Shot Command: Execute a specific prompt and exit (e.g., code-agent --model gpt-4o "Refactor this python code" < file.py).
Interactive Chat: Start a persistent session where conversation history is maintained (e.g., code-agent chat).
2.3 Model Provider Management
Multi-Provider Integration: Utilize LiteLLM to connect to any OpenAI API-compatible endpoint.
Configuration Hierarchy: Prioritize configuration settings: CLI flags > Environment Variables > config.yaml file (e.g., ~/.code-agent/config.yaml).
Provider/Model Selection: Allow users to specify the provider and model per request using CLI flags (e.g., --provider ollama --model llama3), falling back to configured defaults.
List Providers: Include a command to list currently configured providers (code-agent providers list).
2.4 Agent Capabilities
Tool Use:
Internal Tools: Define and use tools implemented in Python for interacting with the local system (e.g., read_file, write_file, apply_edit).
Native Terminal Tools: Allow the agent to request the execution of native terminal commands (configurable allowlist, user confirmation required by default).
Tool Definition: Use the OpenAI function calling/tool use standard for defining tools.
Rule-Based Guidance: Allow users to specify custom rules (e.g., "always use TDD", "prefer functional programming style") via config or prompt to influence agent behavior.
Context & Memory:
Maintain conversation history within interactive sessions for contextual responses.
(Future) Explore more advanced memory techniques if needed (e.g., summarization, vector stores via ADK).
2.5 User Experience
Rich Terminal Output: Utilize libraries like rich for Markdown rendering, syntax highlighting for code, clear diff views, and formatted tables.
Confirmation Prompts: Implement clear yes/no prompts before executing potentially destructive actions like file editing or command execution.
Session Management: Manage distinct chat histories for interactive sessions.
2.6 Error Handling
Handle errors gracefully (API errors, network issues, configuration problems, file access errors, tool execution failures).
Provide informative error messages and suggest potential fixes where possible.
3. Technology Stack
Programming Language: Python 3.x
Core LLM Interaction Framework: LiteLLM (litellm)
CLI Framework: Typer (typer)
Terminal Rendering: Rich (rich)
Configuration Parsing: PyYAML (pyyaml)
Standard Libraries: pathlib, subprocess, difflib, json, os, sqlite3 (optional, for history)
4. Implementation Plan (Step-by-Step)
✅ Project Setup & Foundation:
✅ Create directory structure (code-agent/cli, code-agent/agent, code-agent/config, code-agent/tools, tests/).
✅ Initialize Git repository.
✅ Set up pyproject.toml or requirements.txt, create virtual environment, install base dependencies (typer, litellm, pyyaml, rich).
✅ Configuration Management:
✅ Define config.yaml structure.
✅ Implement config.py to load settings with the defined hierarchy (CLI > Env > File).
✅ Implement validation for essential configuration.
✅ Basic CLI Structure (Typer):
✅ Set up main entry point (cli.py).
✅ Define basic commands (--version, config show, providers list).
✅ Parse global options (--provider, --model).
✅ Core LLM Interaction (LiteLLM):
✅ Create llm.py wrapper around litellm.completion.
✅ Implement a basic single-shot command (code-agent run "prompt") that takes a prompt, uses the config/LLM wrapper, and prints the raw LLM response.
✅ Agent Architecture:
✅ Structure the LLM call within a structured agent class (CodeAgent).
✅ Pass user input, configuration, and system prompt to the agent.
✅ Interactive Chat Mode:
✅ Implement code-agent chat command using a loop.
✅ Implement basic in-memory history tracking within the agent state.
✅ Implement saving/loading history to a file (e.g., JSON) per session.
✅ Use rich for formatted input/output.
✅ Output Formatting:
✅ Integrate rich for Markdown rendering and code syntax highlighting in both single-shot and chat modes.
✅ Tool Use - Internal Tools (File I/O):
✅ Define read_file(path) tool.
✅ Format tool definition for OpenAI standard.
✅ Update agent logic to pass tool definitions to LLM.
✅ Implement handling of tool_calls response: parse request, execute read_file, return result to LLM.
✅ Tool Use - File Editing:
✅ Define apply_edit(path, proposed_content) tool (or similar).
✅ Implement logic: calculate diff (difflib), display diff (rich), prompt for confirmation (y/n), apply changes if confirmed or --auto-approve.
✅ Handle file errors robustly.
✅ Tool Use - Native Commands (Secure Execution):
✅ Define run_native_command(command_string) tool.
✅ Implement SECURE execution: USER CONFIRMATION (default), subprocess execution, capture output, return result.
✅ Implement configurable command allowlist in config.yaml.
✅ Rule-Based Guidance:
✅ Load rules from config/CLI.
✅ Inject rules into the system prompt passed to the LLM.
✅ Multi-Provider Support:
✅ Add specific support for AI Studio APIs
✅ Configure API base URLs for different providers
✅ Implement provider-specific model string formatting
✅ Refinement & Error Handling:
✅ Add comprehensive try...except blocks for API calls, file ops, tool execution.
✅ Improve user feedback (e.g., loading states).
✅ Write tests (unit/integration).
⏳ Documentation & Packaging:
✅ Create README.md (setup, config, usage).
✅ Set up packaging using pyproject.toml and build/pip.
⏳ Maintain docs/ directory with implementation progress.
5. Security Considerations
File System Access: Modifying local files carries inherent risks. The apply_edit tool must default to requiring user confirmation, showing a clear diff beforehand. The --auto-approve flag should be used with extreme caution.
Command Execution: Executing arbitrary terminal commands suggested by an LLM is highly dangerous. The run_native_command tool must default to requiring user confirmation. A configurable allowlist for permitted commands is strongly recommended. Input sanitization should be considered. --auto-approve for native commands should be strongly discouraged or require a separate explicit flag.
API Keys: Sensitive credentials should be handled securely, preferably loaded from environment variables or a config file with restricted permissions, not hardcoded.
6. Future Enhancements
Advanced long-term memory using vector databases.
More sophisticated dynamic tool discovery.
Integration with IDEs or other development tools.
A plugin system for community contributions (custom tools, providers).
(Further out) A graphical user interface (GUI).
