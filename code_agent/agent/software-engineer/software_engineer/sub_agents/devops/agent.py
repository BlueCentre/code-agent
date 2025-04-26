"""DevOps agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer import prompt
from software_engineer.shared_libraries.types import DevOpsResponse

devops_agent = Agent(
    model="gemini-2.0-flash-001",
    name="devops_agent",
    description="Helps with deployment, CI/CD, and infrastructure",
    instruction=prompt.DEVOPS_AGENT_INSTR,
    output_schema=DevOpsResponse,
    output_key="devops",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)
