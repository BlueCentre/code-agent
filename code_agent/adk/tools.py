"""
ADK tool wrappers for existing code_agent tools.

This module wraps the existing tool functions as ADK FunctionTool instances,
adapting them to work with the Google ADK framework.
"""

from pathlib import Path
from typing import Optional, Any, Callable, Dict, List, Tuple, Union
import os
import logging
import functools
import tempfile

from google.adk.memory import BaseMemoryService
from google.adk.tools import FunctionTool, ToolContext
from google.adk.tools.google_search_tool import google_search

from code_agent.tools.file_tools import ReadFileArgs  # Import the ReadFileArgs class
from code_agent.tools.file_tools import delete_file as original_delete_file
from code_agent.tools.file_tools import read_file as original_read_file
from code_agent.tools.native_tools import run_native_command as original_run_command
from code_agent.tools.simple_tools import apply_edit as original_apply_edit

# from code_agent.tools.memory_tools import load_memory as original_load_memory # Removed
from .services import get_memory_service
from code_agent.config import get_config
from code_agent.tools.verbosity import get_controller

logger = logging.getLogger(__name__)
config = get_config()
verbosity_controller = get_controller()

# --- Read File Tool ---
def read_file(tool_context: ToolContext, path: str, offset: Optional[int] = None, limit: Optional[int] = None, enable_pagination: bool = False) -> str:
    """
    Reads a file and returns its contents.

    Args:
        path: The path of the file to read
        offset: Line number to start reading from (0-indexed)
        limit: Maximum number of lines to read
        enable_pagination: Whether to enable pagination for large files

    Returns:
        The contents of the file as a string or an error message
    """
    # Log the tool execution in the context
    tool_context.logger.info(f"Reading file: {path}")

    # Create a ReadFileArgs instance from the parameters
    args = ReadFileArgs(path=path, offset=offset, limit=limit, enable_pagination=enable_pagination)

    # Call the original implementation with the args object
    result = original_read_file(args)

    # Log the result summary
    if result.startswith("Error:"):
        tool_context.logger.error(f"Failed to read file: {path}")
    else:
        file_size = len(result)
        tool_context.logger.info(f"Successfully read file: {path} ({file_size} bytes)")

    return result


# --- Delete File Tool ---
def delete_file(tool_context: ToolContext, path: str) -> str:
    """
    Deletes a file at the specified path.

    Args:
        path: The path of the file to delete

    Returns:
        Success or error message
    """
    # Log the tool execution in the context
    tool_context.logger.info(f"Deleting file: {path}")

    # Call the original implementation
    result = original_delete_file(path)

    # Log the result
    if result.startswith("Error:"):
        tool_context.logger.error(f"Failed to delete file: {path}")
    else:
        tool_context.logger.info(f"Successfully deleted file: {path}")

    return result


# --- Apply Edit Tool ---
def apply_edit(tool_context: ToolContext, target_file: str, code_edit: str) -> str:
    """
    Applies proposed content changes to a file after showing a diff and requesting user confirmation.

    Args:
        target_file: The path of the file to edit
        code_edit: The proposed content to apply to the file

    Returns:
        Success or error message
    """
    # Log the tool execution in the context
    tool_context.logger.info(f"Applying edit to file: {target_file}")

    # Call the original implementation - it handles confirmation internally based on config
    result = original_apply_edit(target_file, code_edit)

    # Log the result
    if result.startswith("Error:") or result == "Edit cancelled by user.":
        tool_context.logger.warning(f"Edit not applied to file: {target_file}")
    else:
        tool_context.logger.info(f"Successfully edited file: {target_file}")

    return result


# --- List Directory Tool ---
def list_dir(tool_context: ToolContext, relative_workspace_path: str = ".") -> str:
    """
    Lists the contents of a directory.

    Args:
        relative_workspace_path: Path to list contents of, relative to the workspace root

    Returns:
        A string containing the directory listing or an error message
    """
    # Log the tool execution in the context
    tool_context.logger.info(f"Listing directory: {relative_workspace_path}")

    try:
        # Convert to Path object and resolve to handle relative paths
        path = Path(relative_workspace_path).resolve()

        # Check if path exists
        if not path.exists():
            error_msg = f"Error: Path does not exist: {relative_workspace_path}"
            tool_context.logger.error(error_msg)
            return error_msg

        # Check if it's a directory
        if not path.is_dir():
            error_msg = f"Error: Path is not a directory: {relative_workspace_path}"
            tool_context.logger.error(error_msg)
            return error_msg

        # Get the contents
        items = list(path.iterdir())

        # Sort by type (directories first, then files) and name
        dirs = sorted([item for item in items if item.is_dir()], key=lambda p: p.name)
        files = sorted([item for item in items if item.is_file()], key=lambda p: p.name)

        # Format the output
        result = []

        # Add the current path
        result.append(f"Contents of directory: {path}")
        result.append("")

        # Add directories
        if dirs:
            result.append("Directories:")
            for d in dirs:
                result.append(f"  📁 {d.name}/")
            result.append("")

        # Add files
        if files:
            result.append("Files:")
            for f in files:
                # Get file size
                try:
                    size = f.stat().st_size
                    size_str = f"{size} bytes"
                    if size > 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                except Exception:
                    size_str = "unknown size"

                result.append(f"  📄 {f.name} ({size_str})")

        # If directory is empty
        if not dirs and not files:
            result.append("Directory is empty")

        tool_context.logger.info(f"Successfully listed directory with {len(dirs)} directories and {len(files)} files")
        return "\n".join(result)

    except Exception as e:
        error_msg = f"Error listing directory {relative_workspace_path}: {e!s}"
        tool_context.logger.error(error_msg)
        return error_msg


