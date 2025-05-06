"""Implementation of the Software Engineer Agent with knowledge and experience of sub-agents."""

import logging

# from google.adk.agents import Agent
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

# from google.adk.tools import load_memory
from . import prompt

# Use relative imports from the 'software_engineer' sibling directory
from .sub_agents.code_quality.agent import code_quality_agent
from .sub_agents.code_review.agent import code_review_agent
from .sub_agents.debugging.agent import debugging_agent
from .sub_agents.design_pattern.agent import design_pattern_agent
from .sub_agents.devops.agent import devops_agent
from .sub_agents.documentation.agent import documentation_agent
from .sub_agents.testing.agent import testing_agent
from .tools import (
    check_command_exists_tool,
    check_shell_command_safety_tool,
    codebase_search_tool,
    configure_shell_approval_tool,
    configure_shell_whitelist_tool,
    edit_file_tool,
    execute_vetted_shell_command_tool,
    get_os_info_tool,
    google_search_grounding,
    list_dir_tool,
    # load_memory_from_file_tool, # Remove placeholder
    read_file_tool,
)

# Import tools via the tools package __init__
from .tools import (
    configure_approval_tool as configure_edit_approval_tool,  # Keep alias for now
)
from .tools.project_context import load_project_context

logger = logging.getLogger(__name__)


# --- Agent Definition ---

# Note: Using custom ripgrep-based codebase search in tools/code_search.py

# --- Example Agent using a model hosted on a vLLM endpoint ---

# Endpoint URL provided by your vLLM deployment
api_base_url = "http://localhost:11434/v1"

# Model name as recognized by *your* vLLM endpoint configuration
model_name_at_endpoint = "hosted_vllm/llama3.2"  # Example from vllm_test.py

# Authentication (Example: using gcloud identity token for a Cloud Run deployment)
# Adapt this based on your endpoint's security
# try:
#     gcloud_token = subprocess.check_output(
#         ["gcloud", "auth", "print-identity-token", "-q"]
#     ).decode().strip()
#     auth_headers = {"Authorization": f"Bearer {gcloud_token}"}
# except Exception as e:
#     print(f"Warning: Could not get gcloud token - {e}. Endpoint might be unsecured or require different auth.")
#     auth_headers = None # Or handle error appropriately


# REF: https://ai.google.dev/gemini-api/docs/rate-limits
# root_agent = Agent(
root_agent = LlmAgent(
    # model="gemini-2.5-flash-preview-04-17",
    model=LiteLlm(
        model=model_name_at_endpoint,
        api_base=api_base_url,
        # auth_headers=auth_headers,
    ),
    name="root_agent",
    description="An AI software engineer assistant that helps with various software development tasks",
    instruction=prompt.ROOT_AGENT_INSTR,
    sub_agents=[
        design_pattern_agent,
        documentation_agent,
        code_review_agent,
        code_quality_agent,
        testing_agent,
        debugging_agent,
        devops_agent,  # TODO: Move command tools to devops_agent with more guardrails
    ],
    tools=[
        read_file_tool,
        list_dir_tool,
        edit_file_tool,
        configure_edit_approval_tool,
        check_command_exists_tool,
        check_shell_command_safety_tool,
        configure_shell_approval_tool,
        configure_shell_whitelist_tool,
        execute_vetted_shell_command_tool,
        google_search_grounding,
        codebase_search_tool,
        get_os_info_tool,
    ],
    # Pass the function directly, not as a list
    before_agent_callback=load_project_context,
    output_key="software_engineer",
)
