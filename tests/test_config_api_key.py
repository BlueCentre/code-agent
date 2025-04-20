"""
Tests for how API keys from configuration are used by the agent.

These tests ensure the agent correctly retrieves and uses API keys
from the configuration system.
"""

import pytest
from unittest.mock import patch, MagicMock

from code_agent.agent.agent import CodeAgent
from code_agent.config import SettingsConfig
from code_agent.config.config import ApiKeys

# --- Fixtures ---

@pytest.fixture
def mock_config_with_keys():
    """Mock config with various API keys set."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="test-openai-key",
            ai_studio="test-ai-studio-key",
            anthropic="test-anthropic-key",
            groq="test-groq-key"
        ),
        rules=["Be helpful"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    return config


@pytest.fixture
def mock_config_missing_key():
    """Mock config with missing API key for default provider."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            ai_studio="test-ai-studio-key",
            anthropic="test-anthropic-key",
            groq="test-groq-key"
        ),
        rules=["Be helpful"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    return config


# --- Tests ---

def test_agent_uses_correct_api_key_from_config(mock_config_with_keys, mocker):
    """Test that the agent retrieves the correct API key for the default provider."""
    # Patch the get_config function to return our mock
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_keys
        
        # Patch litellm.completion to avoid actual API calls
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Create agent and run a simple turn
        agent = CodeAgent()
        agent.run_turn("Test prompt")
        
        # Check that litellm.completion was called with the correct API key
        # for the default provider (openai)
        args, kwargs = mock_completion.call_args
        assert kwargs["api_key"] == "test-openai-key"


def test_agent_uses_override_provider_api_key(mock_config_with_keys, mocker):
    """Test that the agent uses the correct API key when provider is overridden."""
    # Patch the get_config function to return our mock
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_keys
        
        # Patch litellm.completion to avoid actual API calls
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Create agent and run a turn with override provider
        agent = CodeAgent()
        agent.run_turn("Test prompt", provider="anthropic")
        
        # Check that litellm.completion was called with the correct API key
        # for the overridden provider (anthropic)
        args, kwargs = mock_completion.call_args
        assert kwargs["api_key"] == "test-anthropic-key"


def test_agent_falls_back_when_api_key_missing(mock_config_missing_key, mocker):
    """Test that the agent falls back to simple handling when API key is missing."""
    # Patch the get_config function to return our mock
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_missing_key
        
        # Patch native command execution for the fallback case
        mock_run_cmd = mocker.patch("code_agent.agent.agent.run_native_command")
        mock_run_cmd.return_value = "/home/user/project"
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("What is the current directory?")
        
        # Verify that the result uses the fallback path and the native command was called
        assert "current working directory" in result
        mock_run_cmd.assert_called_once_with("pwd")


def test_agent_builds_correct_model_string(mock_config_with_keys, mocker):
    """Test that the agent correctly formats model strings for different providers."""
    # Patch get_config and litellm.completion
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_keys
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Test with default provider (openai)
        agent = CodeAgent()
        agent.run_turn("Test")
        args1, kwargs1 = mock_completion.call_args
        assert kwargs1["model"] == "gpt-4"
        
        # Reset mock and test with ai_studio provider
        mock_completion.reset_mock()
        agent.run_turn("Test", provider="ai_studio", model="gemini-pro")
        args2, kwargs2 = mock_completion.call_args
        assert kwargs2["model"] == "vertex_ai/gemini-pro"
        
        # Reset mock and test with another provider
        mock_completion.reset_mock()
        agent.run_turn("Test", provider="anthropic", model="claude-3-opus")
        args3, kwargs3 = mock_completion.call_args
        assert kwargs3["model"] == "anthropic/claude-3-opus"


def test_custom_api_base_for_ai_studio(mock_config_with_keys, mocker):
    """Test that the agent sets the correct API base URL for AI Studio provider."""
    # Patch get_config and litellm.completion
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_keys
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Test with ai_studio provider which should have a custom API base
        agent = CodeAgent()
        agent.run_turn("Test", provider="ai_studio")
        
        # Verify api_base was set in the completion parameters
        args, kwargs = mock_completion.call_args
        assert "api_base" in kwargs
        assert kwargs["api_base"] == "https://api.ai.studio/v1"
        
        # Reset mock and test with a provider that doesn't need custom base
        mock_completion.reset_mock()
        agent.run_turn("Test", provider="openai")
        args, kwargs = mock_completion.call_args
        assert "api_base" not in kwargs 