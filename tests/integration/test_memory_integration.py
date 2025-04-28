"""
Memory integration test script.
"""

import asyncio

import pytest

# Import ADK session service and event types
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from code_agent.adk import get_memory_service
from code_agent.adk.memory import (
    SearchMemoryResponse,
)

# Keep root_agent import for context if needed, though not directly interacted with


@pytest.fixture
def adk_session_service_memory_test():  # Renamed fixture to avoid conflict
    """Fixture providing a real InMemorySessionService instance for this test."""
    return InMemorySessionService()


@pytest.mark.asyncio
async def test_memory_integration(adk_session_service_memory_test: InMemorySessionService):  # Use the fixture
    """Test memory integration end-to-end using ADK session service."""
    print("Starting memory integration test...")
    session_service = adk_session_service_memory_test  # Use the injected service

    # --- Session 1 ---
    # Create the initial session
    session1 = session_service.create_session(app_name="code_agent", user_id="test_user")
    initial_session_id = session1.id
    print(f"Created initial session ID: {initial_session_id}")

    # Simulate adding messages to session 1 history directly via the session service
    user_message_content = "I need to create a Python application that uses OpenAI for embeddings."
    assistant_message_content = "I can help you with that. OpenAI provides great embeddings APIs for semantic search."

    user_event = Event(author="user", content=Content(parts=[Part(text=user_message_content)]))
    assistant_event = Event(author="assistant", content=Content(parts=[Part(text=assistant_message_content)]))

    # Pass the actual session object to append_event
    session_service.append_event(session1, event=user_event)
    session_service.append_event(session1, event=assistant_event)
    print(f"Appended user and assistant events to session {initial_session_id}")

    # Add specific facts to memory using the service for session 1
    memory_service = get_memory_service()
    memory_service.add(initial_session_id, "Fact about Python App", {"category": "details"})
    print(f"Added specific memory fact to session {initial_session_id}")

    # --- Session 2 ---
    # Create a new session to simulate clearing/starting over
    session2 = session_service.create_session(app_name="code_agent", user_id="test_user")
    current_session_id = session2.id
    print(f"Created second session ID: {current_session_id}")
    assert initial_session_id != current_session_id

    # Simulate adding a user message to the new session via the session service
    new_user_message_content = "What was I working on yesterday?"
    new_user_event = Event(author="user", content=Content(parts=[Part(text=new_user_message_content)]))
    session_service.append_event(session2, event=new_user_event)  # Pass session2 object
    print(f"Appended user event to session {current_session_id}")

    # Search memory from the *initial* session
    search_query = "Python application OpenAI"
    print(f"\nSearching memory for: '{search_query}' in initial session {initial_session_id}")
    memory_results: SearchMemoryResponse = memory_service.search(session_id=initial_session_id, query=search_query)

    print("\nMemory search results:")
    # Use a more robust way to print results if it's an object
    print(f"  Found {len(memory_results.results)} results.")
    for i, res in enumerate(memory_results.results):
        print(f"  Result {i+1}: Score={res.score}, Content='{res.content[:50]}...'")  # Print truncated content

    assert len(memory_results.results) > 0, "Should have found results in memory from previous session"

    print("\nTest completed successfully!")


# Keep the main block if direct execution is desired, but update it
if __name__ == "__main__":
    # Need to manually create the service for direct run
    test_service = InMemorySessionService()
    # Run the async function, but the service calls within are sync
    asyncio.run(test_memory_integration(test_service))
