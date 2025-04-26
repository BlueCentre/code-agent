"""Testing agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer import prompt
from software_engineer.shared_libraries.types import TestingResponse

testing_agent = Agent(
    model="gemini-2.0-flash-001",
    name="testing_agent",
    description="Helps generate test cases and testing strategies",
    instruction=prompt.TESTING_AGENT_INSTR,
    output_schema=TestingResponse,
    output_key="testing",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)
