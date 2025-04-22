"""
Tests for the CodeAgent class focusing on model string handling.

These tests target low coverage areas in the agent module specifically related to
model string formatting and API base handling.
"""

from unittest.mock import MagicMock, patch

import pytest

from code_agent.agent.agent import CodeAgent
from code_agent.config import ApiKeys, SettingsConfig


@pytest.fixture
def agent_with_config():
    """Create an agent with a configured config for testing."""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = SettingsConfig(
            default_provider="openai",
            default_model="gpt-4",
            api_keys=ApiKeys(
                openai="mock-openai-key",
                anthropic="mock-anthropic-key",
                groq="mock-groq-key",
                ai_studio="mock-ai-studio-key",
            ),
            native_command_allowlist=["ls", "cat", "pwd"],
            rules=["Be helpful", "Write clean code"],
        )
        mock_get_config.return_value = config
        agent = CodeAgent()
        yield agent


def test_get_model_string_openai(agent_with_config):
    """Test model string formatting for OpenAI provider."""
    model_string = agent_with_config._get_model_string("openai", "gpt-4-turbo")
    assert model_string == "gpt-4-turbo"


def test_get_model_string_anthropic(agent_with_config):
    """Test model string formatting for Anthropic provider."""
    model_string = agent_with_config._get_model_string("anthropic", "claude-3-opus")
    assert model_string == "anthropic/claude-3-opus"


def test_get_model_string_ai_studio(agent_with_config):
    """Test model string formatting for AI Studio (Gemini) provider."""
    model_string = agent_with_config._get_model_string("ai_studio", "gemini-pro")
    assert model_string == "gemini-pro"


def test_get_model_string_groq(agent_with_config):
    """Test model string formatting for Groq provider."""
    model_string = agent_with_config._get_model_string("groq", "llama3-8b-8192")
    assert model_string == "groq/llama3-8b-8192"


def test_get_model_string_defaults(agent_with_config):
    """Test model string formatting using default provider and model."""
    model_string = agent_with_config._get_model_string(None, None)
    assert model_string == "gpt-4"  # Default model from config


def test_get_api_base(agent_with_config):
    """Test that _get_api_base returns None for standard providers."""
    api_base = agent_with_config._get_api_base("openai")
    assert api_base is None

    api_base = agent_with_config._get_api_base("anthropic")
    assert api_base is None

    api_base = agent_with_config._get_api_base(None)  # Default provider
    assert api_base is None


@patch("requests.get")
def test_ollama_integration(mock_get, agent_with_config):
    """Test the Ollama integration handling in run_turn."""
    # Mock the OllamaProvider
    with patch("cli_agent.providers.ollama.OllamaProvider") as mock_provider_class:
        mock_provider = MagicMock()
        mock_provider.list_models.return_value = [{"name": "llama3:latest"}]
        mock_provider_class.return_value = mock_provider

        # Mock importlib to simulate requests package available
        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = True

            # Run the agent with Ollama provider
            agent_with_config.run_turn("Test prompt", provider="ollama", model="llama3:latest")

            # This may not actually produce a result as we're not mocking the full flow
            # but it should exercise the Ollama-specific code paths
            mock_provider_class.assert_called_once()
            mock_provider.list_models.assert_called_once()


@patch("rich.prompt.Confirm.ask")
@patch("google.generativeai.list_models")
@patch("google.generativeai.configure")
def test_handle_model_not_found_with_gemini(mock_configure, mock_list_models, mock_confirm, agent_with_config):
    """Test handling model not found errors with Gemini models."""
    # Force the provider to be ai_studio (Gemini)
    agent_with_config.config.default_provider = "ai_studio"

    # Mock the model list response
    mock_model1 = MagicMock()
    mock_model1.name = "models/gemini-1.5-pro"
    mock_model2 = MagicMock()
    mock_model2.name = "models/gemini-1.5-flash"
    mock_list_models.return_value = [mock_model1, mock_model2]

    # Don't actually update config
    mock_confirm.return_value = False

    # Test the method
    result = agent_with_config._handle_model_not_found_error("gemini-pro")

    # Verify that the API was configured and models were listed
    mock_configure.assert_called_once()
    mock_list_models.assert_called_once()

    # Check that the result contains available models
    assert "Available models" in result
    assert "gemini-1.5-pro" in result


@patch("importlib.util.find_spec")
def test_ollama_missing_requests(mock_find_spec, agent_with_config):
    """Test handling when requests package is missing for Ollama."""
    # Simulate requests package not available
    mock_find_spec.return_value = None

    result = agent_with_config.run_turn("Test prompt", provider="ollama")

    # Should return error about missing dependencies
    assert "Error: Ollama provider requires additional dependencies" in result
    assert "requests" in result
