"""Debugging agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer import prompt
from software_engineer.shared_libraries.types import DebuggingResponse

debugging_agent = Agent(
    model="gemini-2.0-flash-001",
    name="debugging_agent",
    description="Helps identify and fix code issues",
    instruction=prompt.DEBUGGING_AGENT_INSTR,
    output_schema=DebuggingResponse,
    output_key="debugging",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)
