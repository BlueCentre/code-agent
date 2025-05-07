"""
Tools for getting system information.

NOTE: This is needed for LiteLLM models in order to use the FunctionTool.
"""

import logging
import platform
from typing import Any, Dict

from google.adk.tools import FunctionTool, ToolContext
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OSInfoOutput(BaseModel):
    """Output model for the get_os_info tool."""

    system: str = Field(description="Operating system name (e.g., 'Linux', 'Darwin', 'Windows').")
    release: str = Field(description="Operating system release (e.g., '5.15.0-78-generic').")
    version: str = Field(description="Operating system version.")
    machine: str = Field(description="Machine hardware name (e.g., 'x86_64').")


def get_os_info(args: dict, tool_context: ToolContext) -> Dict[str, Any]:
    """Gets information about the operating system.

    Args:
        args: Does not require any arguments.
        tool_context: The tool context.

    Returns:
        A dictionary with information about the operating system.
    """
    os_info = {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    return {"os_info": os_info}


def list_available_tools(args: dict, tool_context: ToolContext) -> Dict[str, Any]:
    """Lists all available tools in the agent.

    Args:
        args: Arguments (not used)
        tool_context: The tool context

    Returns:
        Dictionary containing the list of available tools and their descriptions
    """
    # List all tools registered with the agent
    tools = {
        "file_system_tools": {
            "read_file_tool": "Reads the content of a file",
            "list_dir_tool": "Lists the contents of a directory",
            "edit_file_tool": "Edits or creates a file",
            "configure_edit_approval_tool": "Configures whether file edits require approval",
        },
        "shell_command_tools": {
            "check_command_exists_tool": "Checks if a command exists in the system",
            "check_shell_command_safety_tool": "Checks if a shell command is safe to run",
            "configure_shell_approval_tool": "Configures approval requirements for shell commands",
            "configure_shell_whitelist_tool": "Manages the whitelist of shell commands",
            "execute_vetted_shell_command_tool": "Executes a vetted shell command",
        },
        "search_tools": {"google_search_grounding": "Searches the web for information", "codebase_search_tool": "Searches for code in the codebase"},
        "system_info_tools": {
            "get_os_info_tool": "Gets information about the operating system",
            "list_available_tools_tool": "Lists all available tools in the agent",
        },
    }

    return {"tools": tools, "message": "Use these tools directly by calling them with appropriate arguments. No need to discover them first."}


# Wrap get_os_info with FunctionTool
get_os_info_tool = FunctionTool(get_os_info)
list_available_tools_tool = FunctionTool(list_available_tools)

# Add aliases for different naming conventions that various models might use
list_tools_tool = list_available_tools_tool  # Alias for shorter name
available_tools_tool = list_available_tools_tool  # Another common name
