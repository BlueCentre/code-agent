import shlex  # For safely splitting command strings
import subprocess

from google.adk.tools.function_tool import FunctionTool
from pydantic import BaseModel, Field
from rich import print
from rich.prompt import Confirm


# --- Tool Input Schema ---
class RunNativeCommandArgs(BaseModel):
    command: str = Field(
        ..., description="The native terminal command string to execute."
    )
    # TODO: Consider adding timeout, working directory options?


# --- Tool Implementation ---
def run_native_command(args: RunNativeCommandArgs) -> str:
    """Executes a native terminal command after checking allowlist and requesting
    user confirmation."""
    # Import get_config here
    from code_agent.config.config import get_config

    config = get_config()
    command_str = args.command.strip()  # Ensure no leading/trailing whitespace
    if not command_str:
        return "Error: Empty command string provided."

    # --- Special handling for file listing requests ---
    # Check if this is a file listing command, especially for Python files
    command_lower = command_str.lower()
    if (
        (
            "list" in command_lower
            and "python" in command_lower
            and "file" in command_lower
        )
        or ("find" in command_lower and "*.py" in command_lower)
        or (command_lower.startswith("ls") and "*.py" in command_lower)
    ):
        # Extract the target directory from the command if possible
        target_dir = "."  # Default to current directory
        parts = command_str.split()
        for i, part in enumerate(parts):
            if i > 0 and not part.startswith("-") and not part.startswith("*"):
                # This might be a directory path
                target_dir = part
                break

        # Use find command for better recursive listing of Python files
        modified_command = f"find {target_dir} -type f -name '*.py' | sort"
        print(f"[yellow]Enhanced file listing command:[/yellow] {modified_command}")
        command_str = modified_command

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
    if (
        not allowlist
    ):  # Empty allowlist means all commands require confirmation (unless auto-approved)
        is_allowed = True
    elif base_command in allowlist:  # Check if the base command is exactly in the list
        is_allowed = True

    if not is_allowed and not config.auto_approve_native_commands:
        # Break long f-string
        return (
            f"Error: Command '{base_command}' is not in the configured allowlist "
            f"({config.DEFAULT_CONFIG_PATH}) and auto-approval is disabled."
        )
    elif not is_allowed and config.auto_approve_native_commands:
        # Break long f-string
        print(
            f"[yellow]Warning:[/yellow] Command '{base_command}' is not in the allowlist, "
            f"but executing due to auto-approval."
        )

    # 2. User Confirmation
    confirmed = False
    if config.auto_approve_native_commands:
        # Break long f-string
        print(
            f"[yellow]Auto-approving native command execution based on configuration:[/yellow] "
            f"{command_str}"
        )
        confirmed = True
    else:
        # Show the command clearly before asking
        print(
            f"[bold red]Agent requests to run native command:[/bold red] {command_str}"
        )
        confirmed = Confirm.ask("Do you want to execute this command?", default=False)

    if not confirmed:
        return "Command execution cancelled by user."

    # --- Execute Command ---
    try:
        # Command already split safely above
        print(f"[grey50]Executing command:[/grey50] {command_parts}")
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,  # Get stdout/stderr as strings
            check=False,  # Don't raise exception on non-zero exit code
            # Consider adding timeout=...
        )

        output = f"Command: {command_str}\nExit Code: {result.returncode}\n"
        if result.stdout:
            output += f"\n--- stdout ---\n{result.stdout.strip()}\n--------------\n"
        if result.stderr:
            output += f"\n--- stderr ---\n{result.stderr.strip()}\n--------------\n"

        return output.strip()

    except FileNotFoundError:
        return f"Error: Command not found: {command_parts[0]}"
    except Exception as e:
        return f"Error executing command '{command_str}': {e}"


# Create the native command tool
run_native_command_tool = FunctionTool.from_function(
    run_native_command,
    name="run_native_command",
    description="Executes a native terminal command after requesting confirmation.",
)

# For compatibility with imports elsewhere
run_native_command = run_native_command_tool

# Example usage (can be removed later)
if __name__ == "__main__":
    print("Testing run_native_command tool (requires user interaction):")

    # Assumes config allows 'echo' or has empty allowlist & no auto-approve
    args_echo = RunNativeCommandArgs(command="echo 'Hello from native tool!'")
    result_echo = run_native_command(args_echo)
    print(f"\nResult (echo):\n---\n{result_echo}\n---")

    # Assumes 'git status | cat' is allowed or handled by confirmation
    args_git = RunNativeCommandArgs(command="git status | cat")
    result_git = run_native_command(args_git)
    print(f"\nResult (git):\n---\n{result_git}\n---")

    # Test disallowed command (assuming allowlist is non-empty and doesn't include 'dangerous_cmd')
    # Need to mock config or ensure it's set appropriately for this test
    # print("\nTesting disallowed command:")
    # args_disallowed = RunNativeCommandArgs(
    #     command="dangerous_cmd --delete-everything"
    # )
    # result_disallowed = run_native_command(args_disallowed)
    # print(f"\nResult (disallowed):\n---\n{result_disallowed}\n---")
