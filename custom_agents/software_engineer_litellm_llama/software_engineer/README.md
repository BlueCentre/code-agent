# Software Engineer Agent (LiteLLM - Multi-Model Compatible)

This agent uses LiteLLM to provide software engineering assistance with multi-model compatibility, supporting both Gemini and LLaMA models.

## Model Compatibility

This agent is designed to work with different LLM backends with specific adaptations for cross-model compatibility:

### Key Compatibility Features

1. **Flexible Tool Arguments**
   - Tool functions handle both dictionary and string arguments
   - Includes argument parsing utilities to handle model-specific formats
   - String-to-boolean conversion for handling "true"/"false" string literals

2. **Tool Discovery Mechanism**
   - LLaMA models often try to call discovery functions like `list_available_tools` before using tools
   - Gemini models typically work with directly registered tools
   - Solution: Implemented a flexible tool discovery system with multiple aliases:
     - `list_available_tools_tool` (primary name)
     - `list_tools_tool` (shorter alias)
     - `available_tools_tool` (another common variation)

3. **Clear Tool Documentation**
   - Explicit tool listing in the prompt instructions
   - Comprehensive tool descriptions
   - Instructions to avoid discovery calls when possible

### Implementation Details

#### Tool Discovery Function

The tool discovery function returns a structured listing of all available tools:

```python
def list_available_tools(args: dict, tool_context: ToolContext) -> Dict[str, Any]:
    """Lists all available tools in the agent."""
    tools = {
        "file_system_tools": { ... },
        "shell_command_tools": { ... },
        "search_tools": { ... },
        "system_info_tools": { ... }
    }
    
    return {
        "tools": tools,
        "message": "Use these tools directly by calling them with appropriate arguments."
    }
```

#### Registered with Multiple Aliases

```python
# Primary tool
list_available_tools_tool = FunctionTool(list_available_tools)

# Aliases for different naming conventions
list_tools_tool = list_available_tools_tool
available_tools_tool = list_available_tools_tool
```

## Tool Categories

The agent provides tools in several categories:

1. **File System Tools**: Read, list, edit files and configure approval requirements
2. **Shell Command Tools**: Execute shell commands with safety checks and approval settings
3. **Search Tools**: Search the web and codebase
4. **System Info Tools**: Get OS information and list available tools

## Usage

To run this agent with a specific model:

```bash
uv run code-agent run "-" custom_agents/software_engineer_litellm_llama/software_engineer
```

The agent is configured to use LiteLLM which provides a unified interface to many LLM backends.

### Key Benefits

- Works with both Gemini and LLaMA models without modifications
- Handles different argument formats transparently
- Provides tool discovery for models that require it
- Maintains backward compatibility with existing code 