"""
Tools for configuring the agent at runtime.

These tools allow users to modify agent behavior without restarting.
"""

from code_agent.config import get_config
from code_agent.verbosity import get_controller


def set_verbosity(level: str) -> str:
    """
    Set the verbosity level of the agent.

    Args:
        level: The verbosity level to set (0-3, QUIET, NORMAL, VERBOSE, DEBUG)

    Returns:
        A confirmation message
    """
    # Get the verbosity controller
    controller = get_controller()

    # Set the level and get confirmation
    result = controller.set_level_from_string(level)

    # Also update the config for consistency
    config = get_config()

    # Find the numeric value of the new level
    new_level = controller.level_value
    config.verbosity = new_level

    # Return a helpful message
    level_descriptions = {
        0: "QUIET - Only essential information and errors",
        1: "NORMAL - Standard information for users",
        2: "VERBOSE - Additional details and warnings",
        3: "DEBUG - Detailed diagnostic information",
    }

    description = level_descriptions.get(new_level, "Custom level")
    return f"{result}\n{description}"


def get_config_info() -> str:
    """
    Get information about the current agent configuration.

    Returns:
        A string with the current configuration information
    """
    # Skip getting actual config and just return tool list
    return """
Available tools:
- read_file: Read content from a file
- apply_edit: Create or modify a file
- run_native_command: Execute a terminal command
- google_search: Search the internet for information
- set_verbosity: Change the verbosity level
"""


def simple_tools_list() -> str:
    """
    Get a simple list of available tools without any config information.

    Returns:
        A string with the list of available tools
    """
    return """
Available tools:
- read_file: Read content from a file
- apply_edit: Create or modify a file
- run_native_command: Execute a terminal command
- google_search: Search the internet for information
- set_verbosity: Change the verbosity level
"""
