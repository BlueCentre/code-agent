import subprocess
from typing import Optional

from pydantic import BaseModel, Field
from rich import print
from rich.console import Console
from rich.prompt import Confirm

from code_agent.config import get_config
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


def run_native_command(command: str, working_directory: Optional[str] = None, timeout: Optional[int] = None) -> str:
    """Executes a native terminal command after approval checks."""
    config = get_config()

    # Security check for command
    is_safe, reason, is_warning = is_command_safe(command)

    # For dangerous commands, always require confirmation
    if not is_safe:
        # Don't even offer dangerous commands for execution
        print("[bold red]Not executing command due to security concerns:[/bold red]")
        print(f"[red]{reason}[/red]")
        return f"Command execution not permitted: {reason}"

    # For risky commands, show warning and require confirmation
    if is_warning:
        print("[bold yellow]Warning - this command has potential risks:[/bold yellow]")
        print(f"[yellow]{reason}[/yellow]")

    # Only ask for confirmation if auto-approve is disabled
    if not config.auto_approve_native_commands:
        # Display the command and ask for confirmation
        print(f"[bold]Command requested:[/bold] {command}")
        confirmed = Confirm.ask("Do you want to execute this command?", default=False)
        if not confirmed:
            return "Command execution cancelled by user choice."
    else:
        print(f"[dim]Auto-approving command: {command}[/dim]")

    # If we got here, the command passed all security checks or was manually approved
    try:
        print("[grey50]Running command...[/grey50]")
        # Split the command for safer execution with shell=False
        cmd_parts = command.split()

        # Use shell=False for better security
        process = subprocess.run(cmd_parts, shell=False, text=True, capture_output=True, cwd=working_directory, timeout=timeout)

        # Prepare result with both stdout and stderr
        result = process.stdout

        # Add error info if there was an error
        if process.returncode != 0:
            result += f"\n\n[red]Error (exit code: {process.returncode}):[/red]\n{process.stderr}"
            print(f"[red]Command failed with exit code {process.returncode}[/red]")
        else:
            print("[green]Command completed successfully[/green]")

        return result

    except subprocess.TimeoutExpired:
        timeout_value = timeout or "default"
        error_message = f"Command timed out after {timeout_value} seconds"
        print(f"[bold red]{error_message}[/bold red]")
        return error_message
    except Exception as e:
        error_message = f"Error executing command: {e}"
        print(f"[bold red]{error_message}[/bold red]")
        return error_message


# Legacy function that accepts RunNativeCommandArgs for compatibility
def run_native_command_legacy(args: RunNativeCommandArgs) -> str:
    return run_native_command(args.command, working_directory=args.working_directory, timeout=args.timeout)


# Example usage (can be removed later)
if __name__ == "__main__":
    print("Testing run_native_command tool:")

    # Simple example - list files
    print("\n--- Test 1: Simple Command ---")
    result1 = run_native_command("ls -la")
    print(f"Result 1:\n---\n{result1}\n---")

    # Command with error
    print("\n--- Test 2: Command with Error ---")
    result2 = run_native_command("ls /nonexistent_directory")
    print(f"Result 2:\n---\n{result2}\n---")

    # Dangerous command test
    print("\n--- Test 3: Dangerous Command ---")
    result3 = run_native_command("rm -rf /tmp/test_dir")
    print(f"Result 3:\n---\n{result3}\n---")
