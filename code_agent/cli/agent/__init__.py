"""
ADK Agent definition script for use with 'adk run'.

This script defines an agent instance that the ADK CLI runner can load.
"""

# import json # Removed F401
# import sys # Removed F401
# from typing import List # Removed F401

import os

import google.generativeai as genai  # Moved up

# import typer # Removed F401
from dotenv import load_dotenv

# from rich.panel import Panel # Removed F401
# ADK Imports (ensure these are correct)
from google.adk.agents import LlmAgent
from rich import print as rich_print

# Local application imports
# from code_agent.adk.client import ADKClient # Removed F401
from code_agent.adk.models_v2 import create_model

# from code_agent.adk.services import get_adk_session_manager # Removed F401
# from code_agent.agent.cli_runner import ADKWorkflowRunner # Removed F401
from code_agent.config import get_api_key, get_config, initialize_config  # Added get_api_key

# from code_agent.config.settings_based_config import ApiKeys, CodeAgentSettings # Removed F401
# from code_agent.utils import detect_environment # Removed F401

# Define root_agent at module level
root_agent = None


# Use this print function to ensure consistent printing behavior
# and make it easier to mock in tests
def agent_print(message):
    """Print function that can be easily mocked in tests."""
    rich_print(message)


def initialize_agent():
    """Initialize the agent with proper configuration."""
    global root_agent

    # Load environment variables from .env file
    load_dotenv()

    agent_print("Initializing configuration...")
    # Ensure config is initialized (reads config files, env vars)
    initialize_config()  # Now defined
    config = get_config()

    agent_print(f"Resolved Provider: {config.default_provider}")
    agent_print(f"Resolved Model: {config.default_model}")

    # Configure google.generativeai API key if using Gemini
    # Use the get_api_key helper function to access the api key
    google_api_key_val = get_api_key("ai_studio")
    if google_api_key_val:
        agent_print("Configuring genai globally with key from AI_STUDIO_API_KEY")
        genai.configure(api_key=google_api_key_val)
    elif config.default_provider == "ai_studio":
        agent_print("Warning: ai_studio provider selected but no AI_STUDIO_API_KEY found.")
        agent_print("         Agent might rely on Application Default Credentials (ADC).")

    agent_print("Creating model reference...")
    # Get the model string (for Gemini) or BaseLlm instance (for others)
    model_ref = create_model()

    agent_print(f"Model reference created: {type(model_ref)}")

    # --- Define the agent --- #
    # Simple LlmAgent for testing. Replace with get_root_agent() for multi-agent.
    agent_print("Defining agent instance...")
    root_agent = LlmAgent(  # Now defined
        model=model_ref,  # Pass the string or BaseLlm instance
        name="adk_cli_runner_agent",
        instruction="You are a helpful assistant responding via the ADK CLI runner.",
        # Add tools here if desired:
        # tools=[your_tool_function],
    )

    agent_print("Agent definition complete. Ready for 'adk run'.")
    return root_agent


# Initialize the agent when the module is imported in a non-test environment
# Only auto-initialize in non-test environments
if not os.environ.get("PYTEST_CURRENT_TEST"):
    root_agent = initialize_agent()
