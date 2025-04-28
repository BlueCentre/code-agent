"""Debugging agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from ...tools.filesystem import (
    configure_approval_tool,
    edit_file_tool,
    list_dir_tool,
    read_file_tool,
)

# Updated import for shell command tools
from ...tools.shell_command import (
    check_shell_command_safety,
    configure_shell_approval,
    configure_shell_whitelist,
    execute_vetted_shell_command,
)
from ...tools.system_info import check_command_exists, get_os_info
from . import prompt

# from software_engineer.tools.git_tools import (
#     git_status_tool,
# )

debugging_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.5-pro-exp-03-25", #"gemini-2.0-flash-001",
    name="debugging_agent",
    description="Helps identify and fix code issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    tools=[
        read_file_tool,
        list_dir_tool,
        configure_approval_tool,
        edit_file_tool,
        configure_shell_approval,
        configure_shell_whitelist,
        check_shell_command_safety,
        execute_vetted_shell_command,
        get_os_info,
        check_command_exists,
    ],
    output_key="debugging",
    generate_content_config=GenerateContentConfig(
        temperature=0.8,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
