"""
Memory integration test script.
"""

import asyncio

import pytest

from code_agent.adk import get_memory_service
from code_agent.adk.memory import SearchMemoryResponse
from code_agent.agent.custom_agent.agent import CodeAgent


@pytest.mark.asyncio
async def test_memory_integration():
    """Test memory integration end-to-end."""
    print("Starting memory integration test...")

    # Create an agent and initialize
    agent = CodeAgent()
    await agent.async_init()
    initial_session_id = agent.session_id  # Store initial session ID

    # Add some messages
    await agent.add_user_message("I need to create a Python application that uses OpenAI for embeddings.")
    await agent.add_assistant_message("I can help you with that. OpenAI provides great embeddings APIs for semantic search.")

    # Store the session in memory
    # session = await agent.session_manager.get_session(agent.session_id)
    memory_service = get_memory_service()
    # Remove incorrect call - memory is added via memory_service.add now
    # memory_service.add_session_to_memory(session)

    # Add specific facts to memory using the service
    memory_service.add(initial_session_id, "Fact about Python App", {"category": "details"})

    # Create a new session by clearing messages
    await agent.clear_messages()
    current_session_id = agent.session_id  # Get the new session ID
    assert initial_session_id != current_session_id
    await agent.add_user_message("What was I working on yesterday?")

    # Search memory from the *initial* session
    search_query = "Python application OpenAI"
    print(f"\nSearching memory for: '{search_query}' in session {initial_session_id}")
    memory_results: SearchMemoryResponse = memory_service.search(session_id=initial_session_id, query=search_query)

    print("\nMemory search results:")
    print(memory_results)
    assert len(memory_results.results) > 0, "Should have found results in memory from previous session"

    print("\nTest completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_memory_integration())
