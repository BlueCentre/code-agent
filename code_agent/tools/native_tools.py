import os
import subprocess
from typing import List, Optional

from pydantic import BaseModel, Field
from rich import print
from rich.console import Console
from rich.prompt import Confirm

from code_agent.config import get_config

console = Console()

class RunNativeCommandArgs(BaseModel):
    command: str = Field(..., description="The terminal command to execute")

# Dangerous commands that should trigger warnings
DANGEROUS_COMMAND_PREFIXES = [
    "rm -r", 
    "rm -f", 
    "rm -rf",  # Most dangerous
    "sudo ",
    "> /",     # Writing to root
    "dd",
    "chmod -R",
    "mkfs",
    ":(){ ",   # Fork bomb
]

# Commands that might be potentially risky
RISKY_COMMAND_PREFIXES = [
    "mv ",
    "cp -r",
    "sed -i",
    "apt",
    "yum",
    "pip install",
    "npm install",
    "kubectl delete",
    "terraform destroy",
]

def run_native_command(command: str) -> str:
    """Executes a native terminal command after approval checks."""
    config = get_config()

    print(f"[yellow]Command requested:[/yellow] {command}")
    
    # Skip confirmation under certain conditions
    auto_approve = config.auto_approve_native_commands
    
    if auto_approve:
        # Check if the specific command is in the allowlist
        allowlist = config.native_command_allowlist
        command_allowed = any(
            (cmd and command.startswith(cmd)) for cmd in allowlist if cmd
        )
        
        if not command_allowed:
            # Override auto-approve for commands not on the allowlist
            auto_approve = False
            print("[yellow]Command not found on the allowlist. Confirmation required.[/yellow]")
    
    # Check for dangerous commands regardless of auto-approve setting
    is_dangerous = any(command.startswith(prefix) for prefix in DANGEROUS_COMMAND_PREFIXES)
    is_risky = any(command.startswith(prefix) for prefix in RISKY_COMMAND_PREFIXES)
    
    if is_dangerous:
        print("[bold red]⚠️  WARNING: This command could be destructive![/bold red]")
        print("[red]This command has been identified as potentially dangerous and could cause data loss.[/red]")
        # Force confirmation for dangerous commands regardless of settings
        auto_approve = False
    elif is_risky:
        print("[bold yellow]⚠️  CAUTION: This command could have side effects.[/bold yellow]")
        
    # Request confirmation if not auto-approved
    if not auto_approve:
        if not Confirm.ask("Do you want to run this command?", default=False):
            return "Command execution cancelled by user."
    else:
        print("[yellow]Auto-approving command based on configuration and allowlist.[/yellow]")
    
    # Execute the command
    try:
        print("[grey50]Running command...[/grey50]")
        # Use shell=True to execute complex commands with pipes, redirects, etc.
        # For security in a production environment, this should be rewritten to use shell=False
        process = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            executable="/bin/bash",  # Use bash to ensure consistency
        )
        
        # Prepare result with both stdout and stderr
        result = process.stdout
        
        # Add error info if there was an error
        if process.returncode != 0:
            result += f"\n\n[red]Error (exit code: {process.returncode}):[/red]\n{process.stderr}"
            print(f"[red]Command failed with exit code {process.returncode}[/red]")
        else:
            print("[green]Command completed successfully[/green]")
            
        return result
        
    except Exception as e:
        error_message = f"Error executing command: {e}"
        print(f"[bold red]{error_message}[/bold red]")
        return error_message

# Legacy function that accepts RunNativeCommandArgs for compatibility
def run_native_command_legacy(args: RunNativeCommandArgs) -> str:
    return run_native_command(args.command)

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
