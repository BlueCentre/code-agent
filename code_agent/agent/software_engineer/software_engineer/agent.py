"""Implementation of the Software Engineer Agent using Google Agent Development Kit."""

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN

import logging

from google.adk.agents import Agent

# from google.adk.runtime.executors import SequentialExecutor
# from google.adk.runtime.planner import SequentialPlanner
# Use relative imports from the 'software_engineer' sibling directory
from . import prompt
from .sub_agents.code_quality.agent import code_quality_agent
from .sub_agents.code_review.agent import code_review_agent
from .sub_agents.debugging.agent import debugging_agent
from .sub_agents.design_pattern.agent import design_pattern_agent
from .sub_agents.devops.agent import devops_agent
from .sub_agents.documentation.agent import documentation_agent
from .sub_agents.testing.agent import testing_agent

# Import the code search tool from the new location
from .tools import codebase_search_tool
from .tools.filesystem import (
    configure_approval_tool as configure_edit_approval_tool,
)
from .tools.filesystem import (
    edit_file_tool,
    list_dir_tool,
    read_file_tool,
)

# Import memory tools
# from .tools.memory import forget_tool, memorize_list_tool, memorize_tool
from .tools.project_context import load_project_context
from .tools.search import google_search_grounding

# Updated import for shell command tools
from .tools.shell_command import (
    check_command_exists_tool,
    check_shell_command_safety_tool,
    configure_shell_approval_tool,
    configure_shell_whitelist_tool,
    execute_vetted_shell_command_tool,
)
from .tools.system_info import get_os_info_tool

logger = logging.getLogger(__name__)

# Note: Using custom ripgrep-based codebase search in tools/code_search.py

# REF: https://ai.google.dev/gemini-api/docs/rate-limits
root_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",
    name="root_agent",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[
        code_review_agent,
        design_pattern_agent,
        testing_agent,
        debugging_agent,
        documentation_agent,
        devops_agent,
        code_quality_agent,
    ],
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        configure_edit_approval_tool,
        check_command_exists_tool,
        check_shell_command_safety_tool,
        configure_shell_approval_tool,
        configure_shell_whitelist_tool,
        execute_vetted_shell_command_tool,
        google_search_grounding,
        codebase_search_tool,
        get_os_info_tool,
        # memorize_tool,
        # memorize_list_tool,
        # forget_tool,
    ],
    before_agent_callback=load_project_context,
    output_key="software_engineer",
)
