"""Documentation agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer import prompt
from software_engineer.shared_libraries.types import DocumentationResponse

documentation_agent = Agent(
    model="gemini-2.0-flash-001",
    name="documentation_agent",
    description="Helps create clear and comprehensive documentation",
    instruction=prompt.DOCUMENTATION_AGENT_INSTR,
    output_schema=DocumentationResponse,
    output_key="documentation",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)
