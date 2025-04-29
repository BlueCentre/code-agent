import logging
import platform
import shutil

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OSInfoOutput(BaseModel):
    """Output model for the get_os_info tool."""

    system: str = Field(description="Operating system name (e.g., 'Linux', 'Darwin', 'Windows').")
    release: str = Field(description="Operating system release (e.g., '5.15.0-78-generic').")
    version: str = Field(description="Operating system version.")
    machine: str = Field(description="Machine hardware name (e.g., 'x86_64').")


def get_os_info() -> OSInfoOutput:
    """Gets basic operating system information."""
    logger.info("Getting operating system information.")
    try:
        return OSInfoOutput(system=platform.system(), release=platform.release(), version=platform.version(), machine=platform.machine())
    except Exception as e:
        logger.exception(f"Failed to get OS info: {e}")
        # Return placeholder values on error
        return OSInfoOutput(system="Unknown", release="Unknown", version="Unknown", machine="Unknown")


class CommandExistsInput(BaseModel):
    """Input model for the check_command_exists tool."""

    command_name: str = Field(..., description="The name of the command to check.")


class CommandExistsOutput(BaseModel):
    """Output model for the check_command_exists tool."""

    exists: bool = Field(description="True if the command exists in the system PATH, False otherwise.")
    path: str | None = Field(None, description="The full path to the command if found, otherwise None.")


def check_command_exists(args: dict) -> CommandExistsOutput:
    """Checks if a given command exists in the system's PATH.

    Args:
        args (dict): A dictionary containing:
            command_name (str): The name of the command to check.
    """
    command_name = args.get("command_name")
    if not command_name:
        logger.error("'command_name' argument missing for check_command_exists.")
        return CommandExistsOutput(exists=False, path=None)

    logger.info(f"Checking existence of command: {command_name}")
    try:
        command_path = shutil.which(command_name)
        if command_path:
            logger.info(f"Command '{command_name}' found at: {command_path}")
            return CommandExistsOutput(exists=True, path=command_path)
        else:
            logger.warning(f"Command '{command_name}' not found in PATH.")
            return CommandExistsOutput(exists=False, path=None)
    except Exception as e:
        logger.exception(f"Error checking command '{command_name}': {e}")
        return CommandExistsOutput(exists=False, path=None)
