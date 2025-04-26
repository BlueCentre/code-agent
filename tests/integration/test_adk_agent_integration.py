"""
Integration tests for the CodeAgent ADK implementation.

These tests focus on the agent's interaction with the ADK session
manager and the overall turn-taking logic, potentially mocking the LLM
but using real session services.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.sessions import InMemorySessionService

from code_agent.agent.custom_agent.agent import CodeAgent
from code_agent.config import CodeAgentSettings

# Import ApiKeys for fixture
from code_agent.config.settings_based_config import ApiKeys

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_config_integration():
    """Fixture for a mock CodeAgentSettings used in integration tests."""
    # Create an actual ApiKeys instance
    actual_api_keys = ApiKeys(mock_provider="test-key")

    return CodeAgentSettings(
        default_provider="mock_provider",  # Use mock provider
        default_model="mock_model",  # Use mock model
        api_keys=actual_api_keys,  # Use the actual ApiKeys instance
        rules=[],
        native_command_allowlist=[],
        ollama={},
        verbosity=0,  # Reduce noise for integration tests
        max_tokens=1000,
        max_tool_calls=10,
        # security field will use its default factory if not provided
    )


@pytest.fixture
def adk_session_service():
    """Fixture providing a real InMemorySessionService instance."""
    # Use the actual factory, but ensure it returns an InMemory service for tests
    return InMemorySessionService()  # Explicitly use InMemory


@pytest.fixture
async def initialized_agent(mock_config_integration, adk_session_service):
    """Fixture to create and initialize a CodeAgent with real session service."""
    # Patch get_config to use our test config
    # Patch get_adk_session_service to return our real InMemory service instance
    with (
        patch("code_agent.agent.agent.get_config", return_value=mock_config_integration),
        patch("code_agent.agent.agent.get_adk_session_service", return_value=adk_session_service),
    ):
        agent = CodeAgent()
        await agent.async_init()  # Initialize with the real session service
        # Store the service instance on the agent object for easier access in tests if needed
        agent._test_session_service = adk_session_service
        return agent


@pytest.fixture
def mock_litellm_acompletion_integration():
    """Fixture to mock litellm.acompletion for integration tests."""
    with patch("code_agent.agent.agent.litellm.acompletion") as mock_acompletion:
        # Default mock response (simple text)
        mock_message = MagicMock()
        mock_message.content = "Default mock LLM response."
        mock_message.tool_calls = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_acompletion.return_value = mock_response
        yield mock_acompletion


# === Test Cases ===


async def test_agent_multi_turn_conversation_history(
    initialized_agent: CodeAgent, mock_litellm_acompletion_integration: AsyncMock, adk_session_service: InMemorySessionService
):
    """
    Test that conversation history is correctly maintained across multiple turns
    using the real InMemorySessionService.
    """
    agent = await initialized_agent
    session_id = agent.session_id

    # --- Turn 1 ---
    prompt1 = "My favorite color is blue."
    # Mock LLM response for turn 1
    mock_message1 = MagicMock(content="Okay, I'll remember that.", tool_calls=None)
    mock_choice1 = MagicMock(message=mock_message1)
    mock_response1 = MagicMock(choices=[mock_choice1])
    mock_litellm_acompletion_integration.return_value = mock_response1

    response1 = await agent.run_turn(prompt1)
    assert response1 == "Okay, I'll remember that."

    # Verify history after turn 1 using the real service
    session_after_turn1 = await adk_session_service.get_session(app_name="code_agent", user_id="default_user", session_id=session_id)
    assert len(session_after_turn1.events) == 2  # User prompt + Assistant response
    assert session_after_turn1.events[0].author == "user"
    assert session_after_turn1.events[0].content.parts[0].text == prompt1
    assert session_after_turn1.events[1].author == "assistant"
    assert session_after_turn1.events[1].content.parts[0].text == "Okay, I'll remember that."

    # --- Turn 2 ---
    prompt2 = "What is my favorite color?"
    # Mock LLM response for turn 2 (should have context)
    mock_message2 = MagicMock(content="Your favorite color is blue.", tool_calls=None)
    mock_choice2 = MagicMock(message=mock_message2)
    mock_response2 = MagicMock(choices=[mock_choice2])
    mock_litellm_acompletion_integration.return_value = mock_response2  # Reset mock for next call

    response2 = await agent.run_turn(prompt2)
    assert "blue" in response2.lower()  # Check if LLM used context

    # Verify history after turn 2
    session_after_turn2 = await adk_session_service.get_session(app_name="code_agent", user_id="default_user", session_id=session_id)
    assert len(session_after_turn2.events) == 4  # User1, Assist1, User2, Assist2
    assert session_after_turn2.events[2].author == "user"
    assert session_after_turn2.events[2].content.parts[0].text == prompt2
    assert session_after_turn2.events[3].author == "assistant"
    assert "blue" in session_after_turn2.events[3].content.parts[0].text.lower()

    # Verify litellm was called with the correct history for turn 2
    # The history passed to litellm should include messages from turn 1
    call_args, call_kwargs = mock_litellm_acompletion_integration.call_args
    messages_for_turn2 = call_kwargs["messages"]
    assert len(messages_for_turn2) == 3  # System (if any) + User1 + Assist1 + User2
    # Find user1 message
    user1_msg = next((m for m in messages_for_turn2 if m["role"] == "user" and m["content"] == prompt1), None)
    assert user1_msg is not None
    # Find assist1 message
    assist1_msg = next((m for m in messages_for_turn2 if m["role"] == "assistant" and m["content"] == "Okay, I'll remember that."), None)
    assert assist1_msg is not None
    # Check last message is user2 prompt
    assert messages_for_turn2[-1]["role"] == "user"
    assert messages_for_turn2[-1]["content"] == prompt2
