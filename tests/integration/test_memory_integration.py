"""
Memory integration test script.
"""

import asyncio

from code_agent.adk import get_memory_service
from code_agent.agent.custom_agent.agent import CodeAgent


async def test_memory_integration():
    """Test memory integration end-to-end."""
    print("Starting memory integration test...")

    # Create an agent and initialize
    agent = CodeAgent()
    await agent.async_init()

    # Add some messages
    await agent.add_user_message("I need to create a Python application that uses OpenAI for embeddings.")
    await agent.add_assistant_message("I can help you with that. OpenAI provides great embeddings APIs for semantic search.")

    # Store the session in memory
    session = await agent.session_manager.get_session(agent.session_id)
    memory_service = get_memory_service()
    memory_service.add_session_to_memory(session)

    # Create a new session
    await agent.clear_messages()
    await agent.add_user_message("What was I working on yesterday?")

    # Search memory
    from code_agent.tools.memory_tools import load_memory

    memory_results = await load_memory("Python application OpenAI")

    print("\nMemory search results:")
    print(memory_results)

    print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_memory_integration())
