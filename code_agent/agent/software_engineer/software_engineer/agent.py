"""Implementation of the Software Engineer Agent using Google Agent Development Kit."""

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN

from google.adk.agents import Agent
# from google.adk.runtime.executors import SequentialExecutor
# from google.adk.runtime.planner import SequentialPlanner

# Use relative imports from the 'software_engineer' sibling directory
from . import prompt
from .sub_agents.code_review.agent import code_review_agent
from .sub_agents.debugging.agent import debugging_agent
from .sub_agents.design_pattern.agent import design_pattern_agent
from .sub_agents.devops.agent import devops_agent
from .sub_agents.documentation.agent import documentation_agent
from .sub_agents.testing.agent import testing_agent
from .tools.project_context import load_project_context
from .tools.search import google_search_grounding
from .tools.filesystem import (
    read_file_tool,
    list_dir_tool,
    edit_file_tool,
    configure_approval_tool,
)

# REF: https://ai.google.dev/gemini-api/docs/rate-limits
root_agent = Agent(
    model="gemini-2.5-flash-preview-04-17", #"gemini-2.5-pro-exp-03-25", #"gemini-2.0-flash-001",
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
    ],
    tools=[
        google_search_grounding,
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        configure_approval_tool,
    ],
    before_agent_callback=load_project_context,
)
