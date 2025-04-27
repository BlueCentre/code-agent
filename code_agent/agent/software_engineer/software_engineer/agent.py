"""Implementation of the Software Engineer Agent using Google Agent Development Kit."""

# NOTE: SWITCH TO ADK WEB or COMMENT OUT FOR ADK RUN

from google.adk.agents import Agent

# Use relative imports from the 'software_engineer' sibling directory
from software_engineer import prompt
from software_engineer.sub_agents.code_review.agent import code_review_agent
from software_engineer.sub_agents.debugging.agent import debugging_agent
from software_engineer.sub_agents.design_pattern.agent import design_pattern_agent
from software_engineer.sub_agents.devops.agent import devops_agent
from software_engineer.sub_agents.documentation.agent import documentation_agent
from software_engineer.sub_agents.testing.agent import testing_agent
from software_engineer.tools.project_context import load_project_context

root_agent = Agent(
    model="gemini-2.0-flash-001",
    name="root_agent",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[
        code_review_agent,
        design_pattern_agent,
        testing_agent,
        debugging_agent,
        documentation_agent,
        devops_agent,
    ],
    before_agent_callback=load_project_context,
)
