"""Design pattern agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig
from google.adk.tools import FunctionTool

# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DesignPatternResponse

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.design_pattern import prompt
from software_engineer.shared_libraries.types import DesignPatternResponse

design_pattern_agent = Agent(
    model="gemini-2.0-flash-001",
    name="design_pattern_agent",
    description="Recommends design patterns for specific problems",
    instruction=prompt.DESIGN_PATTERN_AGENT_INSTR,
    output_schema=DesignPatternResponse,
    output_key="design_pattern",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
    ),
)

# Placeholder for actual tool implementation
