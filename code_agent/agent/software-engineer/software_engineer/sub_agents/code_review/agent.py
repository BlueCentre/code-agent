"""Code review agent implementation."""

from google.adk.agents import Agent
from google.genai.types import GenerateContentConfig

from software_engineer import prompt
from software_engineer.shared_libraries.types import CodeReviewResponse
from software_engineer.tools.code_analysis import analyze_code_tool

code_review_agent = Agent(
    model="gemini-2.0-flash-001",
    name="code_review_agent",
    description="Analyzes code for issues and suggests improvements",
    instruction=prompt.CODE_REVIEW_AGENT_INSTR,
    tools=[analyze_code_tool],
    output_schema=CodeReviewResponse,
    output_key="code_review",
    generate_content_config=GenerateContentConfig(
        temperature=0.1,
        top_p=0.95,
    ),
)
