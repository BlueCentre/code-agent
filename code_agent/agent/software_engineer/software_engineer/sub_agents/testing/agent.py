"""Testing agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer.sub_agents.testing import prompt

# from google.adk.tools.tool_mixins import BaseTool
from software_engineer.tools.filesystem import list_dir_tool, read_file_tool

testing_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.0-flash-001",
    name="testing_agent",
    description="Helps generate test cases and testing strategies",
    instruction=prompt.TESTING_AGENT_INSTR,
    tools=[read_file_tool, list_dir_tool],
    output_key="testing",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=4096,
    ),
)

# Placeholder for actual tool implementation
