# Code Agent Architecture

This document provides a high-level overview of the Code Agent system architecture using C4 model diagrams rendered with Mermaid.

## Level 1: System Context

This diagram shows the Code Agent system in relation to its users and the external systems it interacts with.

```mermaid
C4Context
    title System Context diagram for Code Agent CLI

    Person(user, "Developer", "Uses the CLI agent for code assistance, file operations, command execution, etc.")

    System_Ext(llm_providers, "LLM Providers", "e.g., OpenAI, Groq, Anthropic, Ollama (via LiteLLM)")
    System_Ext(file_system, "Local File System", "Reads and writes files based on user prompts and confirmation.")
    System_Ext(terminal, "Terminal Shell", "Executes native commands based on user prompts and confirmation.")

    System(code_agent_system, "Code Agent CLI", "Provides AI assistance and local interaction capabilities in the terminal.")

    Rel(user, code_agent_system, "Uses")
    Rel(code_agent_system, llm_providers, "Gets completions from", "HTTPS/API")
    Rel(code_agent_system, file_system, "Reads/Writes", "File I/O")
    Rel(code_agent_system, terminal, "Executes commands in", "subprocess")
```

## Level 2: Container Diagram

This diagram decomposes the Code Agent system into its key deployable/runnable components (containers in the C4 sense).

```mermaid
C4Container
    title Container diagram for Code Agent CLI

    Person(user, "Developer", "Uses the CLI via terminal.")
    System_Ext(llm_providers, "LLM Providers", "Handles language model requests.")
    System_Ext(file_system, "Local File System", "Stores files and configuration.")
    System_Ext(terminal, "Terminal Shell", "Runs native commands.")

    System_Boundary(cli_boundary, "Code Agent System") {
        Container(cli_app, "CLI Application", "Python (Typer)", "Handles user commands, arguments, input/output, history.")
        Container(agent_core, "Agent Core", "Python (ADK)", "Orchestrates LLM calls, tool definitions, and tool execution logic.")
        Container(config_loader, "Config Loader", "Python (PyYAML, Pydantic)", "Loads and validates configuration from file/env.")
        Container(tool_executor, "Tool Executor", "Python (Functions)", "Contains implementations for file I/O and native command execution.")
        ContainerDb(history_store, "History Store", "JSON Files", "Stores chat session history on the local file system.")
    }

    Rel(user, cli_app, "Interacts with", "CLI (stdin/stdout)")

    Rel(cli_app, agent_core, "Invokes agent turn with prompt/history", "Python API")
    Rel(cli_app, config_loader, "Gets config for overrides (future)")
    Rel(cli_app, history_store, "Saves/Loads History")

    Rel(agent_core, config_loader, "Gets config for agent behavior, tools, rules")
    Rel(agent_core, llm_providers, "Sends requests via ADK/LiteLLM", "HTTPS/API")
    Rel(agent_core, tool_executor, "Delegates tool execution based on LLM response", "Python API")

    Rel(tool_executor, config_loader, "Gets config for tool behavior (e.g., allowlist)")
    Rel(tool_executor, file_system, "Reads/Writes files (apply_edit, read_file)")
    Rel(tool_executor, terminal, "Executes commands (run_native_command)")

```

*Note: ADK itself handles some internal communication with LLM providers and potentially tool execution flow, which isn't fully detailed at this container level.*

## Level 3: Component Diagram (Agent Core - Simplified)

This diagram provides a glimpse into the components within the `Agent Core` container.

```mermaid
C4Component
    title Component diagram for Agent Core

    Container(cli_app, "CLI Application")
    System_Ext(llm_providers, "LLM Providers")
    Container(tool_executor, "Tool Executor")
    Container(config_loader, "Config Loader")

    Container_Boundary(agent_boundary, "Agent Core") {
        Component(agent_runner, "Agent Runner", "agent.py", "Initializes ADK agent, passes history/prompt, invokes run.")
        Component(adk_agent, "ADK Agent", "google.adk.agents.Agent", "Manages interaction cycle, LLM calls, tool dispatch.")
        Component(adk_runtime, "ADK Runtime", "google.adk.runtime.phidata_runtime", "Executes the agent run cycle, handling async/sync logic.")

        Rel(agent_runner, adk_runtime, "Uses to run agent")
        Rel(agent_runner, config_loader, "Gets config for initialization")
        Rel(adk_runtime, adk_agent, "Executes")
        Rel(adk_agent, llm_providers, "Sends API requests")
        Rel(adk_agent, tool_executor, "Requests tool execution") # ADK decides when to call tools
    }

    Rel(cli_app, agent_runner, "Invokes run_agent_turn")

``` 