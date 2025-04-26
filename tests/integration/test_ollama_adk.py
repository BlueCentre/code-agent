#!/usr/bin/env python
"""
Test script for Ollama integration with Google ADK.

This script demonstrates how to use Ollama with Google ADK directly,
without going through the CLI interface.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from code_agent.adk.models import OllamaLlm
from code_agent.adk.tools import (
    create_apply_edit_tool,
    create_read_file_tool,
    create_run_terminal_cmd_tool,
    create_web_search_tool,
)


async def main():
    # Get Ollama URL from environment or use default
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    # Get Ollama model from environment or use default
    ollama_model = os.environ.get("OLLAMA_MODEL", "llama3:latest")

    print(f"Using Ollama at {ollama_url} with model {ollama_model}")

    try:
        # Create Ollama model for ADK
        model = OllamaLlm(
            model_name=ollama_model,
            base_url=ollama_url,
            temperature=0.7,
        )

        # Create tools
        read_file_tool = create_read_file_tool()
        apply_edit_tool = create_apply_edit_tool()
        run_cmd_tool = create_run_terminal_cmd_tool()
        web_search_tool = create_web_search_tool()

        # Create agent
        agent = LlmAgent(
            model=model,
            name="ollama_test_agent",
            instruction="You are a helpful coding assistant.",
            tools=[read_file_tool, apply_edit_tool, run_cmd_tool, web_search_tool],
        )

        # Create session service for the agent
        session_service = InMemorySessionService()

        # Create a runner to execute the agent
        runner = Runner(agent=agent, app_name="test_ollama_app", session_service=session_service)

        # Get user input or use default prompt
        prompt = input("Enter prompt (or press Enter for default): ")
        if not prompt:
            prompt = "What is 2+2? Use your reasoning skills."

        print(f"\nSending prompt: {prompt}")
        print("\nWaiting for response...")

        # Create user content
        user_content = types.Content(role="user", parts=[types.Part(text=prompt)])

        # Create session ID
        session_id = "test_session_123"
        user_id = "test_user_456"

        # Create session if it doesn't exist
        session_service.create_session(app_name="test_ollama_app", user_id=user_id, session_id=session_id)

        # Run the agent with a runner
        response_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content):
            # Print events if in verbose mode
            # print(f"Event: {event.type}, Author: {event.author}")

            # Capture final response content
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text

        # Print the final result
        print("\n----- RESULT -----")
        print(response_text)
        print("----- END RESULT -----")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
