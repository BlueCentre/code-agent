import os

import google.generativeai as genai  # Import genai for API key configuration

# ADK Imports
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools import google_search

# Intentionally avoid importing problematic ADK service modules
# Project Tool Imports
from code_agent.adk import tools as adk_tool_wrappers
from code_agent.config import get_config
from code_agent.verbosity import get_controller  # Updated import

# Direct API key configuration
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_STUDIO_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("WARNING: No API key found in environment. Check GOOGLE_API_KEY or AI_STUDIO_API_KEY. Models will not work.")

# --- Configuration and Model Instantiation ---
config = get_config()
verbosity_controller = get_controller()

# --- Specialized Agents ---

# 1. Search Agent
search_agent = Agent(
    name="SearchAgent",
    model=Gemini(model=config.default_model),
    tools=[google_search],
    instruction="""
    You are a specialized web search agent.
    Your sole purpose is to use the available google_search tool to find information on the web based on the user's query.
    Provide the search results clearly.
    Do not attempt any other tasks like file operations or command execution.
    """,
    description="Performs web searches using Google Search to find up-to-date information.",
)

# 2. Local Operations Agent
local_ops_agent = Agent(
    name="LocalOpsAgent",
    model=Gemini(model=config.default_model),
    # Get all custom tools (file, command, memory)
    tools=adk_tool_wrappers.get_all_tools(),
    instruction="""
    You are a specialized agent for local operations.
    Use your available tools (read_file, apply_edit, run_native_command, load_memory) to interact with the local file system, execute commands, and access long-term memory.
    - Use `read_file` before `apply_edit`.
    - Use `load_memory` to recall past information.
    - Use `run_native_command` for shell interactions (e.g., listing files `find . -name ... | cat`, checking status `git status | cat`).
    Do not perform web searches.
    """,  # noqa: E501
    description="Handles local tasks: reading/writing files, running commands, and accessing agent memory.",
)

# --- Root Orchestrator Agent ---

root_agent = Agent(
    name="RootAgent",
    model=Gemini(model=config.default_model),
    description="Orchestrates tasks, delegating to specialized agents (Search, LocalOps) or handling directly.",
    instruction="""
    - You are the primary agent. Analyze the user's request and determine the best course of action.
    - You want to gather a minimal information to help the user.
    - Please use only the agents and tools to fulfill all user rquest.
    - If the user asks to search the web or external knowledge bases, transfer to the agent 'SearchAgent'.
    - If the user ask about local file system operations (reading, writing, listing files), transfer to the agent 'LocalOpsAgent'.
    - Otherwise, handle the request yourself.
    """,
    sub_agents=[search_agent, local_ops_agent],
)


# --- Function to get the root agent (for use in CLI/main) ---
def get_root_agent() -> Agent:
    """Returns the configured root agent instance."""
    # Agents are defined globally, ADK handles model instantiation internally
    return root_agent
