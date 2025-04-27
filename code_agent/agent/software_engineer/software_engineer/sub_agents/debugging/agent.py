"""Debugging agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

# from google.adk.tools.tool_mixins import BaseTool
# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DebuggingResponse
# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.debugging import prompt
from software_engineer.tools.filesystem import list_dir_tool, read_file_tool

# from software_engineer.tools.git_tools import (
#     git_status_tool,
# )

debugging_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.5-pro-exp-03-25", #"gemini-2.0-flash-001",
    name="debugging_agent",
    description="Helps identify and fix code issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    tools=[read_file_tool, list_dir_tool],
    output_key="debugging",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)

# Placeholder for actual tool implementation
