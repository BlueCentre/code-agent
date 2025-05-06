import ast
import json
import logging
import os
import shlex
import shutil  # <-- Added import
import subprocess
from typing import Literal, Optional

# Import ToolContext for state management
from google.adk.tools import (
    FunctionTool,  # Ensure FunctionTool is imported if not already
    ToolContext,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def parse_args(args):
    """Utility function to parse arguments for tool functions.

    Handles both dictionary and string arguments for compatibility with
    different LLM models (Gemini uses dict, LLaMA uses str).

    Args:
        args: The arguments to parse, either as a dictionary or string.

    Returns:
        dict: The parsed arguments as a dictionary.

    Raises:
        ValueError: If the arguments cannot be parsed.
    """
    if isinstance(args, dict):
        return args
    elif isinstance(args, str):
        try:
            # Try parsing as JSON first
            try:
                return json.loads(args)
            except json.JSONDecodeError:
                # If not valid JSON, try parsing as a Python literal
                return ast.literal_eval(args)
        except (ValueError, SyntaxError, AttributeError) as e:
            logger.error(f"Failed to parse args string: {e}")
            raise ValueError(f"Failed to parse arguments: {e}")
    else:
        logger.error(f"Unsupported args type: {type(args)}")
        raise ValueError(f"Unsupported args type: {type(args)}")


# --- Configuration Tool --- #


class ConfigureShellApprovalInput(BaseModel):
    """Input model for configuring shell command approval."""

    require_approval: bool = Field(..., description="Set to true to require approval for shell commands, false to disable.")


class ConfigureShellApprovalOutput(BaseModel):
    """Output model for configuring shell command approval."""

    status: str


def configure_shell_approval(args: dict, tool_context: ToolContext) -> ConfigureShellApprovalOutput:
    """Configures whether running shell commands requires user approval for the current session.
    This is separate from file edit approvals which are managed by configure_edit_approval.

    Args:
        args (dict): A dictionary containing:
            require_approval (bool): Set to true to require approval for shell commands, false to disable.
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for accessing session state.
    """
    try:
        args_dict = parse_args(args)
        require_approval = args_dict.get("require_approval")
    except ValueError as e:
        return ConfigureShellApprovalOutput(status=str(e))

    # Convert string representations of booleans to actual booleans
    if isinstance(require_approval, str):
        if require_approval.lower() == "true":
            require_approval = True
        elif require_approval.lower() == "false":
            require_approval = False

    # Add validation for the boolean argument
    if require_approval is None or not isinstance(require_approval, bool):
        message = "Error: 'require_approval' argument is missing or not a boolean (true/false)."
        logger.error(message)
        return ConfigureShellApprovalOutput(status=message)

    tool_context.state["require_shell_approval"] = require_approval
    status = "enabled" if require_approval else "disabled"
    logger.info(f"Shell command approval requirement set to: {status}")
    return ConfigureShellApprovalOutput(
        status=f"Shell command approval requirement is now {status}. Shell commands {'' if require_approval else 'no longer '}require explicit approval."
    )


# --- Whitelist Configuration Tool --- #


class ConfigureShellWhitelistInput(BaseModel):
    """Input model for configuring the shell command whitelist."""

    action: Literal["add", "remove", "list", "clear"] = Field(..., description="Action to perform: add, remove, list, or clear.")
    command: Optional[str] = Field(None, description="The command to add or remove (required for 'add' and 'remove' actions).")


class ConfigureShellWhitelistOutput(BaseModel):
    """Output model for configuring the shell command whitelist."""

    status: str
    whitelist: Optional[list[str]] = Field(None, description="The current whitelist (only for 'list' action).")


def configure_shell_whitelist(args: dict, tool_context: ToolContext) -> ConfigureShellWhitelistOutput:
    """Manages the whitelist of shell commands that bypass approval.

    Note: To completely disable shell approval checks, use the `configure_shell_approval`
    function with `require_approval` set to `false` instead.

    Args:
        args (dict): A dictionary containing:
            action (Literal["add", "remove", "list", "clear"]): The action.
            command (Optional[str]): The command for add/remove.
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for accessing session state.
    """
    try:
        args_dict = parse_args(args)
        action = args_dict.get("action")
        command = args_dict.get("command")
    except ValueError as e:
        return ConfigureShellWhitelistOutput(status=str(e))

    # Default safe commands (adjust as needed)
    DEFAULT_SAFE_COMMANDS = [
        "ls",
        "grep",
        "find",
        "cat",
        "pwd",
        "echo",
        "git status",
        "head",
        "tail",
        "wc",
        "git diff",
        "git log",
        "which",
        "ping",
        "host",
        "dig",
        "nslookup",
        "ss",
        "uname",
        "uptime",
        "date",
        "time",
        "df",
        "du",
        "free",
        "stat",
        "ps",
        "pgrep",
        "ip addr",
        "ip route",
        "traceroute",
        "git grep",
        "git branch",
        "git branch --show-current",  # Specific safe variant
        "git tag",
        "git remote -v",
        "git config --list",
        "docker ps",
        "docker images",
        "kubectl get",
        "kubectl describe",
        "kubectl logs",
        "kubectl cluster-info",
        "kubectl config view",
        "kubectl version",
        "kubectl api-resources",
        "kubectl api-versions",
        "kubectl top",
    ]

    # Initialize whitelist in state if it doesn't exist
    if "shell_command_whitelist" not in tool_context.state:
        # Initialize with default safe commands
        tool_context.state["shell_command_whitelist"] = DEFAULT_SAFE_COMMANDS[:]
        logger.info(f"Initialized shell command whitelist with defaults: {DEFAULT_SAFE_COMMANDS}")

    whitelist: list[str] = tool_context.state["shell_command_whitelist"]

    if action == "add":
        if not command:
            return ConfigureShellWhitelistOutput(status="Error: 'command' is required for 'add' action.")
        if command not in whitelist:
            whitelist.append(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Added command '{command}' to shell whitelist.")
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' added to whitelist.")
        else:
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' is already in the whitelist.")
    elif action == "remove":
        if not command:
            return ConfigureShellWhitelistOutput(status="Error: 'command' is required for 'remove' action.")
        if command in whitelist:
            whitelist.remove(command)
            tool_context.state["shell_command_whitelist"] = whitelist  # Update state
            logger.info(f"Removed command '{command}' from shell whitelist.")
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' removed from whitelist.")
        else:
            return ConfigureShellWhitelistOutput(status=f"Command '{command}' not found in whitelist.")
    elif action == "list":
        return ConfigureShellWhitelistOutput(status="Current whitelist retrieved.", whitelist=list(whitelist))  # Return a copy
    elif action == "clear":
        tool_context.state["shell_command_whitelist"] = []
        logger.info("Cleared shell command whitelist.")
        return ConfigureShellWhitelistOutput(status="Shell command whitelist cleared.")
    else:
        return ConfigureShellWhitelistOutput(status=f"Error: Invalid action '{action}'. Valid actions are: add, remove, list, clear.")


# --- Check Command Existence Tool --- #


class CheckCommandExistsInput(BaseModel):
    """Input model for checking command existence."""

    command: str = Field(..., description="The command name (e.g., 'git', 'ls') to check for existence.")


class CheckCommandExistsOutput(BaseModel):
    """Output model for checking command existence."""

    exists: bool
    command_checked: str
    message: str


def check_command_exists(args: dict, tool_context: ToolContext) -> CheckCommandExistsOutput:
    """Checks if a command exists in the system's PATH. Extracts the base command.

    Args:
        args (dict): A dictionary containing:
            command (str): The command name to check.
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for accessing session state.
    """
    try:
        args_dict = parse_args(args)
        command_name = args_dict.get("command")
    except ValueError as e:
        return CheckCommandExistsOutput(exists=False, command_checked="", message=str(e))

    base_command = None
    message = ""

    if not command_name:
        message = "Error: 'command' argument is missing."
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=command_name or "", message=message)

    try:
        # Extract base command if it includes arguments (shutil.which needs the command name only)
        parts = shlex.split(command_name)
        if parts:
            base_command = parts[0]
        else:
            message = f"Could not parse base command from input: '{command_name}'"
            logger.warning(message)
            return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    except ValueError as e:
        message = f"Error parsing command '{command_name}': {e}"
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    if not base_command:  # Should not happen if parsing worked, but check anyway
        message = "Error: Could not determine base command."
        logger.error(message)
        return CheckCommandExistsOutput(exists=False, command_checked=command_name, message=message)

    exists = shutil.which(base_command) is not None
    status_msg = "exists" if exists else "does not exist"
    message = f"Command '{base_command}' {status_msg} in system PATH."
    logger.info(f"Checked existence for command '{base_command}': {exists}")
    return CheckCommandExistsOutput(exists=exists, command_checked=base_command, message=message)


# --- Shell Command Safety Check Tool --- #


class CheckShellCommandSafetyInput(BaseModel):
    """Input model for checking shell command safety."""

    command: str = Field(..., description="The shell command to check.")


class CheckShellCommandSafetyOutput(BaseModel):
    """Output model for checking shell command safety."""

    status: Literal["whitelisted", "approval_disabled", "approval_required"] = Field(..., description="The safety status of the command.")
    command: str = Field(..., description="The command that was checked.")
    message: str = Field(..., description="Explanation of the status.")


def check_shell_command_safety(args: dict, tool_context: ToolContext) -> CheckShellCommandSafetyOutput:
    """Checks if a shell command is safe to run without explicit user approval.

    Checks against the configured whitelist and the session's approval requirement.
    Does NOT execute the command.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to check.
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for accessing session state.
    """
    try:
        args_dict = parse_args(args)
        command = args_dict.get("command")
    except ValueError as e:
        return CheckShellCommandSafetyOutput(status="approval_required", command=str(args), message=str(e))

    if not command:
        # Technically this shouldn't happen with Pydantic validation, but belt-and-suspenders
        return CheckShellCommandSafetyOutput(
            status="approval_required",
            command="[no command provided]",
            message="No command string was provided to check.",
        )

    # Check if shell approval is disabled globally
    if "require_shell_approval" in tool_context.state and tool_context.state["require_shell_approval"] is False:
        return CheckShellCommandSafetyOutput(
            status="approval_disabled",
            command=command,
            message="Shell command approval is disabled for this session.",
        )

    # Check if the command is in the whitelist
    whitelist = tool_context.state.get("shell_command_whitelist", [])
    if command in whitelist:
        return CheckShellCommandSafetyOutput(
            status="whitelisted",
            command=command,
            message=f"Command '{command}' is in the whitelist.",
        )

    # Default: require approval for any command not explicitly whitelisted
    return CheckShellCommandSafetyOutput(
        status="approval_required",
        command=command,
        message=f"Command '{command}' requires explicit approval.",
    )


# --- Vetted Shell Command Execution Tool --- #


class ExecuteVettedShellCommandInput(BaseModel):
    """Input model for the execute_vetted_shell_command tool."""

    command: str = Field(..., description="The shell command to execute. Should have been vetted first.")
    working_directory: Optional[str] = Field(None, description="Optional working directory to run the command in.")
    timeout: int = Field(60, description="Timeout in seconds for the command execution.")


class ExecuteVettedShellCommandOutput(BaseModel):
    """Output model for the execute_vetted_shell_command tool."""

    stdout: str | None = Field(None, description="The standard output of the command.")
    stderr: str | None = Field(None, description="The standard error of the command.")
    return_code: int | None = Field(None, description="The return code of the command.")
    command_executed: str | None = Field(None, description="The command that was executed.")
    status: str = Field(description="Status: 'executed' or 'error'.")
    message: str = Field(description="Additional information about the status.")


def execute_vetted_shell_command(args: dict, tool_context: ToolContext) -> ExecuteVettedShellCommandOutput:
    """Executes a shell command that has already been verified as safe or approved.

    Args:
        args (dict): A dictionary containing:
            command (str): The shell command to execute.
            working_directory (Optional[str]): Optional working directory.
            timeout (Optional[int]): Timeout in seconds (default: 60).
            Also handles string representation of arguments for LLaMA models.
        tool_context (ToolContext): The context for the tool.

    Returns:
        ExecuteVettedShellCommandOutput: Result of the command execution.
    """
    try:
        args_dict = parse_args(args)
        command = args_dict.get("command")
        working_directory = args_dict.get("working_directory")
        timeout = args_dict.get("timeout", 60)
    except ValueError as e:
        return ExecuteVettedShellCommandOutput(status="error", message=str(e), command_executed=str(args))

    if not command:
        logger.error("No command provided for execution.")
        return ExecuteVettedShellCommandOutput(
            status="error",
            message="No command provided for execution.",
            command_executed=None,
            stdout=None,
            stderr=None,
            return_code=None,
        )

    # Ensure timeout is an integer
    try:
        timeout = int(timeout)
    except (ValueError, TypeError):
        logger.warning(f"Invalid timeout value: {timeout}, using default 60 seconds.")
        timeout = 60

    # Use working_directory if provided and it exists
    cwd = None
    if working_directory:
        if not os.path.isdir(working_directory):
            logger.warning(f"Working directory '{working_directory}' does not exist, using current directory.")
        else:
            cwd = working_directory

    # Set environment variables to prevent interactive prompts
    # And make sure we're not using ANSI colors in the output
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",  # Don't prompt for credentials
            "TERM": "dumb",  # Disable ANSI colors
            "FORCE_COLOR": "0",  # Disable colored output
            "NO_COLOR": "1",  # Disable colored output
            "CI": "1",  # Pretend we're in a CI environment
        }
    )

    try:
        logger.info(f"Executing command: {command}")
        # Use shell=True for complex commands with pipes, redirects, etc.
        # This is safe because we've already vetted the command
        # But we should still be cautious about wildcard expansion and special chars
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            env=env,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""
        return_code = process.returncode

        # Log the result
        log_msg = f"Command '{command}' executed with return code {return_code}"
        if return_code == 0:
            logger.info(log_msg)
        else:
            logger.warning(f"{log_msg}. stderr: {stderr[:100]}...")

        # Return the result
        return ExecuteVettedShellCommandOutput(
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            command_executed=command,
            status="executed",
            message=f"Command executed with return code {return_code}.",
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after {timeout} seconds.")
        return ExecuteVettedShellCommandOutput(
            stdout=None,
            stderr=None,
            return_code=None,
            command_executed=command,
            status="error",
            message=f"Command timed out after {timeout} seconds.",
        )
    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}")
        return ExecuteVettedShellCommandOutput(
            stdout=None,
            stderr=str(e),
            return_code=None,
            command_executed=command,
            status="error",
            message=f"Command execution error: {e}",
        )


# --- Tool Registrations --- # <-- Added section (optional but good practice)

# Wrap functions with FunctionTool
# Note: This assumes FunctionTool is imported or available in the scope

configure_shell_approval_tool = FunctionTool(configure_shell_approval)
configure_shell_whitelist_tool = FunctionTool(configure_shell_whitelist)
check_command_exists_tool = FunctionTool(check_command_exists)  # <-- Added tool
check_shell_command_safety_tool = FunctionTool(check_shell_command_safety)
execute_vetted_shell_command_tool = FunctionTool(execute_vetted_shell_command)
