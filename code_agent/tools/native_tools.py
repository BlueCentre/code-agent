import asyncio
import shlex
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field
from rich import box, print
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from code_agent.config.config import get_config
from code_agent.tools.progress_indicators import command_execution_indicator, operation_complete, operation_error, step_progress
from code_agent.tools.security import is_command_safe

# --- Native Terminal Command Execution ---

console = Console()


class RunNativeCommandArgs(BaseModel):
    command: str = Field(..., description="The terminal command to execute")
    working_directory: str = Field(None, description="The working directory to run the command in")
    timeout: int = Field(None, description="Timeout for the command in seconds")


# List of command prefixes that are considered dangerous
# Used for custom command safety checks beyond the general security module
DANGEROUS_COMMAND_PREFIXES = [
    "rm -rf /",  # Delete everything from root
    "rm -r /",  # Delete everything from root
    "dd if=",  # Direct disk operations
    "> /dev/sda",  # Overwrite disk
    "mkfs",  # Format filesystem
    ":(){ :|:& };:",  # Fork bomb
    "wget",  # Download and potentially execute
    "curl",  # Download and potentially execute
]

# List of command prefixes that are risky but can be executed with warning
RISKY_COMMAND_PREFIXES = [
    "chmod -R",  # Recursive chmod
    "chown -R",  # Recursive chown
    "mv * /",  # Move everything to root
    "cp -r * /",  # Copy everything to root
    "find / -delete",  # Delete files recursively
    "apt-get",  # Package management
    "apt",  # Package management
    "pip install",  # Python package management
    "npm install",  # Node package management
    "yum",  # Package management
]

# Command categories with descriptions for better context
COMMAND_CATEGORIES = {
    "file_operations": {
        "patterns": ["ls", "cat", "cp", "mv", "rm", "mkdir", "touch", "find"],
        "description": "File system operations that may create, modify, or delete files",
    },
    "network": {
        "patterns": ["curl", "wget", "ping", "ssh", "nc", "netstat", "ifconfig", "ip"],
        "description": "Network-related commands that may connect to external systems",
    },
    "system": {
        "patterns": ["ps", "top", "kill", "pkill", "service", "systemctl"],
        "description": "System administration commands that may affect running processes",
    },
    "package_management": {
        "patterns": ["apt", "apt-get", "yum", "dnf", "brew", "pip", "npm", "cargo"],
        "description": "Package management commands that may install or remove software",
    },
    "development": {
        "patterns": ["git", "make", "gcc", "python", "node", "npm", "yarn"],
        "description": "Development-related commands for source code management and building",
    },
}


def _categorize_command(command: str) -> List[str]:
    """Determine which categories a command falls into for better context."""
    cmd_parts = shlex.split(command)
    base_cmd = cmd_parts[0] if cmd_parts else ""

    categories = []
    for category, info in COMMAND_CATEGORIES.items():
        if any(pattern in command for pattern in info["patterns"]) or base_cmd in info["patterns"]:
            categories.append(category)

    return categories


def _analyze_command_impact(command: str) -> Tuple[str, List[str]]:
    """Analyze a command to determine its potential impact and provide warnings."""
    impact_level = "Low"
    warnings = []

    # Check for commands that might affect the file system
    if any(cmd in command for cmd in ["rm", "mv", "cp", "> ", ">>", "truncate"]):
        impact_level = "Medium"
        warnings.append("This command may modify or delete files")

    # Check for installation commands
    if any(cmd in command for cmd in ["apt", "apt-get", "yum", "dnf", "pip install", "npm install"]):
        impact_level = "Medium"
        warnings.append("This command may install new software or dependencies")

    # Check for recursive operations
    if any(pattern in command for pattern in ["-r", "-R", "--recursive", "-rf"]):
        impact_level = "High"
        warnings.append("This command includes recursive options that may affect multiple files or directories")

    # Check for commands that might affect system configuration
    if any(cmd in command for cmd in ["chmod", "chown", "sudo", "systemctl"]):
        impact_level = "High"
        warnings.append("This command may change system configuration or permissions")

    return impact_level, warnings


