"""
Tests for error handling in the agent_model module.
"""

from unittest.mock import MagicMock, mock_open, patch

from code_agent.agent_model import handle_model_not_found_error, is_anthropic_api_key_valid


class TestHandleModelNotFoundError:
    """Tests for the handle_model_not_found_error function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("code_agent.agent_model.importlib.import_module")
    def test_handle_model_not_found_error_with_suggestions(
        self, mock_import_module, mock_yaml_dump, mock_yaml_load, mock_file
    ):
        """Test handling MissingModelError with model suggestions."""
        # Setup
        mock_yaml_load.return_value = {"models": {"primary": "invalid-model"}}

        # Create mock error with suggestions
        error = MagicMock()
        error.suggestions = ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]

        # Run the function
        result = handle_model_not_found_error(error)

        # Check the result
        assert "Model not found" in result
        assert "claude-3-opus-20240229" in result
        assert "claude-3-sonnet-20240229" in result

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("code_agent.agent_model.importlib.import_module")
    def test_handle_model_not_found_error_update_config(
        self, mock_import_module, mock_yaml_dump, mock_yaml_load, mock_file
    ):
        """Test that config is updated with a valid model."""
        # Setup
        mock_yaml_load.return_value = {"models": {"primary": "invalid-model"}}

        # Create mock error with suggestions
        error = MagicMock()
        error.suggestions = ["claude-3-opus-20240229", "claude-3-sonnet-20240229"]

        # Run the function
        handle_model_not_found_error(error)

        # Check that the config was updated with a valid model
        assert mock_yaml_dump.called
        # Get the updated config that was passed to yaml.dump
        updated_config = mock_yaml_dump.call_args[0][0]
        assert updated_config["models"]["primary"] in error.suggestions

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("code_agent.agent_model.importlib.import_module")
    def test_handle_model_not_found_error_without_suggestions(
        self, mock_import_module, mock_yaml_dump, mock_yaml_load, mock_file
    ):
        """Test handling MissingModelError without model suggestions."""
        # Setup
        mock_yaml_load.return_value = {"models": {"primary": "invalid-model"}}

        # Create mock error without suggestions
        error = MagicMock()
        error.suggestions = []

        # Run the function
        result = handle_model_not_found_error(error)

        # Check the result
        assert "Model not found" in result
        assert "No alternative models suggested" in result

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_load")
    @patch("yaml.dump")
    @patch("code_agent.agent_model.importlib.import_module")
    def test_handle_model_not_found_error_config_error(
        self, mock_import_module, mock_yaml_dump, mock_yaml_load, mock_file
    ):
        """Test handling MissingModelError with a config file error."""
        # Setup config load to raise an exception
        mock_yaml_load.side_effect = Exception("Config error")

        # Create mock error
        error = MagicMock()
        error.suggestions = ["claude-3-opus-20240229"]

        # Run the function
        result = handle_model_not_found_error(error)

        # Check the result
        assert "Model not found" in result
        assert "claude-3-opus-20240229" in result
        assert "Error updating config file" in result


class TestIsAnthropicApiKeyValid:
    """Tests for the is_anthropic_api_key_valid function."""

    @patch("code_agent.agent_model.AnthropicClient")
    def test_is_anthropic_api_key_valid_success(self, mock_anthropic_client):
        """Test is_anthropic_api_key_valid with a valid API key."""
        # Setup
        mock_client = MagicMock()
        mock_anthropic_client.return_value = mock_client

        # Run the function
        result = is_anthropic_api_key_valid("sk-valid-key")

        # Check the result
        assert result is True
        mock_anthropic_client.assert_called_once_with(api_key="sk-valid-key")

    @patch("code_agent.agent_model.AnthropicClient")
    def test_is_anthropic_api_key_valid_invalid_key(self, mock_anthropic_client):
        """Test is_anthropic_api_key_valid with an invalid API key."""
        # Setup
        mock_anthropic_client.side_effect = Exception("Invalid API key")

        # Run the function
        result = is_anthropic_api_key_valid("invalid-key")

        # Check the result
        assert result is False

    @patch("code_agent.agent_model.AnthropicClient")
    def test_is_anthropic_api_key_valid_empty_key(self, mock_anthropic_client):
        """Test is_anthropic_api_key_valid with an empty API key."""
        # Run the function
        result = is_anthropic_api_key_valid("")

        # Check the result
        assert result is False
        # Ensure AnthropicClient was not called
        mock_anthropic_client.assert_not_called()
