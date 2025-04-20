# Code Agent Architecture

This document provides a high-level overview of the Code Agent system architecture using C4 model diagrams rendered with Mermaid.

## Level 1: System Context

This diagram shows the Code Agent system in relation to its users and the external systems it interacts with.

```mermaid
flowchart TD
    title["System Context diagram for Code Agent CLI"]

    user["Developer<br>Uses the CLI agent for code assistance, file operations, command execution, etc."]

    llm_providers["LLM Providers<br>e.g., OpenAI, Groq, Anthropic, Ollama (via LiteLLM)"]
    file_system["Local File System<br>Reads and writes files based on user prompts and confirmation."]
    terminal["Terminal Shell<br>Executes native commands based on user prompts and confirmation."]

    code_agent_system["Code Agent CLI<br>Provides AI assistance and local interaction capabilities in the terminal."]

    user --> |"Uses"| code_agent_system
    code_agent_system --> |"Gets completions from<br>HTTPS/API"| llm_providers
    code_agent_system --> |"Reads/Writes<br>File I/O"| file_system
    code_agent_system --> |"Executes commands in<br>subprocess"| terminal
```

## Level 2: Container Diagram

This diagram decomposes the Code Agent system into its key deployable/runnable components (containers in the C4 sense).

```mermaid
flowchart TD
    title["Container diagram for Code Agent CLI"]

    user["Developer<br>Uses the CLI via terminal."]
    llm_providers["LLM Providers<br>Handles language model requests."]
    file_system["Local File System<br>Stores files and configuration."]
    terminal["Terminal Shell<br>Runs native commands."]

    subgraph cli_boundary["Code Agent System"]
        cli_app["CLI Application<br>Python (Typer)<br>Handles user commands, arguments, input/output, history."]
        agent_core["Agent Core<br>Python (ADK)<br>Orchestrates LLM calls, tool definitions, and tool execution logic."]
        config_loader["Config Loader<br>Python (PyYAML, Pydantic)<br>Loads and validates configuration from file/env."]
        tool_executor["Tool Executor<br>Python (Functions)<br>Contains implementations for file I/O and native command execution."]
        history_store[(History Store<br>JSON Files<br>Stores chat session history on the local file system.)]
    end

    user --> |"Interacts with<br>CLI (stdin/stdout)"| cli_app

    cli_app --> |"Invokes agent turn with prompt/history<br>Python API"| agent_core
    cli_app --> |"Gets config for overrides (future)"| config_loader
    cli_app --> |"Saves/Loads History"| history_store

    agent_core --> |"Gets config for agent behavior, tools, rules"| config_loader
    agent_core --> |"Sends requests via ADK/LiteLLM<br>HTTPS/API"| llm_providers
    agent_core --> |"Delegates tool execution based on LLM response<br>Python API"| tool_executor

    tool_executor --> |"Gets config for tool behavior (e.g., allowlist)"| config_loader
    tool_executor --> |"Reads/Writes files (apply_edit, read_file)"| file_system
    tool_executor --> |"Executes commands (run_native_command)"| terminal
```

*Note: ADK itself handles some internal communication with LLM providers and potentially tool execution flow, which isn't fully detailed at this container level.*

## Level 3: Component Diagram (Agent Core - Simplified)

This diagram provides a glimpse into the components within the `Agent Core` container.

```mermaid
flowchart TD
    title["Component diagram for Agent Core"]

    cli_app["CLI Application"]
    llm_providers["LLM Providers"]
    tool_executor["Tool Executor"]
    config_loader["Config Loader"]

    subgraph agent_boundary["Agent Core"]
        agent_runner["Agent Runner<br>agent.py<br>Initializes ADK agent, passes history/prompt, invokes run."]
        adk_agent["ADK Agent<br>google.adk.agents.Agent<br>Manages interaction cycle, LLM calls, tool dispatch."]
        adk_runtime["ADK Runtime<br>google.adk.runtime.phidata_runtime<br>Executes the agent run cycle, handling async/sync logic."]

        agent_runner --> |"Uses to run agent"| adk_runtime
        agent_runner --> |"Gets config for initialization"| config_loader
        adk_runtime --> |"Executes"| adk_agent
        adk_agent --> |"Sends API requests"| llm_providers
        adk_agent --> |"Requests tool execution"| tool_executor
    end

    cli_app --> |"Invokes run_agent_turn"| agent_runner
``` 