# --- Run Terminal Command Tool ---
def run_terminal_cmd(tool_context: ToolContext, command: str, is_background: bool = False) -> str:
    """
    Executes a terminal command after security checks and user confirmation.

    Args:
        command: The terminal command to execute
        is_background: Whether to run the command in the background

    Returns:
        Command output or error message
    """
    # Log the tool execution in the context
    tool_context.logger.info(f"Running terminal command: {command}")

    # Background processing not implemented in the original function
    # We'll add a warning if it's requested
    if is_background:
        tool_context.logger.warning("Background execution requested but not supported. Running in foreground.")

    # Call the original implementation - it handles confirmation internally based on config
    result = original_run_command(command)

    # Log the result
    # Check for known error prefixes/substrings returned by original_run_command
    if (
        result.startswith("Error:")
        or "Error executing command:" in result
        or "Command timed out" in result
        or result.startswith("Command execution not permitted:")
        or "[red]Error (exit code:" in result
    ):  # Check for non-zero exit code message
        tool_context.logger.error(f"Failed to run command: {command} -> {result}")
    else:
        tool_context.logger.info(f"Successfully ran command: {command}")

    return result


# --- Load Memory Tool (Moved from tools/memory_tools.py) ---
async def load_memory(tool_context: ToolContext, query: str, app_name: str = "code_agent", user_id: str = "default_user") -> str:
    """
    Load relevant information from long-term memory based on a search query.

    Args:
        query: The search query to find relevant information
        app_name: The name of the application (defaults to 'code_agent')
        user_id: The ID of the user (defaults to 'default_user')

    Returns:
        A string containing relevant memory content
    """
    tool_context.logger.info(f"Searching memory for '{query}' (App: {app_name}, User: {user_id})")

    # Get the memory service
    # Note: get_memory_service is synchronous, might need adjustment if it becomes async
    memory_service: BaseMemoryService = get_memory_service()

    # Search memory for relevant information
    # Add error handling for the memory search itself
    try:
        # Use search instead of search_memory to match the API
        search_response = memory_service.search(app_name, user_id, query)
    except Exception as e:
        error_msg = f"Error searching memory for '{query}': {e!s}"
        tool_context.logger.error(error_msg, exc_info=True)
        return error_msg  # Return error if search fails

    # If no results found, return a message
    if not search_response.results:
        tool_context.logger.info("No relevant memories found.")
        return "No relevant information found in memory."

    # Format search results
    result_parts = ["Found relevant information in memory:"]

    for i, result in enumerate(search_response.results, 1):
        # Add a separator between results
        if i > 1:
            result_parts.append("\n---\n")

        # Format the result with relevance score
        result_parts.append(f"{result.text} [Relevance: {result.relevance_score:.2f}]")

    # Join all parts and return
    full_result = "\n".join(result_parts)
    tool_context.logger.info(f"Found {len(search_response.results)} relevant memories for '{query}'.")
    return full_result


# --- Tool Factory Functions ---


def create_read_file_tool() -> FunctionTool:
    """Create a read file tool for the codebase."""
    return FunctionTool(
        func=read_file,
    )


def create_delete_file_tool() -> FunctionTool:
    """Create a delete file tool for the codebase."""
    return FunctionTool(
        func=delete_file,
    )


def create_apply_edit_tool() -> FunctionTool:
    """Create a apply edit tool for the codebase."""
    return FunctionTool(
        func=apply_edit,
    )


def create_list_dir_tool() -> FunctionTool:
    """Create a list directory tool for the codebase."""
    return FunctionTool(
        func=list_dir,
    )


def create_run_terminal_cmd_tool() -> FunctionTool:
    """Create a run terminal command tool."""
    return FunctionTool(
        func=run_terminal_cmd,
    )


def create_google_search_tool() -> FunctionTool:
    """Create a Google Search tool.
    
    This tool uses Google's search capability to find information on the web.
    It requires a valid Google API key to be set in the environment.
    """
    # We use the built-in google_search tool provided by Google ADK
    # No need to wrap it as it's already configured properly
    return google_search


# --- Tool Collection ---


def get_file_tools() -> List[FunctionTool]:
    """Get all file tools."""
    return [
        create_read_file_tool(),
        create_delete_file_tool(),
        create_apply_edit_tool(),
        create_list_dir_tool(),
    ]


def get_all_tools() -> List[FunctionTool]:
    """Get all tools."""
    tools = get_file_tools()
    tools.append(create_run_terminal_cmd_tool())
    # Add google_search tool to the list of all tools
    tools.append(create_google_search_tool())
    return tools
