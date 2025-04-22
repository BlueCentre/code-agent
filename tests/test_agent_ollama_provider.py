"""
Tests for the Ollama provider integration with the CodeAgent.

This file focuses on testing the integration between CodeAgent and OllamaProvider,
ensuring the connection handling, error handling, and configuration are properly covered.
"""

from unittest.mock import MagicMock, patch

import pytest

from code_agent.agent.agent import CodeAgent
from code_agent.config import ApiKeys, SettingsConfig


@pytest.fixture
def agent_with_ollama_config():
    """Create an agent with Ollama configuration."""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        # Create a mock ollama config object with URL attribute
        mock_ollama_config = MagicMock()
        mock_ollama_config.url = "http://custom-ollama:11434"

        config = SettingsConfig(
            default_provider="ollama",
            default_model="llama3:latest",
            api_keys=ApiKeys(),  # Ollama doesn't need API keys
            native_command_allowlist=["ls", "cat", "pwd"],
            rules=["Be helpful", "Write clean code"],
        )
        # Add the ollama config to the main config
        config.ollama = mock_ollama_config

        mock_get_config.return_value = config
        agent = CodeAgent()
        yield agent


@patch("requests.get")
@patch("cli_agent.providers.ollama.OllamaProvider")
@patch("importlib.util.find_spec")
def test_agent_ollama_custom_url(mock_find_spec, mock_provider_class, mock_get, agent_with_ollama_config):
    """Test that the agent uses the custom Ollama URL from config."""
    # Simulate requests package available
    mock_find_spec.return_value = True

    # Setup mock provider
    mock_provider = MagicMock()
    mock_provider.list_models.return_value = [{"name": "llama3:latest"}]
    mock_provider_class.return_value = mock_provider

    # Run the agent with Ollama
    agent_with_ollama_config.run_turn("Test prompt")

    # Check that the provider was created with the custom URL
    mock_provider_class.assert_called_once_with("http://custom-ollama:11434")

    # Verify the model listing was called
    mock_provider.list_models.assert_called_once()


@patch("requests.get")
@patch("cli_agent.providers.ollama.OllamaProvider")
@patch("importlib.util.find_spec")
def test_agent_ollama_connection_error(mock_find_spec, mock_provider_class, mock_get, agent_with_ollama_config):
    """Test handling of Ollama connection errors."""
    # Simulate requests package available
    mock_find_spec.return_value = True

    # Setup mock provider to raise connection error
    mock_provider = MagicMock()
    mock_provider.list_models.side_effect = Exception("Connection refused")
    mock_provider_class.return_value = mock_provider

    # Run the agent with Ollama
    result = agent_with_ollama_config.run_turn("Test prompt")

    # Check that the error was handled
    assert result is not None
    assert "Could not connect to Ollama" in result or "Error" in result


@patch("requests.get")
@patch("importlib.util.find_spec")
def test_agent_ollama_without_config(mock_find_spec, mock_get):
    """Test agent behavior with Ollama provider when no specific Ollama config exists."""
    # Create a basic agent without Ollama-specific config
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = SettingsConfig(
            default_provider="ollama",
            default_model="llama3:latest",
            api_keys=ApiKeys(),
        )
        # No ollama config attribute

        mock_get_config.return_value = config
        agent = CodeAgent()

        # Simulate requests package available
        mock_find_spec.return_value = True

        # Mock the OllamaProvider
        with patch("cli_agent.providers.ollama.OllamaProvider") as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.list_models.return_value = [{"name": "llama3:latest"}]
            mock_provider_class.return_value = mock_provider

            # Run the agent with Ollama
            agent.run_turn("Test prompt")

            # Check that the provider was created with the default URL
            mock_provider_class.assert_called_once_with("http://localhost:11434")


@patch("requests.get")
@patch("importlib.util.find_spec")
def test_ollama_connection_failure(mock_find_spec, mock_get, agent_with_ollama_config):
    """Test handling when Ollama connection fails."""
    # Simulate requests package available
    mock_find_spec.return_value = True

    # Mock the requests.get to simulate a connection failure
    mock_get.side_effect = Exception("Connection refused")

    # We need to patch specific print functions to avoid errors in test output
    with patch("rich.print"):
        # Run the agent with Ollama provider
        result = agent_with_ollama_config.run_turn("Test prompt")

        # Check that the error was handled
        assert result is not None
        assert "Error" in result or "Could not connect" in result
