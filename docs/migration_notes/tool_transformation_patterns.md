# ADK Tool Transformation Patterns

This document outlines the patterns and strategies used for transforming existing tool functions to work with Google ADK.

## General Transformation Pattern

When migrating tools to ADK, the following pattern should be followed:

1. **Create a wrapper function** that accepts `tool_context` as its first parameter
2. **Call the original implementation** from within the wrapper
3. **Add logging** using the context logger
4. **Return the same result** as the original function
5. **Create a factory function** that returns an ADK `FunctionTool` instance

## Specific Patterns

### Simple Function Transformation

For simple functions like `read_file`, `delete_file`, etc.:

```python
# Original function
def original_function(param1, param2, ...):
    # Original implementation
    return result

# ADK wrapper
def adk_function(tool_context, param1, param2, ...):
    """
    Function docstring with detailed information.
    
    Args:
        tool_context: The ADK ToolContext
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    # Log the operation
    tool_context.logger.info(f"Starting operation with {param1}")
    
    # Call the original implementation
    result = original_function(param1, param2, ...)
    
    # Log the result
    if "Error" in result:
        tool_context.logger.error(f"Operation failed: {param1}")
    else:
        tool_context.logger.info(f"Operation successful: {param1}")
    
    return result

# Factory function
def create_adk_function_tool():
    """Creates an ADK FunctionTool for the function."""
    return FunctionTool(
        func=adk_function,
    )
```

### Security and Path Handling

When working with file paths, be aware that:

1. Original functions typically include security checks to verify paths
2. For testing, we need to mock these security checks:
   - Mock `code_agent.tools.file_tools.is_path_safe`
   - Mock `code_agent.tools.simple_tools.is_path_within_cwd`

## Tool Categories and Implementation Status

| Tool Category | Tool Name | Status | Implementation |
|---------------|-----------|--------|----------------|
| File Operations | `read_file` | Completed | `code_agent/adk/tools.py` |
| File Operations | `delete_file` | Completed | `code_agent/adk/tools.py` |
| File Operations | `apply_edit` | Completed | `code_agent/adk/tools.py` |
| File Operations | `list_dir` | To be implemented | - |
| File Operations | `file_search` | To be implemented | - |
| Code Analysis | `codebase_search` | To be implemented | - |
| Code Analysis | `grep_search` | To be implemented | - |
| Terminal | `run_terminal_cmd` | To be implemented | - |
| Web | `web_search` | To be implemented | - |

## Testing Strategies

1. **Sandbox Testing**: Use `sandbox/adk_test_tools.py` to manually test tool functionality
2. **Unit Testing**: Create proper unit tests with mocks in `tests/unit/test_adk_tools.py`
3. **Security Mocking**: Always mock security checks when testing to avoid path restrictions

## Lessons Learned

1. The `ToolContext` parameter must be of type `ToolContext` imported from `google.adk.tools`
2. ADK `FunctionTool` uses `func` parameter rather than `function`
3. File path security checks need to be mocked for testing
4. Tests should check for both successful and error cases
5. Multiple security checks may need to be mocked depending on which implementation is being used

## Next Steps

1. Implement additional Category 1 tools
2. Move on to Category 2 tools once Category 1 tools are all completed
3. Update this document with new patterns as they emerge 