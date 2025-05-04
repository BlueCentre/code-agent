"""
Tests for the create_model function in code_agent.adk.models_v2 module.
"""

from unittest.mock import MagicMock, patch

from code_agent.adk.models_v2 import LiteLlm, OllamaLlm, create_model


class TestCreateModel:
    """Test the create_model function."""

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    @patch("google.adk.models.Gemini")
    def test_create_model_gemini(self, mock_gemini_class, mock_get_api_key):
        """Test creating a Gemini model."""
        # Set up the mock
        mock_gemini_instance = MagicMock()
        mock_gemini_class.return_value = mock_gemini_instance

        # Call create_model with ai_studio provider
        result = create_model(provider="ai_studio", model_name="gemini-1.5-flash")

        # Check that the Gemini class was called with expected parameters
        mock_gemini_class.assert_called_once()
        assert result == mock_gemini_instance

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    @patch("code_agent.adk.models_v2.LiteLlm")
    def test_create_model_litellm(self, mock_litellm_class, mock_get_api_key):
        """Test creating various LiteLlm models."""
        # Set up the mock
        mock_litellm_instance = MagicMock(spec=LiteLlm)
        mock_litellm_class.return_value = mock_litellm_instance

        # Test OpenAI
        result = create_model(provider="openai", model_name="gpt-4-turbo")

        # Check that LiteLlm was instantiated
        mock_litellm_class.assert_called_once()
        # Check that provider and model_name were passed (not testing all params to avoid brittle tests)
        kwargs = mock_litellm_class.call_args.kwargs
        assert kwargs["provider"] == "openai"
        assert kwargs["model_name"] == "gpt-4-turbo"
        assert kwargs["api_key"] == "fake-api-key"
        assert result == mock_litellm_instance

    @patch("code_agent.adk.models_v2.OllamaLlm")
    def test_create_model_ollama(self, mock_ollama_class):
        """Test creating an Ollama model."""
        # Set up the mock
        mock_ollama_instance = MagicMock(spec=OllamaLlm)
        mock_ollama_class.return_value = mock_ollama_instance

        # Call create_model with ollama provider
        result = create_model(provider="ollama", model_name="llama3")

        # Verify OllamaLlm was instantiated
        mock_ollama_class.assert_called_once()
        # Only check critical parameters
        kwargs = mock_ollama_class.call_args.kwargs
        assert kwargs["model_name"] == "llama3"
        assert result == mock_ollama_instance

    @patch("code_agent.adk.models_v2.get_api_key", return_value=None)
    @patch("code_agent.adk.models_v2.LiteLlm")
    def test_missing_api_key_with_fallback(self, mock_litellm_class, mock_get_api_key):
        """Test fallback to alternative model when API key is missing."""
        # Create a mock for the fallback model
        mock_fallback_instance = MagicMock(spec=LiteLlm)
        mock_litellm_class.return_value = mock_fallback_instance

        # Call with a fallback configuration
        result = create_model(provider="openai", model_name="gpt-4-turbo", fallback_provider="anthropic", fallback_model="claude-3-opus")

        # Should create the fallback model
        mock_litellm_class.assert_called_once()
        # Check at least one key parameter
        kwargs = mock_litellm_class.call_args.kwargs
        assert kwargs["provider"] == "anthropic"
        assert kwargs["model_name"] == "claude-3-opus"
        assert result == mock_fallback_instance

    @patch("code_agent.adk.models_v2.get_api_key", return_value=None)
    @patch("google.adk.models.Gemini")
    def test_fallback_to_gemini_without_key(self, mock_gemini_class, mock_get_api_key):
        """Test that without API key and no fallback, we get a Gemini model."""
        # Set up the mock
        mock_gemini_instance = MagicMock()
        mock_gemini_class.return_value = mock_gemini_instance

        # Call create_model without fallback
        result = create_model(provider="openai", model_name="gpt-4-turbo")

        # Should create a Gemini model (default fallback behavior)
        mock_gemini_class.assert_called_once()
        assert result == mock_gemini_instance
