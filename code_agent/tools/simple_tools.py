"""
Simplified tools module containing functions that the ADK Agent can use
without relying on complex decorators or tool classes.
"""

import difflib
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional

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

        # Read current content (or empty if file doesn't exist)
        current_content = ""
        if file_path.is_file():
            try:
                current_content = file_path.read_text()
            except Exception as read_e:
                return format_file_error(read_e, target_file, "reading for edit")
        elif file_path.exists():
            return (
                f"Error: Path exists but is not a regular file: '{target_file}'.\n"
                f"Only regular files can be edited. If you're trying to edit a directory,\n"
                f"this operation is not supported."
            )

        # --- Calculate and Display Diff ---
        diff = list(
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
        # Use rich Syntax for diff highlighting
        diff_text = "".join(diff)
        syntax = Syntax(diff_text, "diff", theme="default", line_numbers=False)
        console.print(syntax)

        # --- Request Confirmation ---
        confirmed = False
        if config.auto_approve_edits:
            print("[yellow]Auto-approving edit based on configuration.[/yellow]")
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
def run_native_command(command: str) -> str:
    """Executes a native terminal command after checking allowlist and requesting user confirmation."""
    config = get_config()

    command_str = command.strip()  # Ensure no leading/trailing whitespace
    if not command_str:
        return "Error: Empty command string provided."

    # Split command for analysis and execution
    try:
        command_parts = shlex.split(command_str)
        if not command_parts:
            return "Error: Empty command string after splitting."
        base_command = command_parts[0]
    except ValueError as e:
        return f"Error parsing command string: {e}"

    # --- Security Checks ---
    # 1. Allowlist Check (Exact match on base command)
    allowlist = config.native_command_allowlist
    is_allowed = False
    if not allowlist:  # Empty allowlist means all commands require confirmation
        is_allowed = True
    elif base_command in allowlist:  # Check if the base command is in the list
        is_allowed = True

    if not is_allowed and not config.auto_approve_native_commands:
        return f"Error: Command '{base_command}' is not in the configured allowlist and auto-approval is disabled."
    elif not is_allowed and config.auto_approve_native_commands:
        print(f"[yellow]Warning:[/yellow] Command '{base_command}' is not in the allowlist, but executing due to auto-approval.")

    # 2. User Confirmation
    confirmed = False
    if config.auto_approve_native_commands:
        print(f"[yellow]Auto-approving native command execution based on configuration:[/yellow] {command_str}")
        confirmed = True
    else:
        # Show the command clearly before asking
        print(f"[bold red]Agent requests to run native command:[/bold red] {command_str}")
        # Use the module-level variable that can be mocked
        confirmed = confirm_ask("Do you want to execute this command?", default=False)

    if not confirmed:
        return "Command execution cancelled by user."

    # --- Execute Command ---
    try:
        # Use shell=True only for commands with shell operators
        use_shell = "|" in command_str or ">" in command_str or "<" in command_str

        if use_shell:
            # For complex commands with pipe/redirects, use shell=True
            print("[grey50]Using shell for complex command[/grey50]")
            # Use the module-level variable that can be mocked
            result = subprocess_run(command_str, shell=True, capture_output=True, text=True, check=False)
        else:
            # For simple commands, avoid shell=True for better security
            # Use the module-level variable that can be mocked
            result = subprocess_run(command_parts, capture_output=True, text=True, check=False)

        # --- Format and Return Results ---
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        return_code = result.returncode

        # Format the response
        response = []
        response.append(f"Command: {command_str}")
        response.append(f"Return code: {return_code}")

        if stdout:
            response.append("\n=== STDOUT ===")
            response.append(stdout)

        if stderr:
            response.append("\n=== STDERR ===")
            response.append(stderr)

        if return_code != 0:
            response.append(f"\n⚠️ [bold yellow]Command exited with non-zero status code: {return_code}[/bold yellow]")

        return "\n".join(response)

    except FileNotFoundError:
        return f"Error: Command not found: '{base_command}'. Please check if it's installed and available in PATH."
    except PermissionError:
        return f"Error: Permission denied when executing '{base_command}'. Check file permissions or if elevated privileges are required."
    except Exception as e:
        return f"Error executing command: {e}"


# --- WEB SEARCH Tool ---
def web_search(query: str) -> Optional[str]:
    """
    Searches the web using DuckDuckGo and returns formatted results.

    Args:
        query: The search query string

    Returns:
        A formatted string of search results, or an error message if the search fails
    """
    config = get_config()

    # Check if web search is enabled in configuration
    if not hasattr(config, "security") or not getattr(config.security, "enable_web_search", False):
        return "Error: Web search is disabled in configuration. Enable it in your config file to use this feature."

    try:
        from duckduckgo_search import DDGS

        print(f"[yellow]Searching the web for:[/yellow] {query}")

        # Initialize the DuckDuckGo search client
        ddgs = DDGS()

        # Perform the search with rate limiting to avoid being blocked
        try:
            # Add a small delay before search to avoid rate limiting
            time.sleep(0.5)
            MAX_SEARCH_RESULTS = 3
            results = list(ddgs.text(query, max_results=MAX_SEARCH_RESULTS))
        except Exception as search_error:
            return f"Error performing web search: {search_error}\nThis might be due to network issues or rate limiting."

        # Check if we got any results
        if not results:
            return f"No results found for query: '{query}'\nTry rephrasing your search query."

        # Format the results
        formatted_results = ["### Web Search Results", ""]

        for i, result in enumerate(results, 1):
            title = result.get("title", "No Title")
            body = result.get("body", "No content available")
            href = result.get("href", "No URL available")

            formatted_results.append(f"**Result {i}:** {title}")
            formatted_results.append(f"{body}")
            formatted_results.append(f"*Source: {href}*")
            formatted_results.append("")  # Empty line for spacing

        return "\n".join(formatted_results)

    except ImportError:
        return "Error: Required package 'duckduckgo-search' is not installed. Please install it to use the web search feature."
    except Exception as e:
        return f"Error during web search: {e}"
