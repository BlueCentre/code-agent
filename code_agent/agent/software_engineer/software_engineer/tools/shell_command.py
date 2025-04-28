import subprocess
import shlex
from pydantic import BaseModel, Field
import logging
from typing import Optional
# Import ToolContext for state management
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# --- Configuration Tool --- #

class ConfigureShellApprovalInput(BaseModel):
    """Input model for configuring shell command approval."""
    require_approval: bool = Field(..., description="Set to true to require approval, false to disable.")

class ConfigureShellApprovalOutput(BaseModel):
    """Output model for configuring shell command approval."""
    status: str

def configure_shell_approval(args: dict, tool_context: ToolContext) -> ConfigureShellApprovalOutput:
    """Configures whether running shell commands requires user approval for the current session.

    Args:
        args (dict): A dictionary containing:
            require_approval (bool): Set to true to require approval, false to disable.
        tool_context (ToolContext): The context for accessing session state.
    """
    require_approval = args.get("require_approval")

    # Add validation for the boolean argument
    if require_approval is None or not isinstance(require_approval, bool):
        message = "Error: 'require_approval' argument is missing or not a boolean (true/false)."
        logger.error(message)
        return ConfigureShellApprovalOutput(status=message)

    tool_context.state['require_shell_approval'] = require_approval
    status = "enabled" if require_approval else "disabled"
    logger.info(f"Shell command approval requirement set to: {status}")
    return ConfigureShellApprovalOutput(status=f"Shell command approval requirement is now {status}.")

# --- Shell Command Execution Tool --- #

class ShellCommandInput(BaseModel):
    """Input model for the run_shell_command tool."""
    command: str = Field(..., description="The shell command to execute.")
    working_directory: Optional[str] = Field(None, description="Optional working directory to run the command in.")
    timeout: int = Field(60, description="Timeout in seconds for the command execution.")

class ShellCommandOutput(BaseModel):
    """Output model for the run_shell_command tool."""
    stdout: str | None = Field(None, description="The standard output of the command (only if run)." )
    stderr: str | None = Field(None, description="The standard error of the command (only if run)." )
    return_code: int | None = Field(None, description="The return code of the command (only if run)." )
    command_executed: str | None = Field(None, description="The command that was attempted or executed.")
    status: str = Field(description="Status: 'executed', 'approval_required', or 'error'.")
    message: str = Field(description="Additional information about the status.")

def run_shell_command(args: dict, tool_context: ToolContext) -> ShellCommandOutput:
    """
    Executes a given shell command directly **ONLY IF** user approval is disabled via configure_shell_approval.
    By default, approval is required, and this tool will return an 'approval_required' status.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to execute.
            working_directory (Optional[str]): Optional working directory.
            timeout (Optional[int]): Optional timeout in seconds (default: 60).
        tool_context (ToolContext): The context for accessing session state.

    Security Note: Use configure_shell_approval(require_approval=False) with caution.
    """
    command = args.get("command")
    working_directory = args.get("working_directory")
    timeout = args.get("timeout", 60)

    if not command:
        return ShellCommandOutput(
            status="error",
            message="Error: 'command' argument is missing."
        )

    # --- Check Approval State --- #
    require_approval = tool_context.state.get('require_shell_approval', True)

    if require_approval:
        logger.warning(f"Shell command approval is required. Command '{command}' was not executed.")
        return ShellCommandOutput(
            status="approval_required",
            message=f"Approval is required to run shell commands. Command '{command}' was not executed. Use the platform's terminal execution feature which prompts for approval, or disable approval using configure_shell_approval.",
            command_executed=command
        )
    # --- Approval Not Required - Proceed with Execution --- #
    logger.info("Shell command approval not required. Proceeding with direct execution.")

    try:
        timeout_sec = int(timeout)
    except (ValueError, TypeError):
        return ShellCommandOutput(
            status="error",
            message=f"Error: Invalid timeout value '{timeout}'. Must be an integer.",
            command_executed=command
        )

    command_parts = shlex.split(command)
    logger.info(f"Executing shell command: '{command}' in directory '{working_directory or '.'}'")

    try:
        process = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=timeout_sec,
            check=False # Don't raise exception on non-zero exit
        )
        logger.info(f"Command '{command}' finished with return code {process.returncode}")
        return ShellCommandOutput(
            stdout=process.stdout.strip(),
            stderr=process.stderr.strip(),
            return_code=process.returncode,
            command_executed=command,
            status="executed",
            message="Command executed successfully." if process.returncode == 0 else "Command executed with non-zero exit code."
        )
    except FileNotFoundError:
        logger.error(f"Command not found: {command_parts[0]}")
        return ShellCommandOutput(
            stderr=f"Error: Command not found: {command_parts[0]}",
            return_code=-1,
            command_executed=command,
            status="error",
            message=f"Command not found: {command_parts[0]}"
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after {timeout_sec} seconds.")
        return ShellCommandOutput(
            stderr=f"Error: Command timed out after {timeout_sec} seconds.",
            return_code=-2,
            command_executed=command,
            status="error",
            message=f"Command timed out after {timeout_sec} seconds."
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred while running command '{command}': {e}")
        return ShellCommandOutput(
            stderr=f"An unexpected error occurred: {e}",
            return_code=-3,
            command_executed=command,
            status="error",
            message=f"An unexpected error occurred: {e}"
        ) 