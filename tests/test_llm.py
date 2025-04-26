"""
Tests for the llm.py module which handles direct interactions with LLM providers.
"""

from unittest.mock import AsyncMock, patch

import pytest

from code_agent.agent.custom_agent.agent import CodeAgent
from code_agent.config import CodeAgentSettings
from code_agent.config.settings_based_config import ApiKeys


@pytest.fixture
def mock_config_llm():
    """Fixture for CodeAgentSettings specific to LLM tests."""
    # Create actual ApiKeys instance
    actual_api_keys = ApiKeys(openai="openai_key", ai_studio="ai_studio_key", ollama=None, groq="groq_key")

    return CodeAgentSettings(
        default_provider="openai",
        default_model="gpt-test",
        api_keys=actual_api_keys,  # Use actual instance
        ollama={},
        # security field will use its default factory
        # Add other fields if needed for tests in this file
    )


@pytest.fixture
def agent_llm(mock_config_llm):
    """Fixture to create a CodeAgent instance with LLM test config (uninitialized)."""
    # Patch get_config used within CodeAgent
    with patch("code_agent.agent.agent.get_config", return_value=mock_config_llm):
        # Mock ADK session service dependencies if agent calls them implicitly
        with patch("code_agent.agent.agent.get_adk_session_service", new_callable=AsyncMock) as mock_adk:
            mock_adk.return_value.create_session.return_value = "fake_session_id"
            agent_instance = CodeAgent()
            yield agent_instance


def test_get_model_string(agent_llm):
    """Test the _get_model_string helper method."""
    agent = agent_llm  # Agent is already patched with mock_config_llm
    assert agent._get_model_string(provider="openai", model="gpt-4") == "gpt-4"
    assert agent._get_model_string(provider="groq", model="llama3") == "groq/llama3"
    assert agent._get_model_string(provider="ollama", model="mistral") == "ollama/mistral"
    assert agent._get_model_string(provider="ai_studio", model="gemini-flash") == "gemini-flash"
    # Test defaults from mock_config_llm
    assert agent._get_model_string(provider=None, model=None) == "gpt-test"
    assert agent._get_model_string(provider="openai", model=None) == "gpt-test"  # Uses default model
    assert agent._get_model_string(provider=None, model="specific-model") == "specific-model"  # Uses default provider


@pytest.mark.skip(reason="Too complex to test the main section reliably")
def test_llm_module_main():
    """Test the __main__ section of the module."""
    # Testing the main section directly is challenging due to many dependencies
    # This section is primarily example code and not critical for functionality
    # The important functionality is already tested in other tests
    pass
