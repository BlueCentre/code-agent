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
    file_system["Local File System<br>Stores files and configuration."]
    terminal["Terminal Shell<br>Runs native commands."]

    subgraph cli_boundary["Code Agent System"]
        cli_app["CLI Application<br>Python (Typer)<br>Handles user commands, arguments, input/output, history."]
        agent_core["Agent Core<br>Python<br>Orchestrates LLM calls, tool definitions, and tool execution logic."]
        config_system["Configuration System<br>Python (Pydantic, PyYAML)<br>Loads, validates, and manages user configuration."]
        tool_modules["Tool Modules<br>Python<br>Implementations for file operations, command execution, and security checks."]
        history_store[(History Store<br>JSON Files<br>Stores chat session history on the local file system.)]
    end

    user --> |"Interacts with<br>CLI (stdin/stdout)"| cli_app

    cli_app --> |"Invokes agent turn with prompt/history"| agent_core
    cli_app --> |"Gets configuration settings"| config_system
    cli_app --> |"Saves/Loads History"| history_store

    agent_core --> |"Gets config for agent behavior, tools, rules"| config_system
    agent_core --> |"Sends requests via LiteLLM<br>HTTPS/API"| llm_providers
    agent_core --> |"Delegates tool execution"| tool_modules

    tool_modules --> |"Gets config for tool behavior (e.g., allowlist)"| config_system
    tool_modules --> |"Reads/Writes files"| file_system
    tool_modules --> |"Executes commands"| terminal
    tool_modules --> |"Performs security checks"| tool_modules
```

## Level 3: Component Diagram (Agent Core and Tools)

This diagram provides a more detailed view of the components within the Agent Core and Tools modules.

```mermaid
flowchart TD
    title["Component diagram for Agent Core and Tools"]

    cli_app["CLI Application<br>cli/main.py"]
    llm_providers["LLM Providers"]
    file_system["Local File System"]
    terminal["Terminal Shell"]
    config_system["Configuration System"]

    subgraph agent_boundary["Agent Core"]
        code_agent["CodeAgent<br>agent/agent.py<br>Manages interaction cycle, message history, and tool dispatch."]
        llm_client["LLM Client<br>llm.py<br>Handles communication with LLM providers via LiteLLM."]
    end

    subgraph tools_boundary["Tool Modules"]
        file_tools["File Tools<br>tools/file_tools.py, simple_tools.py<br>Handles file reading, writing, and editing."]
        command_tools["Command Tools<br>tools/native_tools.py, simple_tools.py<br>Handles command execution and validation."]
        security_tools["Security Tools<br>tools/security.py<br>Performs security checks on file operations and commands."]
        error_utils["Error Utilities<br>tools/error_utils.py<br>Handles error formatting and reporting."]
    end

    cli_app --> |"Invokes run_turn"| code_agent
    code_agent --> |"Makes API requests"| llm_client
    llm_client --> |"Sends API requests"| llm_providers

    code_agent --> |"Invokes tools"| file_tools
    code_agent --> |"Invokes tools"| command_tools

    file_tools --> |"Uses"| security_tools
    command_tools --> |"Uses"| security_tools

    file_tools --> |"Reads/Writes"| file_system
    command_tools --> |"Executes"| terminal

    file_tools --> |"Uses"| error_utils
    command_tools --> |"Uses"| error_utils
    security_tools --> |"Uses"| error_utils

    code_agent --> |"Gets configuration"| config_system
    file_tools --> |"Gets configuration"| config_system
    command_tools --> |"Gets configuration"| config_system
    security_tools --> |"Gets configuration"| config_system
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
