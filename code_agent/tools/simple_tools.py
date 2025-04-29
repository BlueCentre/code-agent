"""
Simplified tools module containing functions that the ADK Agent can use
without relying on complex decorators or tool classes.
"""

import difflib
import subprocess
from pathlib import Path

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

console = Console()

# Define a max file size limit (e.g., 1MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024

# Define the maximum number of search results to return
MAX_SEARCH_RESULTS = 3


# --- Helper for Path Validation ---
def is_path_within_cwd(path_str: str) -> bool:
    """Checks if the resolved path is within the current working directory."""
    try:
        cwd = Path.cwd()
        resolved_path = Path(path_str).resolve()
        return resolved_path.is_relative_to(cwd)
    except (ValueError, OSError):
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
def apply_edit(target_file: str, code_edit: str) -> str:
    """Applies proposed content changes to a file after showing a diff and requesting user confirmation."""
    config = get_config()

    if not is_path_within_cwd(target_file):
        return format_path_restricted_error(target_file)

    try:
        file_path = Path(target_file).resolve()
        print(f"[yellow]Attempting to edit file:[/yellow] {file_path}")

        # --- Read Current Content ---
        current_content = ""
        if file_path.is_file():
            try:
                # Check file size before reading
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE_BYTES:
                    return format_file_size_error(target_file, file_size, MAX_FILE_SIZE_BYTES)
                current_content = file_path.read_text()
            except Exception as read_e:
                return format_file_error(read_e, target_file, "reading for edit")
        elif file_path.exists():
            return (
                f"Error: Path exists but is not a regular file: '{target_file}'.\n"
                f"Only regular files can be edited. If you're trying to edit a directory,\n"
                f"this operation is not supported."
            )

        # --- Show Diff ---
        diff = "".join(
            difflib.unified_diff(
                current_content.splitlines(keepends=True),
                code_edit.splitlines(keepends=True),
                fromfile=f"a/{target_file}",
                tofile=f"b/{target_file}",
                lineterm="\n",
            )
        )

        if not diff:
            return f"No changes needed. File content already matches the proposed edit for {target_file}."

        print("\n[bold]Proposed changes:[/bold]")
        syntax = Syntax(diff, "diff", theme="default", line_numbers=False)
        console.print(syntax)

        # --- Ask for Confirmation ---
        if config.auto_approve_edit:
            confirmed = True
        else:
            confirmed = Confirm.ask(f"Apply these changes to {target_file}?", default=False)

        # --- Apply Changes if Confirmed ---
        if confirmed:
            try:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(code_edit)
                return f"Edit applied successfully to {target_file}."
            except Exception as write_e:
                return format_file_error(write_e, target_file, "writing changes to")
        else:
            return "Edit cancelled by user."

    except PermissionError as e:
        return format_file_error(e, target_file, "accessing")
    except Exception as e:
        return format_file_error(e, target_file, "applying edit to")


# --- RUN NATIVE COMMAND Tool ---
# This function is deprecated and its functionality is now in native_tools.py
# Removing...

# --- WEB SEARCH Tool (using DuckDuckGo) --- # REMOVED FUNCTION
# def web_search(query: str) -> str:
#     ...
