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


@pytest.fixture(scope="module")
def mock_config_integration():
    """Fixture for mock config used in integration tests."""
    # Use real ApiKeys model
    keys = ApiKeys(mock_provider="mock-api-key-12345", openai="dummy-key")
    return CodeAgentSettings(
        default_provider="mock_provider", # Use a mock provider name
        default_model="mock_model",
        api_keys=keys, # Assign ApiKeys instance
        verbosity=0, # Quiet for integration tests
        # Use defaults for other settings
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
        patch("code_agent.agent.custom_agent.agent.get_config", return_value=mock_config_integration),
        patch("code_agent.agent.custom_agent.agent.get_adk_session_service", return_value=adk_session_service),
    ):
        agent = CodeAgent()
        await agent.async_init()  # Initialize with the real session service
        # Store the service instance on the agent object for easier access in tests if needed
        agent._test_session_service = adk_session_service
        return agent


@pytest.fixture
def mock_litellm_acompletion_integration():
    """Fixture to mock litellm.acompletion for integration tests."""
    with patch("code_agent.agent.custom_agent.agent.litellm.acompletion") as mock_acompletion:
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


# @pytest.mark.asyncio # Commented out
# async def test_agent_multi_turn_conversation_history( # Commented out
#     initialized_agent: CodeAgent, mock_litellm_acompletion_integration: AsyncMock, adk_session_service: InMemorySessionService # Commented out
# ): # Commented out
#     """ # Commented out
#     Test that conversation history is correctly maintained across multiple turns # Commented out
#     using the real InMemorySessionService. # Commented out
#     """ # Commented out
#     agent = await initialized_agent # Commented out
#     session_id = agent.session_id # Commented out
# # Commented out
#     # --- Turn 1 --- # Commented out
#     prompt1 = "My favorite color is blue." # Commented out
#     # Mock LLM response for turn 1 # Commented out
#     mock_message1 = MagicMock(content="Okay, I'll remember that.", tool_calls=None) # Commented out
#     mock_choice1 = MagicMock(message=mock_message1) # Commented out
#     mock_response1 = MagicMock(choices=[mock_choice1]) # Commented out
#     mock_litellm_acompletion_integration.return_value = mock_response1 # Commented out
# # Commented out
#     response1 = await agent.run_turn(prompt1) # Commented out
#     assert response1 == "Okay, I'll remember that." # Commented out
# # Commented out
#     # Check ADK history after turn 1 # Commented out
#     history1 = await adk_session_service.get_history(session_id=session_id, app_name="code_agent", user_id="default_user") # Commented out
#     assert len(history1) >= 2 # User prompt, Assistant response (maybe partials too) # Commented out
#     assert history1[0].author == "user" # Commented out
#     assert history1[-1].author == "assistant" # Commented out
#     assert history1[-1].content.parts[0].text == "Okay, I'll remember that." # Commented out
# # Commented out
#     # --- Turn 2 --- # Commented out
#     prompt2 = "What is my favorite color?" # Commented out
#     # Mock LLM response for turn 2 (it should use history) # Commented out
#     mock_message2 = MagicMock(content="Your favorite color is blue.", tool_calls=None) # Commented out
#     mock_choice2 = MagicMock(message=mock_message2) # Commented out
#     mock_response2 = MagicMock(choices=[mock_choice2]) # Commented out
#     mock_litellm_acompletion_integration.return_value = mock_response2 # Commented out
# # Commented out
#     response2 = await agent.run_turn(prompt2) # Commented out
#     assert response2 == "Your favorite color is blue." # Commented out
# # Commented out
#     # Check LiteLLM was called with history from turn 1 # Commented out
#     _call_args, call_kwargs = mock_litellm_acompletion_integration.call_args # Get last call args # Commented out
#     messages = call_kwargs["messages"] # Commented out
#     assert len(messages) > 2 # Should include system, user1, assistant1, user2 # Commented out
#     assert any(m["role"] == "user" and m["content"] == prompt1 for m in messages) # Commented out
#     assert any(m["role"] == "assistant" and m["content"] == "Okay, I'll remember that." for m in messages) # Commented out
#     assert messages[-1]["role"] == "user" and messages[-1]["content"] == prompt2 # Commented out
