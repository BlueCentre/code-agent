"""
ADK Agent definition script for use with 'adk run'.

This script defines an agent instance that the ADK CLI runner can load.
"""

# import json # Removed F401
# import sys # Removed F401
# from typing import List # Removed F401

import google.generativeai as genai  # Moved up

# import typer # Removed F401
from dotenv import load_dotenv

# from rich.panel import Panel # Removed F401
# ADK Imports (ensure these are correct)
from google.adk.agents import LlmAgent
from rich import print

# Local application imports
# from code_agent.adk.client import ADKClient # Removed F401
from code_agent.adk.models_v2 import create_model

# from code_agent.adk.services import get_adk_session_manager # Removed F401
# from code_agent.agent.cli_runner import ADKWorkflowRunner # Removed F401
from code_agent.config import get_config, initialize_config  # Added initialize_config

# from code_agent.config.settings_based_config import ApiKeys, CodeAgentSettings # Removed F401
# from code_agent.utils import detect_environment # Removed F401

# Load environment variables from .env file
load_dotenv()

print("Initializing configuration...")
# Ensure config is initialized (reads config files, env vars)
initialize_config() # Now defined
config = get_config()

print(f"Resolved Provider: {config.default_provider}")
print(f"Resolved Model: {config.default_model}")

# Configure google.generativeai API key if using Gemini

google_api_key_val = config.google_api_key or config.ai_studio_api_key
if google_api_key_val:
    key_source = "GOOGLE_API_KEY" if config.google_api_key else "AI_STUDIO_API_KEY"
    print(f"Configuring genai globally with key from {key_source}")
    genai.configure(api_key=google_api_key_val)
elif config.default_provider == "ai_studio":
    print("Warning: ai_studio provider selected but no GOOGLE_API_KEY/AI_STUDIO_API_KEY found.")
    print("         Agent might rely on Application Default Credentials (ADC).")


print("Creating model reference...")
# Get the model string (for Gemini) or BaseLlm instance (for others)
model_ref = create_model()

print(f"Model reference created: {type(model_ref)}")

# --- Define the agent --- #
# Simple LlmAgent for testing. Replace with get_root_agent() for multi-agent.
print("Defining agent instance...")
root_agent = LlmAgent( # Now defined
    model=model_ref,  # Pass the string or BaseLlm instance
    name="adk_cli_runner_agent",
    instruction="You are a helpful assistant responding via the ADK CLI runner.",
    # Add tools here if desired:
    # tools=[your_tool_function],
)

print("Agent definition complete. Ready for 'adk run'.")
