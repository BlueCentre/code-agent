"""
Simplified tools module containing functions that the ADK Agent can use
without relying on complex decorators or tool classes.
"""

import difflib
import logging
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

# Setup logger for this module
logger = logging.getLogger(__name__)
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
    """Applies a given edit to a target file, showing a diff and asking for confirmation."""
    target_path = Path(target_file)
    config = get_config()

    # Security Check 1: Ensure path is within the current working directory or subdirs
    if not is_path_within_cwd(target_file):
        return f"Error: Target file '{target_file}' is outside the allowed workspace."

    try:
        # Determine if the file exists and is a regular file
        file_exists = target_path.is_file()
        if not file_exists and target_path.exists():
            return f"Error: Path exists but is not a regular file: '{target_file}'. " f"Only regular files can be edited."

        original_content = ""
        # Try reading original content *before* proceeding to diff
        if file_exists:
            try:
                original_content = target_path.read_text()
            except Exception as read_e:
                # Handle potential read errors early
                logger.error(f"Error reading original content from {target_file}: {read_e}", exc_info=True)
                return f"Error: Failed reading original content from '{target_file}'.\nError details: {read_e}"

        # --- Diff and Confirmation --- #
        # Generate diff
        # Check if splitlines can handle potential None or non-string types defensively
        original_lines = original_content.splitlines(keepends=True) if isinstance(original_content, str) else []
        new_lines = code_edit.splitlines(keepends=True) if isinstance(code_edit, str) else []

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{target_file}",
            tofile=f"b/{target_file}",
        )
        diff_text = "".join(diff)

        # If no changes, report and exit
        if not diff_text:
            return "No changes detected."

        # Display diff and ask for confirmation
        console.print(f"Attempting to edit file: \n[cyan]{target_path}[/cyan]")
        console.print("\nProposed changes:")
        console.print(Syntax(diff_text, "diff", theme="default", line_numbers=False))

        # Check for auto-approve setting
        auto_approve = config.auto_approve_edits

        confirmed = False
        if auto_approve:
            console.print("[yellow]Auto-approving edit based on configuration.[/yellow]")
            confirmed = True
        else:
            confirmed = Confirm.ask("Apply these changes?", default=False)

        if confirmed:
            try:
                # Ensure parent directory exists for new files
                if not file_exists:
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                target_path.write_text(code_edit)
                return f"Edit applied successfully to {target_file}."
            except IOError as e:
                logger.error(f"IOError writing changes to {target_file}: {e}")
                return f"Error: Failed when writing changes to '{target_file}'.\nError details: {e}"
        else:
            return "Edit cancelled by user."

    except Exception as e:
        logger.error(f"Error applying edit to {target_file}: {e}", exc_info=True)
        return f"Error: Failed when applying edit to '{target_file}'.\nError details: {e}"


# --- RUN NATIVE COMMAND Tool ---
# This function is deprecated and its functionality is now in native_tools.py
# Removing...

# --- WEB SEARCH Tool (using DuckDuckGo) --- # REMOVED FUNCTION
# def web_search(query: str) -> str:
#     ...