async def run_native_command(command: str, working_directory: Optional[str] = None, timeout: Optional[int] = None) -> str:
    """Executes a native terminal command after approval checks (async)."""
    config = get_config()

    # Use config defaults if values not provided
    if working_directory is None and hasattr(config, "native_commands"):
        working_directory = getattr(config.native_commands, "default_working_directory", None)

    if timeout is None and hasattr(config, "native_commands"):
        timeout = getattr(config.native_commands, "default_timeout", None)

    step_progress("Validating command", "blue")
    # Security check for command
    is_safe, reason, is_warning = is_command_safe(command)

    # For dangerous commands, always require confirmation
    if not is_safe:
        # Don't even offer dangerous commands for execution
        operation_error("Security violation detected!")
        print(Panel(f"[red]{reason}[/red]", title="⚠️ [bold red]SECURITY VIOLATION[/bold red]", border_style="red"))
        return f"Command execution not permitted: {reason}"

    step_progress("Analyzing command impact", "blue")
    # Get more context about the command
    command_categories = _categorize_command(command)
    impact_level, impact_warnings = _analyze_command_impact(command)

    # Create a table with command information
    cmd_table = Table(show_header=False, box=box.SQUARE)
    cmd_table.add_column("Property", style="bold")
    cmd_table.add_column("Value")

    # Add command with syntax highlighting
    cmd_parts = command.split()

    # Add basic command info
    cmd_table.add_row("Command", Syntax(command, "bash", theme="monokai", word_wrap=True))

    # Only add working directory if it's a valid string
    if working_directory and isinstance(working_directory, str):
        cmd_table.add_row("Working Directory", working_directory)

    # Only add timeout if it's a valid number
    if timeout and isinstance(timeout, (int, float)):
        cmd_table.add_row("Timeout", f"{timeout} seconds")

    # Add impact assessment
    impact_color = {"Low": "green", "Medium": "yellow", "High": "red"}.get(impact_level, "yellow")

    cmd_table.add_row("Impact Level", f"[{impact_color}]{impact_level}[/{impact_color}]")

    # Add categories if available
    if command_categories:
        category_descriptions = [f"• {COMMAND_CATEGORIES[cat]['description']}" for cat in command_categories]
        cmd_table.add_row("Categories", "\n".join(category_descriptions))

    # For risky commands or commands with warnings, show detailed warning
    warnings_to_show = []
    if is_warning:
        warnings_to_show.append(f"[yellow]{reason}[/yellow]")

    # Add impact warnings
    warnings_to_show.extend([f"[yellow]• {warning}[/yellow]" for warning in impact_warnings])

    # Create the main panel
    operation_text = Text("🔧 EXECUTE COMMAND", style="bold white on blue")
    command_panel = Panel(cmd_table, title=operation_text, title_align="left", border_style="blue")

    # Display command info
    console.print(command_panel)

    # Show warnings if present
    if warnings_to_show:
        warning_panel = Panel("\n".join(warnings_to_show), title="⚠️ Warnings", border_style="yellow")
        console.print(warning_panel)

    # Only ask for confirmation if auto-approve is disabled AND the command is risky
    if not config.auto_approve_native_commands and is_warning:
        # Display the confirmation prompt
        console.print()
        confirm_text = "[bold blue]Execute this command?[/bold blue]"
        # Run synchronous Confirm.ask in a separate thread
        confirmed = await asyncio.to_thread(Confirm.ask, confirm_text, default=False)
        if not confirmed:
            return "Command execution cancelled by user choice."
    else:
        print("[yellow]Auto-approving command based on configuration.[/yellow]")

    # If we got here, the command passed all security checks or was manually approved
    try:
        step_progress("Preparing command execution", "green")
        # Split the command for safer execution
        # Use shlex.split for better handling of quotes and spaces
        try:
            cmd_parts = shlex.split(command)
            if not cmd_parts:
                raise ValueError("Command string resulted in empty list after splitting.")
        except ValueError as e:
            error_message = f"Error parsing command: {e}"
            operation_error(error_message)
            return error_message

        # Use asyncio.create_subprocess_exec for async execution
        with command_execution_indicator(command):
            process = await asyncio.create_subprocess_exec(*cmd_parts, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=working_directory)

            try:
                # Wait for the command to complete or timeout
                stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                timeout_value = timeout or "default"
                error_message = f"Command timed out after {timeout_value} seconds"
                operation_error(error_message)
                # Ensure the process is killed on timeout
                try:
                    process.kill()
                    await process.wait()  # Wait for cleanup
                except ProcessLookupError:
                    pass  # Process already terminated
                return error_message

        # Decode stdout and stderr
        stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

        # Prepare result with both stdout and stderr
        result = stdout

        # Add error info if there was an error
        if process.returncode != 0:
            result += f"\n\n[red]Error (exit code: {process.returncode}):[/red]\n{stderr}"
            operation_error(f"Command failed with exit code {process.returncode}")
        else:
            operation_complete("Command executed successfully")

        return result.strip()  # Strip trailing whitespace often added

    except FileNotFoundError as e:
        # Handle case where the command itself is not found
        error_message = f"Error executing command: Command not found or invalid: {cmd_parts[0]}. Details: {e}"
        operation_error(error_message)
        return error_message
    except Exception as e:
        # Catch other potential exceptions during subprocess creation or execution
        error_message = f"Error executing command: {e}"
        operation_error(error_message)
        return error_message


# Legacy function that accepts RunNativeCommandArgs for compatibility
async def run_native_command_legacy(args: RunNativeCommandArgs) -> str:
    return await run_native_command(args.command, working_directory=args.working_directory, timeout=args.timeout)


# Example usage (can be removed later)
async def main():
    print("Testing run_native_command tool (async):")

    # Simple example - list files
    print("\n--- Test 1: Simple Command ---")
    result1 = await run_native_command("ls -la")
    print(f"Result 1:\n---\n{result1}\n---")

    # Command with error
    print("\n--- Test 2: Command with Error ---")
    result2 = await run_native_command("ls /nonexistent_directory")
    print(f"Result 2:\n---\n{result2}\n---")

    # Dangerous command test (should be blocked before execution)
    print("\n--- Test 3: Dangerous Command ---")
    result3 = await run_native_command("rm -rf /")  # This pattern is blocked by security.py
    print(f"Result 3:\n---\n{result3}\n---")

    # Command needing confirmation (assuming auto_approve=False)
    print("\n--- Test 4: Confirmation Needed ---")
    # To run this part, ensure auto_approve_native_commands is False in config
    # result4 = await run_native_command("git status")
    # print(f"Result 4:\n---\n{result4}\n---")


if __name__ == "__main__":
    # Get the current event loop or create a new one
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the async main function
    loop.run_until_complete(main())
