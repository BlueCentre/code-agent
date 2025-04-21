"""
Simplified tools module containing functions that the ADK Agent can use
without relying on complex decorators or tool classes.
"""

import difflib
import shlex
import subprocess
from pathlib import Path

from rich import print
from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax

console = Console()

# Define a max file size limit (e.g., 1MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024


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
        return (
            f"Error: Path access restricted. Can only read files within the "
            f"current working directory or its subdirectories: {path}"
        )
    try:
        file_path = Path(path).resolve()
        print(f"[yellow]Attempting to read file:[/yellow] {file_path}")

        if not file_path.is_file():
            return f"Error: File not found or is not a regular file: {path}"

        # Add file size check
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                mb_size = file_size / 1024 / 1024
                max_mb_size = MAX_FILE_SIZE_BYTES / 1024 / 1024
                return f"Error: File is too large ({mb_size:.2f} MB). " f"Maximum allowed size is {max_mb_size:.2f} MB."
        except Exception as stat_e:
            return f"Error getting file size for {path}: {stat_e}"

        content = file_path.read_text()
        return content

    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied when trying to read file: {path}"
    except Exception as e:
        return f"Error reading file {path}: {e}"


# --- APPLY EDIT Tool ---
def apply_edit(target_file: str, code_edit: str) -> str:
    """Applies proposed content changes to a file after showing a diff and requesting user confirmation."""
    from code_agent.config.config import get_config

    config = get_config()

    if not is_path_within_cwd(target_file):
        return (
            f"Error: Path access restricted. Can only edit files within the "
            f"current working directory or its subdirectories: {target_file}"
        )

    try:
        file_path = Path(target_file).resolve()
        print(f"[yellow]Attempting to edit file:[/yellow] {file_path}")

        # Read current content (or empty if file doesn't exist)
        current_content = ""
        if file_path.is_file():
            current_content = file_path.read_text()
        elif file_path.exists():
            return f"Error: Path exists but is not a regular file: {target_file}"

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
            return "No changes detected. File content is the same."

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
                return f"Error writing changes to file {target_file}: {write_e}"
        else:
            return "Edit cancelled by user."

    except PermissionError:
        return f"Error: Permission denied when accessing file: {target_file}"
    except Exception as e:
        return f"Error applying edit to {target_file}: {e}"


# --- RUN NATIVE COMMAND Tool ---
def run_native_command(command: str) -> str:
    """Executes a native terminal command after checking allowlist and requesting user confirmation."""
    from code_agent.config.config import get_config

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
        return f"Error: Command '{base_command}' is not in the configured allowlist " f"and auto-approval is disabled."
    elif not is_allowed and config.auto_approve_native_commands:
        print(
            f"[yellow]Warning:[/yellow] Command '{base_command}' is not in the allowlist, "
            f"but executing due to auto-approval."
        )

    # 2. User Confirmation
    confirmed = False
    if config.auto_approve_native_commands:
        print(f"[yellow]Auto-approving native command execution based on configuration:[/yellow] " f"{command_str}")
        confirmed = True
    else:
        # Show the command clearly before asking
        print(f"[bold red]Agent requests to run native command:[/bold red] {command_str}")
        confirmed = Confirm.ask("Do you want to execute this command?", default=False)

    if not confirmed:
        return "Command execution cancelled by user."

    # --- Execute Command ---
    try:
        # Check if the command contains a pipe or other shell operators
        use_shell = "|" in command_str or ">" in command_str or "<" in command_str

        print(f"[grey50]Executing command:[/grey50] {command_parts}")

        if use_shell:
            # Use shell=True for commands with pipes or redirection
            print("[grey50]Using shell for complex command[/grey50]")
            result = subprocess.run(command_str, shell=True, capture_output=True, text=True, check=False)
        else:
            # Use normal execution for simple commands
            result = subprocess.run(command_parts, capture_output=True, text=True, check=False)

        output = f"Command: {command_str}\nExit Code: {result.returncode}\n"
        if result.stdout:
            output += f"\n--- stdout ---\n{result.stdout.strip()}\n--------------\n"
        if result.stderr:
            output += f"\n--- stderr ---\n{result.stderr.strip()}\n--------------\n"

        return output.strip()

    except FileNotFoundError:
        return f"Error: Command not found: {base_command}"
    except Exception as e:
        return f"Error executing command '{command_str}': {e}"
