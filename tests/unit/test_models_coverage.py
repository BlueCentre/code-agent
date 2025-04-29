"""
Unit tests for code_agent.adk.models module specifically targeting coverage gaps.
"""

import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from code_agent.adk.models import LiteLlm, OllamaLlm, create_model


# Helper function to run coroutines in non-async unit tests
def pytest_run_awaitable(awaitable):
    """Run a coroutine in a unittest TestCase."""
    return asyncio.run(awaitable)


class TestLiteLlmCoverage(unittest.TestCase):
    """Additional tests for the LiteLlm class to improve coverage."""

    def setUp(self):
        """Set up test environment."""
        # Set required environment variables for testing
        os.environ["OPENAI_API_KEY"] = "test-api-key"
        self.model = LiteLlm(provider="openai", model_name="gpt-3.5-turbo", temperature=0.7)

    def tearDown(self):
        """Clean up test environment."""
        # Remove environment variables after testing
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

    def test_generate_content(self):
        """Test the synchronous generate_content method."""
        with patch("code_agent.adk.models.LiteLlm.generate_content_async") as mock_async:
            mock_response = MagicMock()
            mock_async.return_value = mock_response

            # Call the method
            prompt = "Test prompt"
            response = self.model.generate_content(prompt)

            # Check it passes through to async version
            self.assertEqual(response, mock_response)
            # Make sure it was called with the right arguments
            mock_async.assert_called_once()
            # Extract the call args
            call_args, call_kwargs = mock_async.call_args
            self.assertEqual(call_args[0], prompt)

    @patch("litellm.acompletion")
    def test_error_formatting(self, mock_acompletion):
        """Test error handling and formatting in generate_content_async."""
        # Make the API call raise an error
        api_error = Exception("API rate limit exceeded")
        mock_acompletion.side_effect = api_error

        # Call the method and verify it handles the error
        with self.assertRaises(ValueError) as context:
            pytest_run_awaitable(self.model.generate_content_async("Test prompt"))

        # Check error message contains the provider and model name
        error_message = str(context.exception)
        self.assertIn("openai", error_message.lower())
        self.assertIn("gpt-3.5-turbo", error_message)

    @patch("litellm.acompletion")
    def test_options_passing(self, mock_acompletion):
        """Test that options are correctly passed to the LiteLLM API."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "complete"
        mock_response.usage = MagicMock()
        mock_response.usage.model_dump.return_value = {"prompt_tokens": 10, "completion_tokens": 20}
        mock_acompletion.return_value = mock_response

        # Call with custom options
        custom_options = {
            "temperature": 0.3,  # Override instance temperature
            "top_p": 0.9,  # New parameter
            "stream": False,  # New parameter
        }

        response = pytest_run_awaitable(self.model.generate_content_async("Test prompt", **custom_options))

        # Check options were passed correctly
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 0.3)
        self.assertEqual(call_kwargs["top_p"], 0.9)
        self.assertEqual(call_kwargs["stream"], False)


class TestOllamaLlmCoverage(unittest.TestCase):
    """Additional tests for the OllamaLlm class to improve coverage."""

    def setUp(self):
        """Set up test environment."""
        self.model = OllamaLlm(model_name="llama3.2:latest")

    @patch("litellm.acompletion")
    def test_ollama_content_generation(self, mock_acompletion):
        """Test Ollama content generation with API base URL."""
        # Setup the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Ollama test response"
        mock_response.choices[0].finish_reason = "complete"
        mock_response.usage = MagicMock()
        mock_response.usage.model_dump.return_value = {"prompt_tokens": 5, "completion_tokens": 10}
        mock_acompletion.return_value = mock_response

        # Call with a simple prompt
        response = pytest_run_awaitable(self.model.generate_content_async("Test prompt for Ollama"))

        # Verify the API was called correctly with base_url
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args[1]
        self.assertEqual(call_kwargs["api_base"], "http://localhost:11434")
        self.assertEqual(call_kwargs["model"], "ollama/llama3.2:latest")

        # Verify response content
        self.assertEqual(response.content.parts[0].text, "Ollama test response")


class TestCreateModelCoverage(unittest.TestCase):
    """Additional tests for the create_model function to improve coverage."""

    def setUp(self):
        """Set up test environment."""
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

    def tearDown(self):
        """Clean up test environment."""
        # Remove environment variables after testing
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

    @patch("code_agent.adk.models.get_config")
    @patch("code_agent.adk.models.get_api_key")
    def test_default_provider_from_config(self, mock_get_api_key, mock_get_config):
        """Test creating a model with default provider from config."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.default_provider = "openai"
        mock_config.default_model = "gpt-4"
        mock_config.fallback_provider = "ai_studio"  # Valid provider
        mock_config.fallback_model = "gemini-1.5-flash"  # Valid model
        mock_get_config.return_value = mock_config

        # Mock API key to satisfy the API key check
        mock_get_api_key.return_value = "fake-test-api-key"

        # Create a model without specifying provider
        with patch("code_agent.adk.models.LiteLlm") as mock_lite_llm:
            mock_model = MagicMock()
            mock_lite_llm.return_value = mock_model

            # Not providing provider or model_name
            model = create_model()

            # Should use config defaults
            mock_lite_llm.assert_called_once()
            call_kwargs = mock_lite_llm.call_args[1]
            self.assertEqual(call_kwargs["provider"], "openai")
            self.assertEqual(call_kwargs["model_name"], "gpt-4")

    @patch("code_agent.adk.models.get_config")
    @patch("code_agent.adk.models.get_api_key")
    def test_groq_provider(self, mock_get_api_key, mock_get_config):
        """Test creating a model with Groq provider."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.fallback_provider = "ai_studio"  # Valid provider
        mock_config.fallback_model = "gemini-1.5-flash"  # Valid model
        mock_get_config.return_value = mock_config

        # Mock API key to satisfy the API key check
        mock_get_api_key.side_effect = lambda provider: "fake-groq-key" if provider == "groq" else None

        # Create with Groq provider
        with patch("code_agent.adk.models.LiteLlm") as mock_lite_llm:
            mock_model = MagicMock()
            mock_lite_llm.return_value = mock_model

            # Set up API key
            os.environ["GROQ_API_KEY"] = "test-groq-key"

            try:
                # Create a model with groq provider
                model = create_model(provider="groq", model_name="llama3-70b-8192")

                # Check correct parameters passed to LiteLlm
                mock_lite_llm.assert_called_once()
                call_kwargs = mock_lite_llm.call_args[1]
                self.assertEqual(call_kwargs["provider"], "groq")
                self.assertEqual(call_kwargs["model_name"], "llama3-70b-8192")
                self.assertEqual(call_kwargs["api_base"], "https://api.groq.com/openai/v1")
            finally:
                # Clean up
                if "GROQ_API_KEY" in os.environ:
                    del os.environ["GROQ_API_KEY"]
