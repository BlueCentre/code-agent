"""
Tests for handling model-related errors in the Agent class.

These tests focus on the model error handling functions in agent.py,
particularly the _handle_model_not_found_error method.
"""

from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from code_agent.agent.agent import CodeAgent
from code_agent.config import ApiKeys, SettingsConfig


@pytest.fixture
def agent_with_mock_config():
    """Create an agent with a mocked config"""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = SettingsConfig(
            default_provider="ai_studio",
            default_model="gemini-1.5-pro",
            api_keys=ApiKeys(ai_studio="mock-ai-studio-key"),
            rules=["Be helpful", "Write clean code"],
        )
        mock_get_config.return_value = config
        agent = CodeAgent()
        yield agent


def test_handle_model_not_found_error_no_api_key(agent_with_mock_config):
    """Test handling model not found error when no API key is available."""
    # Set up the agent with a config that has no API key
    with patch.object(agent_with_mock_config.config.api_keys, "ai_studio", None):
        result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "Could not find API key" in result


def test_handle_model_not_found_error_import_error(agent_with_mock_config):
    """Test handling model not found error when the generativeai module can't be imported."""
    with patch("code_agent.agent.agent.importlib") as mock_importlib:
        # Simulate ImportError when trying to import google.generativeai
        mock_importlib.import_module.side_effect = ImportError("No module named 'google.generativeai'")

        result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "Cannot list available models" in result


def test_handle_model_not_found_error_with_suggestions(agent_with_mock_config):
    """Test handling model not found error with suggested models."""
    # Create mock genai module
    mock_genai = MagicMock()
    mock_model1 = MagicMock()
    mock_model1.name = "models/gemini-1.5-flash"
    mock_model2 = MagicMock()
    mock_model2.name = "models/gemini-1.5-pro"

    # Set up list_models to return our mock models
    mock_genai.list_models.return_value = [mock_model1, mock_model2]

    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        with patch("code_agent.agent.agent.importlib") as mock_importlib:
            # Return our mock module when importing google.generativeai
            mock_importlib.import_module.return_value = mock_genai

            # Patch Confirm.ask to return False (don't update config)
            with patch("code_agent.agent.agent.Confirm.ask", return_value=False):
                result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "Available models" in result
    assert "gemini-1.5-pro" in result


def test_handle_model_not_found_error_update_config(agent_with_mock_config):
    """Test handling model not found error with config update."""
    # Create mock genai module
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_model.name = "models/gemini-1.5-flash"

    # Set up list_models to return our mock model
    mock_genai.list_models.return_value = [mock_model]

    # Mock Path.home() to return a temporary directory
    mock_home = MagicMock()
    mock_config_dir = MagicMock()
    mock_config_path = MagicMock()
    mock_home.return_value = mock_config_dir
    mock_config_dir.__truediv__.return_value = mock_config_dir
    mock_config_dir.__truediv__.return_value = mock_config_path
    mock_config_path.exists.return_value = True

    # Create a sample config file content
    config_content = {
        "default_provider": "ai_studio",
        "default_model": "gemini-1.5-pro",
        "api_keys": {"ai_studio": "mock-key"},
    }

    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        with patch("code_agent.agent.agent.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_genai

            with patch("code_agent.agent.agent.Path.home", mock_home):
                with patch("builtins.open", mock_open(read_data=yaml.dump(config_content))):
                    with patch("code_agent.agent.agent.Confirm.ask", return_value=True):
                        # Mock IntPrompt.ask to return 1 (select first model)
                        with patch("code_agent.agent.agent.IntPrompt.ask", return_value=1):
                            result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "Configuration updated" in result
    assert "gemini-1.5-flash" in result


def test_handle_model_not_found_error_no_similar_models(agent_with_mock_config):
    """Test handling model not found error when no similar models are found."""
    # Create mock genai module
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_model.name = "models/completely-different-model"

    # Set up list_models to return models with no similarity
    mock_genai.list_models.return_value = [mock_model]

    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        with patch("code_agent.agent.agent.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_genai

            result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "No similar models found" in result or "Could not find similar models" in result


def test_handle_model_not_found_error_with_exception(agent_with_mock_config):
    """Test handling model not found error when an exception occurs."""
    # Create mock genai module that raises an exception
    mock_genai = MagicMock()
    mock_genai.list_models.side_effect = Exception("API error")

    with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
        with patch("code_agent.agent.agent.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = mock_genai

            result = agent_with_mock_config._handle_model_not_found_error("gemini-1.5-pro")

    assert "Error checking for available models" in result
