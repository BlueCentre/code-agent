# Code Agent Architecture

This document provides a high-level overview of the Code Agent system architecture using C4 model diagrams rendered with Mermaid.

## Level 1: System Context

This diagram shows the Code Agent system in relation to its users and the external systems it interacts with.

```mermaid
flowchart TD
    title["System Context diagram for Code Agent CLI"]

    user["Developer<br>Uses the CLI agent for code assistance, file operations, command execution, etc."]

    llm_providers["LLM Providers<br>e.g., OpenAI, Groq, Anthropic, Google AI Studio, Ollama (via LiteLLM)"]
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
    ollama["Ollama<br>Local LLM service (Optional)."]
    file_system["Local File System<br>Stores files and configuration."]
    terminal["Terminal Shell<br>Runs native commands."]
    litellm_lib["LiteLLM Library<br>Provides unified API to LLM Providers."]

    subgraph cli_boundary["Code Agent System"]
        cli_app["CLI Application<br>Python (Typer)<br>Handles user commands (chat, config, ollama), args, I/O, history."]
        agent_core["Agent Core (ADK)<br>Python (google-adk)<br>Orchestrates LLM calls via LiteLLM, tool definitions, and tool execution logic."]
        config_system["Configuration System<br>Python (Pydantic, PyYAML)<br>Loads, validates, and manages user configuration."]
        tool_modules["Tool Modules<br>Python<br>Implementations for file ops, command exec, search, memory, security checks."]
        history_store[(History Store<br>JSON Files<br>Stores chat session history on the local file system.)]
    end

    user --> |"Interacts with<br>CLI (stdin/stdout)"| cli_app

    cli_app --> |"Invokes agent turn (chat cmd)"| agent_core
    cli_app --> |"Gets configuration settings"| config_system
    cli_app --> |"Saves/Loads History"| history_store
    cli_app --> |"Direct Ollama commands<br>HTTP API"| ollama

    agent_core --> |"Gets config for agent behavior, tools, rules"| config_system
    agent_core --> |"Sends requests via"| litellm_lib
    litellm_lib --> |"HTTPS/API"| llm_providers
    agent_core --> |"Delegates tool execution"| tool_modules

    tool_modules --> |"Gets config for tool behavior (e.g., allowlist)"| config_system
    tool_modules --> |"Reads/Writes files"| file_system
    tool_modules --> |"Executes commands"| terminal
```

## Level 2.5: E2E Testing with `adk run`

This level focuses specifically on the End-to-End testing scenario executed by scripts like `scripts/run_e2e_tests.sh`, which typically invoke the agent via the `adk run` command-line tool multiple times.

### Current E2E Testing Limitation (InMemoryMemoryService)

This diagram illustrates why testing cross-session memory recall fails with the default `InMemoryMemoryService` in the current E2E setup. Each `adk run` invocation is a separate process, and the in-memory service does not persist between them.

```mermaid
flowchart TD
    title["E2E Testing - Current State with InMemoryMemoryService"]

    user["Test Script<br>(e.g., run_e2e_tests.sh)"]

    subgraph run1 ["Invocation 1: 'adk run ...'"]
        agent1["Agent Process 1"]
        mem1["InMemoryMemoryService<br>(Ephemeral, Process-local)"]
        agent1 --- mem1
    end

    subgraph run2 ["Invocation 2: 'adk run ...'"]
        agent2["Agent Process 2"]
        mem2["InMemoryMemoryService<br>(Ephemeral, Process-local)"]
        agent2 --- mem2
    end

    user --> |"Executes"| run1
    user --> |"Executes"| run2
    note[Memory is lost between invocations]

    style run1 fill:#f9f,stroke:#333,stroke-width:2px
    style run2 fill:#f9f,stroke:#333,stroke-width:2px
    style mem1 fill:#ff9,stroke:#333,stroke-width:1px
    style mem2 fill:#ff9,stroke:#333,stroke-width:1px
```

### Future E2E Testing (Persistent MemoryService)

This diagram shows the target architecture for enabling cross-session memory testing in the E2E scripts. A persistent `MemoryService` (like `VertexAiRagMemoryService`) is shared across different `adk run` invocations.

