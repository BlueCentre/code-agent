"""DevOps agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig
from google.adk.tools import FunctionTool

# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DevOpsResponse

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.devops import prompt
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

# Placeholder for actual tool implementation
