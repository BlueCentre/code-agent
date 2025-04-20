"""
Tests for API key error handling scenarios.

These tests ensure the agent properly handles errors related to API keys,
such as invalid keys, missing keys, and improper key configuration.
"""

import os
import pytest
import json
from unittest.mock import patch, MagicMock

import litellm
from litellm.exceptions import AuthenticationError, InvalidRequestError, ServiceUnavailableError

from code_agent.agent.agent import CodeAgent
from code_agent.agent.run import run_agent_turn
from code_agent.config import SettingsConfig, ApiKeys

# --- Fixtures ---

@pytest.fixture
def mock_config_with_invalid_key():
    """Mock config with an invalid API key."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="sk-invalid-key-12345",
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
def mock_invalid_key_error():
    """Create a mock litellm authentication error for invalid API key."""
    # Create a basic exception with the required parameters
    error = AuthenticationError(
        message="Incorrect API key provided. You can find your API key at https://platform.openai.com/account/api-keys.",
        llm_provider="openai",
        model="gpt-4"
    )
    return error


@pytest.fixture
def mock_rate_limit_error():
    """Create a mock litellm rate limit error."""
    # Create a basic exception with the required parameters
    error = InvalidRequestError(
        message="Rate limit exceeded. Please try again later.",
        model="gpt-4",
        llm_provider="openai"
    )
    return error


@pytest.fixture
def mock_service_unavailable_error():
    """Create a mock litellm service unavailable error."""
    # Create a basic exception with the required parameters
    error = ServiceUnavailableError(
        message="The server is overloaded or not ready yet.",
        llm_provider="openai",
        model="gpt-4"
    )
    return error


# --- Tests ---

def test_agent_handles_invalid_api_key(mock_config_with_invalid_key, mock_invalid_key_error, mocker):
    """Test that the agent gracefully handles an invalid API key error."""
    # Patch the get_config function to return our mock config with invalid key
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_invalid_key
        
        # Patch litellm.completion to raise an authentication error
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = mock_invalid_key_error
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("Hello")
        
        # Verify that the result is None (indicating error handling occurred)
        assert result is None
        
        # Verify the error was correctly passed to litellm
        mock_completion.assert_called_once()
        args, kwargs = mock_completion.call_args
        assert kwargs["api_key"] == "sk-invalid-key-12345"


def test_agent_handles_rate_limit_error(mock_config_with_invalid_key, mock_rate_limit_error, mocker):
    """Test that the agent gracefully handles a rate limit error."""
    # Patch the get_config function
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_invalid_key
        
        # Patch litellm.completion to raise a rate limit error
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = mock_rate_limit_error
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("Hello")
        
        # Verify that the result is None (indicating error handling occurred)
        assert result is None


def test_agent_handles_service_unavailable(mock_config_with_invalid_key, mock_service_unavailable_error, mocker):
    """Test that the agent gracefully handles a service unavailable error."""
    # Patch the get_config function
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config_with_invalid_key
        
        # Patch litellm.completion to raise a service unavailable error
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = mock_service_unavailable_error
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("Hello")
        
        # Verify that the result is None (indicating error handling occurred)
        assert result is None


def test_empty_api_key_fallback_behavior(mocker):
    """Test that the agent falls back to simple command handling when API key is empty."""
    # Create a config with an empty API key
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            # No openai key provided
        ),
        rules=["Be helpful"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    
    # Patch get_config and run_native_command
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = config
        mock_run_cmd = mocker.patch("code_agent.agent.agent.run_native_command")
        mock_run_cmd.return_value = "/home/user/project"
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("What is the current directory?")
        
        # Verify that the agent used fallback and didn't attempt an API call
        assert "current working directory" in result
        mock_run_cmd.assert_called_once_with("pwd")


def test_api_base_error_handling(mock_config_with_invalid_key, mocker):
    """Test that the agent correctly handles errors when using custom API base URLs."""
    # Modify the config to use AI Studio provider which needs custom API base
    config = mock_config_with_invalid_key
    config.default_provider = "ai_studio"
    
    # Create a connection error to simulate API base issues
    connection_error = Exception("Failed to connect to the API endpoint")
    
    # Patch get_config and litellm.completion
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = config
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = connection_error
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("Hello")
        
        # Verify that the result is None (indicating error handling occurred)
        assert result is None
        
        # Verify the API base URL was correctly set in the completion parameters
        mock_completion.assert_called_once()
        args, kwargs = mock_completion.call_args
        assert kwargs["api_base"] == "https://api.ai.studio/v1"


def test_api_key_from_env_vars(mocker):
    """Test that the agent can use API keys from environment variables."""
    # Create a config with no API keys set
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(),  # Empty API keys
        rules=["Be helpful"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    
    # Patch the agent's api_key property directly
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = config
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        
        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = None
        mock_completion.return_value = mock_response
        
        # Override the agent's config.api_keys.openai access
        with patch.object(config.api_keys, "model_dump") as mock_model_dump:
            mock_model_dump.return_value = {"openai": "sk-env-var-key-12345"}
            
            # Create agent and run a turn
            agent = CodeAgent()
            result = agent.run_turn("Test")
            
            # Check that the completion was called and result is correct
            assert result == "Test response"
            mock_completion.assert_called_once()
            args, kwargs = mock_completion.call_args
            assert kwargs["api_key"] == "sk-env-var-key-12345" 