```mermaid
flowchart TD
    title["E2E Testing - Future State with Persistent MemoryService"]

    user["Test Script<br>(e.g., run_e2e_tests.sh)"]
    shared_mem["Persistent MemoryService<br>(e.g., Vertex AI RAG Corpus)<br>Shared across invocations"]

    subgraph run1 ["Invocation 1: 'adk run ...'"]
        agent1["Agent Process 1"]
    end

    subgraph run2 ["Invocation 2: 'adk run ...'"]
        agent2["Agent Process 2"]
    end

    user --> |"Executes"| run1
    user --> |"Executes"| run2

    agent1 --> |"Reads/Writes<br>via Runner/Tools"| shared_mem
    agent2 --> |"Reads/Writes<br>via Runner/Tools"| shared_mem

    style run1 fill:#f9f,stroke:#333,stroke-width:2px
    style run2 fill:#f9f,stroke:#333,stroke-width:2px
    style shared_mem fill:#9cf,stroke:#333,stroke-width:2px
```

## Level 3: Component Diagram (Agent Core and Tools)

This diagram provides a more detailed view of the components within the Agent Core and Tools modules.

```mermaid
flowchart TD
    title["Component diagram for Agent Core and Tools"]

    cli_app["CLI Application<br>cli/main.py"]
    llm_providers["LLM Providers"]
    ollama["Ollama Local Service"]
    file_system["Local File System"]
    terminal["Terminal Shell"]
    config_system["Configuration System"]
    litellm_lib["LiteLLM Library"]

    subgraph agent_boundary["Agent Core (ADK)"]
        code_agent["Agent Logic<br>agent/*, adk/*<br>Manages ADK agent execution, history, tool dispatch."]
    end

    subgraph cli_commands_boundary["CLI Commands"]
        ollama_commands["Ollama Commands<br>cli/commands/ollama.py<br>Handles `ollama list/chat`."]
        config_commands["Config Commands<br>cli/commands/config.py<br>Handles `config show/reset`."]
        providers_commands["Providers Command<br>cli/commands/providers.py<br>Handles `providers list`."]
    end

    subgraph tools_boundary["Tool Modules (ADK Tools)"]
        file_tools["File Tools<br>adk/tools.py (wraps tools/fs_tool.py)<br>read_file, apply_edit, delete_file, list_dir."]
        command_tools["Command Tool<br>adk/tools.py (wraps tools/native_tool.py)<br>run_terminal_cmd."]
        memory_tools["Memory Tool<br>adk/tools.py (uses adk/memory.py)<br>load_memory."]
        search_tools["Search Tools<br>adk/tools.py<br>google_search (via ADK built-in)."]
    end

    cli_app --> |"Invokes run_turn (chat cmd)"| code_agent
    cli_app --> |"Invokes subcommands"| ollama_commands
    cli_app --> |"Invokes subcommands"| config_commands
    cli_app --> |"Invokes subcommands"| providers_commands

    ollama_commands --> |"HTTP API Requests"| ollama

    code_agent --> |"Makes LLM requests via"| litellm_lib
    litellm_lib --> |"Sends API requests"| llm_providers

    code_agent --> |"Invokes ADK tools"| file_tools
    code_agent --> |"Invokes ADK tools"| command_tools
    code_agent --> |"Invokes ADK tools"| memory_tools
    code_agent --> |"Invokes ADK tools"| search_tools

    file_tools --> |"Reads/Writes"| file_system
    command_tools --> |"Executes"| terminal

    code_agent --> |"Gets configuration"| config_system
    file_tools --> |"Gets configuration"| config_system
    command_tools --> |"Gets configuration"| config_system
    memory_tools --> |"Gets configuration"| config_system
    ollama_commands --> |"Gets configuration"| config_system
```

## Level 4: Configuration System Components

This diagram shows the components of the Configuration System and how they interact.

```mermaid
flowchart TD
    title["Component diagram for Configuration System"]

    user["User"]
    file_system["File System"]
    agent_core["Agent Core"]
    tool_modules["Tool Modules"]

    subgraph config_boundary["Configuration System"]
        config_loader["Config Loader<br>config/__init__.py<br>Provides access to configuration."]
        settings_config["Settings Config<br>config/settings_based_config.py<br>Defines the configuration structure using Pydantic."]
        config_validation["Config Validation<br>config/validation.py<br>Validates configuration values."]
        config_handler["Config Handler<br>config/config.py<br>Loads configuration from file and environment."]
    end

    user --> |"Creates/Edits"| file_system
    file_system --> |"Stores config files"| config_handler

    agent_core --> |"Gets configuration"| config_loader
    tool_modules --> |"Gets configuration"| config_loader

    config_loader --> |"Uses"| settings_config
    settings_config --> |"Uses"| config_validation
    config_handler --> |"Uses"| settings_config
    config_loader --> |"Uses"| config_handler
```
