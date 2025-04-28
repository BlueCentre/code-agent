"""Design pattern agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

# NOTE: SWITCH TO ADK WEB or UNCOMMENT FOR ADK RUN
# Use absolute imports with correct directory name
# from code_agent.agent.software_engineer.software_engineer import prompt
# from code_agent.agent.software_engineer.software_engineer.shared_libraries.types import DesignPatternResponse
# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN
from software_engineer.sub_agents.design_pattern import prompt
from software_engineer.tools.search import google_search_grounding

design_pattern_agent = Agent(
    model="gemini-2.5-flash-preview-04-17",  # "gemini-2.0-flash-001",
    name="design_pattern_agent",
    description="Recommends design patterns for specific problems",
    instruction=prompt.DESIGN_PATTERN_AGENT_INSTR,
    # output_schema=DesignPatternResponse, # NOTE: Replace with tools
    output_key="design_pattern",
    generate_content_config=GenerateContentConfig(
        temperature=0.2,
        top_p=0.95,
        max_output_tokens=1000,
    ),
    tools=[google_search_grounding],
)

# Placeholder for actual tool implementation
