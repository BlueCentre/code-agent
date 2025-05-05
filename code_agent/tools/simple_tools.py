"""
Simplified tools module containing functions that the ADK Agent can use
without relying on complex decorators or tool classes.
"""

import difflib
import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

from rich import print
from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax

from code_agent.config.config import get_config
from code_agent.tools.error_utils import (
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
)

# Make these module-level variables that can be easily mocked in tests
subprocess_run = subprocess.run
confirm_ask = Confirm.ask

# Setup logger for this module
logger = logging.getLogger(__name__)
console = Console()

# Define a max file size limit (e.g., 1MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Define the maximum number of search results to return
MAX_SEARCH_RESULTS = 3


# --- Helper Functions ---
def deduce_from_path(path: Path) -> str:
    """Deduce the syntax highlighting lexer from a file path."""
    extension = path.suffix.lower()
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
        ".bash": "bash",
        ".c": "c",
        ".cpp": "cpp",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
    }
    return extension_map.get(extension, "text")


# --- Helper for Path Validation ---
def is_path_within_cwd(path_str: Optional[Union[str, Path]]) -> bool:
    """
    Check if a given path is within the current working directory.

    Args:
        path_str: A path string to check

    Returns:
        True if the path is within the current working directory, False otherwise
    """
    try:
        if path_str is None:
            return False

        cwd = Path.cwd()
        resolved_path = Path(path_str).resolve()
        return resolved_path.is_relative_to(cwd)
    except (ValueError, OSError, TypeError):
        # Handle various errors: invalid paths, non-existing files, etc.
        return False


# --- READ FILE Tool ---
def read_file(path: str) -> str:
    """Reads the entire content of a file at the given path, restricted to CWD."""
    if not is_path_within_cwd(path):
        return format_path_restricted_error(path)

    try:
        file_path = Path(path).resolve()
        print(f"[yellow]Attempting to read file:[/yellow] {file_path}")

        if not file_path.is_file():
            return (
                f"Error: File not found or is not a regular file: '{path}'.\n"
                f"Please check:\n"
                f"- If the path points to a regular file, not a directory\n"
                f"- If the file exists at the specified location"
            )

        # Add file size check
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return format_file_size_error(path, file_size, MAX_FILE_SIZE_BYTES)
        except Exception as stat_e:
            return format_file_error(stat_e, path, "checking size of")

        content = file_path.read_text()
        return content

    except FileNotFoundError as e:
        return format_file_error(e, path, "reading")
    except PermissionError as e:
        return format_file_error(e, path, "reading")
    except Exception as e:
        return format_file_error(e, path, "reading")


# --- APPLY EDIT Tool ---
def apply_edit(target_file: str, content: str, explanation: Optional[str] = None) -> str:
    """
    Apply an edit to a file by creating the file or replacing its contents.

    Args:
        target_file: The path to the file to edit
        content: The new content for the file
        explanation: Optional explanation of the edit

    Returns:
        A string message indicating success or failure
    """
    config = get_config()

    try:
        # Ensure valid path (security check)
        file_path = Path(target_file)
        if not is_path_within_cwd(file_path):
            return format_path_restricted_error(str(file_path))

        # Handle the case where target exists but is not a file
        if file_path.exists() and not file_path.is_file():
            return f"Error: Path exists but is not a regular file: {file_path}"

        # Get existing file content (if any)
        existing_content = ""
        try:
            if file_path.exists() and file_path.is_file():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
        except Exception as read_error:
            return f"Error: Could not read existing file: {read_error!s}"

        # Check if content is identical to avoid unnecessary edits
        if existing_content == content:
            return f"No changes detected in {file_path}"

        # Show diff
        console = Console()
        print(f"Attempting to edit file: \n{target_file}")

        if existing_content:
            # Create a unified diff when there was existing content
            diff = difflib.unified_diff(
                existing_content.splitlines(), content.splitlines(), lineterm="", fromfile=f"Original: {file_path.name}", tofile=f"Updated: {file_path.name}"
            )
            diff_text = "\n".join(diff)
            print("\nProposed changes:")
            console.print(Syntax(diff_text, "diff"))
        else:
            # Show the new content when creating a new file
            print("\nProposed new file:")
            console.print(Syntax(content, deduce_from_path(file_path)))

        # If auto-approval is enabled, skip confirmation
        if config.auto_approve_edits:
            console.print("Auto-approving edit based on configuration.")
            # Ensure parent directory exists
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content (new file or replacing old file)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Edit applied successfully to {file_path}"
            except Exception as write_error:
                return f"Error: Failed to write to {file_path}: {write_error!s}"

        # Interactive confirmation
        else:
            # Use rich's Confirm.ask for a prettier prompt
            confirmed = Confirm.ask("Apply these changes?", default=False)
            if confirmed:
                # Ensure parent directory exists
                if not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                # Write content (new file or replacing old file)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    return f"Edit applied successfully to {file_path}"
                except Exception as write_error:
                    return f"Error: Failed to write to {file_path}: {write_error!s}"
            else:
                return "Edit cancelled by user"

    except OSError as e:
        return f"Error: Failed when write '{target_file}'.\nOperating system error when accessing '{target_file}'.\nDetails: {e}\nThis could be due to:\n- Disk I/O errors\n- Network file system issues\n- Resource limitations"  # noqa: E501
    except Exception as e:
        return f"Error: Unexpected error occurred while editing the file: {e}"


# --- RUN NATIVE COMMAND Tool ---
# This function is deprecated and its functionality is now in native_tools.py
# Removing...

# --- WEB SEARCH Tool (using DuckDuckGo) --- # REMOVED FUNCTION
# def web_search(query: str) -> str:
#     ...
