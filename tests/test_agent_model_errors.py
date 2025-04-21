"""
Tests for error handling in agent model interactions.
"""

from unittest.mock import MagicMock, patch

from code_agent.agent.agent import CodeAgent


class TestModelErrorHandling:
    """Tests for model error handling in the agent."""

    def test_handle_model_not_found_error(self, capsys):
        """Test handling model not found errors."""
        # Create a mock config with settings
        with patch("code_agent.agent.agent.get_config") as mock_get_config:
            config = MagicMock()
            config.default_provider = "openai"
            config.default_model = "invalid-model"
            config.api_keys = MagicMock()
            config.api_keys.openai = "test-key"
            mock_get_config.return_value = config

            # Create a mock for error formatting
            with patch("code_agent.agent.agent.format_api_error") as mock_format_error:
                # Make it return a specific error message
                mock_format_error.return_value = "Error: Model 'invalid-model' not found."

                # Create a mock for litellm that raises an exception
                with patch("code_agent.agent.agent.litellm.completion") as mock_litellm:
                    mock_litellm.side_effect = Exception("Model 'invalid-model' not found")

                    # Also mock _handle_model_not_found_error to return a deterministic value
                    with patch.object(
                        CodeAgent, "_handle_model_not_found_error", return_value="Cannot list available models. Try installing google-generativeai package."
                    ):
                        # Create agent and run
                        agent = CodeAgent()
                        agent.run_turn("Hello")

                        # Capture the output that was printed
                        captured = capsys.readouterr()

                        # The actual error formatting should be captured in the output
                        assert "Model 'invalid-model' not found" in captured.out

    def test_handle_api_key_error(self, capsys):
        """Test handling invalid API key errors."""
        # Create a mock config with settings
        with patch("code_agent.agent.agent.get_config") as mock_get_config:
            config = MagicMock()
            config.default_provider = "openai"
            config.default_model = "gpt-4"
            config.api_keys = MagicMock()
            config.api_keys.openai = "invalid-key"
            mock_get_config.return_value = config

            # Create a mock for error formatting
            with patch("code_agent.agent.agent.format_api_error") as mock_format_error:
                # Make it return a specific error message
                error_message = "Error: Authentication error: Invalid API key"
                mock_format_error.return_value = error_message

                # Create a mock for litellm that raises an exception
                with patch("code_agent.agent.agent.litellm.completion") as mock_litellm:
                    mock_litellm.side_effect = Exception("Authentication error: Invalid API key")

                    # Create agent and run
                    agent = CodeAgent()

                    # For this kind of error, no special handlers are called so result will be None
                    # But the formatted error should be printed
                    agent.run_turn("Hello")

                    # Capture the output that was printed
                    captured = capsys.readouterr()

                    # The actual error formatting should be captured in the output
                    assert "Authentication error" in captured.out
                    assert "API key" in captured.out

    def test_handle_rate_limit_error(self, capsys):
        """Test handling rate limit errors."""
        # Create a mock config with settings
        with patch("code_agent.agent.agent.get_config") as mock_get_config:
            config = MagicMock()
            config.default_provider = "openai"
            config.default_model = "gpt-4"
            config.api_keys = MagicMock()
            config.api_keys.openai = "test-key"
            mock_get_config.return_value = config

            # Create a mock for error formatting
            with patch("code_agent.agent.agent.format_api_error") as mock_format_error:
                # Make it return a specific error message
                error_message = "Error: Rate limit exceeded. Please try again later."
                mock_format_error.return_value = error_message

                # Create a mock for litellm that raises an exception
                with patch("code_agent.agent.agent.litellm.completion") as mock_litellm:
                    mock_litellm.side_effect = Exception("Rate limit exceeded")

                    # Create agent and run
                    agent = CodeAgent()

                    # For this kind of error, no special handlers are called so result will be None
                    # But the formatted error should be printed
                    agent.run_turn("Hello")

                    # Capture the output that was printed
                    captured = capsys.readouterr()

                    # The actual error formatting should be captured in the output
                    assert "Rate limit exceeded" in captured.out
