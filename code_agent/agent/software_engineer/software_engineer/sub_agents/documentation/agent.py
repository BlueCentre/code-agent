"""Documentation agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

# from software_engineer.tools.git_tools import (
#     git_status_tool,
# )
# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DocumentationResponse
# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.documentation import prompt

# from google.adk.tools.tool_mixins import BaseTool
from software_engineer.tools.filesystem import list_dir_tool, read_file_tool

documentation_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.0-flash-001",
    name="documentation_agent",
    description="Helps create clear and comprehensive documentation",
    instruction=prompt.DOCUMENTATION_AGENT_INSTR,
    tools=[read_file_tool, list_dir_tool],
    output_key="documentation",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)

# Placeholder for actual tool implementation
