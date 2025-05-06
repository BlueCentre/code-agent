"""
ADK Agent definition script for use with ADK.

This script defines an agent instance that the ADK runner can load.
"""

# import os

# Configure google.generativeai API key if using Gemini
# This is still needed as ADK's LlmAgent might rely on this global config
# when it receives a 'gemini-*' model string.
import google.generativeai as genai

# Load environment variables first (e.g., from .env)
from dotenv import load_dotenv

# Import necessary ADK and local components
from google.adk.agents import LlmAgent
from google.adk.models import Gemini  # Import ADK models directly

# Previously imported from removed module
# from code_agent.adk.models_v2 import create_model  # Use v2 models
from code_agent.config.config import get_config, initialize_config

load_dotenv()

# Import tools if you want to add them
# from your_tool_module import your_tool_function

# Ensure config is initialized (reads config files, env vars)
# Note: CLI overrides might not be directly available here,
# relies on env vars or config file primarily.
initialize_config()
config = get_config()

google_api_key_val = config.google_api_key or config.ai_studio_api_key
if google_api_key_val:
    # Configure genai globally
    genai.configure(api_key=google_api_key_val)

# Get the model instance
# Replace the create_model() call with direct instantiation
model_ref = Gemini(model_name="gemini-1.5-flash")

# --- Define the agent --- #
root_agent = LlmAgent(
    model=model_ref,  # Pass the BaseLlm instance
    name="adk_runner_agent",
    instruction="You are a helpful assistant responding via the ADK runner.",
    # Add tools here if desired:
    # tools=[your_tool_function],
)

print("Agent definition complete. Ready for use with ADK.")
