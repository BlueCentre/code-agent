"""Documentation agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig
from google.adk.tools import FunctionTool

# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DocumentationResponse

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.documentation import prompt
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

# Placeholder for actual tool implementation
