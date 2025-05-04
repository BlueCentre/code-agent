"""
Tests for the code_agent.adk.models_v2 module.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types

from code_agent.adk.models_v2 import (
    LiteLlm,
    ModelConfig,
    OllamaLlm,
    create_model,
    get_default_models_by_provider,
    get_model_providers,
)


class TestLiteLlm:
    """Tests for the LiteLlm class."""

    def test_init_default_params(self):
        """Test that LiteLlm initializes with default parameters."""
        llm = LiteLlm()

        assert llm.provider == "openai"
        assert llm.model_name == "gpt-3.5-turbo"
        assert llm.model == "openai/gpt-3.5-turbo"
        assert llm.litellm_model == "openai/gpt-3.5-turbo"
        assert llm.temperature == 0.7
        assert llm.retry_count == 2

    def test_init_custom_params(self):
        """Test that LiteLlm initializes with custom parameters."""
        llm = LiteLlm(provider="anthropic", model_name="claude-3", temperature=0.5, max_tokens=1000, timeout=60, retry_count=3, api_key="test-key")

        assert llm.provider == "anthropic"
        assert llm.model_name == "claude-3"
        assert llm.model == "anthropic/claude-3"
        assert llm.litellm_model == "anthropic/claude-3"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 1000
        assert llm.timeout == 60
        assert llm.retry_count == 3
        assert llm.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_generate_content_async_string_prompt(self):
        """Test generating content with a string prompt."""
        with patch("litellm.acompletion") as mock_acompletion:
            # Mock the litellm response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test response"), finish_reason="stop")]
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"total_tokens": 100}

            mock_acompletion.return_value = mock_response

            llm = LiteLlm(provider="openai", model_name="gpt-4")
            response = await llm.generate_content_async("What is the capital of France?")

            # Check litellm was called correctly
            mock_acompletion.assert_called_once()
            call_args = mock_acompletion.call_args[1]
            assert call_args["model"] == "openai/gpt-4"
            assert call_args["messages"] == [{"role": "user", "content": "What is the capital of France?"}]

            # Check response structure
            assert isinstance(response, LlmResponse)
            assert response.content.parts[0].text == "Test response"

    @pytest.mark.asyncio
    async def test_generate_content_async_message_list(self):
        """Test generating content with a list of messages."""
        with patch("litellm.acompletion") as mock_acompletion:
            # Mock the litellm response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="I'll help with Python"), finish_reason="stop")]
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"total_tokens": 120}

            mock_acompletion.return_value = mock_response

            messages = [{"role": "system", "content": "You are a Python expert."}, {"role": "user", "content": "Help me with list comprehensions."}]

            llm = LiteLlm(provider="openai", model_name="gpt-4")
            response = await llm.generate_content_async(messages)

            # Check litellm was called correctly
            mock_acompletion.assert_called_once()
            call_args = mock_acompletion.call_args[1]
            assert call_args["model"] == "openai/gpt-4"
            assert call_args["messages"] == messages

            # Check response structure
            assert isinstance(response, LlmResponse)
            assert response.content.parts[0].text == "I'll help with Python"

    @pytest.mark.asyncio
    async def test_generate_content_async_llm_request(self):
        """Test generating content with an LlmRequest object."""
        with patch("litellm.acompletion") as mock_acompletion:
            # Mock the litellm response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="LLM request response"), finish_reason="stop")]
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"total_tokens": 80}

            mock_acompletion.return_value = mock_response

            # Create a basic LlmRequest with system and user messages
            system_content = types.Content(role="system", parts=[types.Part(text="You are a helpful assistant.")])
            user_content = types.Content(role="user", parts=[types.Part(text="Tell me about yourself.")])
            llm_request = LlmRequest(contents=[system_content, user_content])

            llm = LiteLlm(provider="openai", model_name="gpt-4")
            response = await llm.generate_content_async(llm_request)

            # Check litellm was called correctly
            mock_acompletion.assert_called_once()
            call_args = mock_acompletion.call_args[1]
            assert call_args["model"] == "openai/gpt-4"
            assert len(call_args["messages"]) == 2
            assert call_args["messages"][0]["role"] == "system"
            assert call_args["messages"][0]["content"] == "You are a helpful assistant."
            assert call_args["messages"][1]["role"] == "user"
            assert call_args["messages"][1]["content"] == "Tell me about yourself."

            # Check response structure
            assert isinstance(response, LlmResponse)
            assert response.content.parts[0].text == "LLM request response"

    @pytest.mark.asyncio
    async def test_generate_content_async_retry_logic(self):
        """Test the retry logic when API calls fail."""
        with patch("litellm.acompletion") as mock_acompletion:
            # First call fails, second succeeds
            mock_acompletion.side_effect = [
                Exception("API rate limit exceeded"),
                MagicMock(
                    choices=[MagicMock(message=MagicMock(content="Retry succeeded"), finish_reason="stop")],
                    usage=MagicMock(model_dump=lambda: {"total_tokens": 50}),
                ),
            ]

            llm = LiteLlm(provider="openai", model_name="gpt-4", retry_count=1)
            response = await llm.generate_content_async("Test retry")

            # Check litellm was called twice
            assert mock_acompletion.call_count == 2

            # Check response structure
            assert isinstance(response, LlmResponse)
            assert response.content.parts[0].text == "Retry succeeded"

    @pytest.mark.asyncio
    async def test_generate_content_async_max_retries_exceeded(self):
        """Test that an error is raised when max retries are exceeded."""
        with patch("litellm.acompletion") as mock_acompletion:
            # All calls fail
            mock_acompletion.side_effect = Exception("API rate limit exceeded")

            llm = LiteLlm(provider="openai", model_name="gpt-4", retry_count=2)

            with pytest.raises(ValueError, match="LiteLLM error"):
                await llm.generate_content_async("Test retry exhaustion")

            # Check litellm was called the expected number of times (1 + retry_count)
            assert mock_acompletion.call_count == 3


class TestOllamaLlm:
    """Tests for the OllamaLlm class."""

    def test_init_default_params(self):
        """Test that OllamaLlm initializes with default parameters."""
        llm = OllamaLlm()

        assert llm.provider == "ollama"
        assert llm.model_name == "llama3.2:latest"
        assert llm.model == "ollama/llama3.2:latest"
        assert llm.litellm_model == "ollama/llama3.2:latest"
        assert llm.base_url == "http://localhost:11434"
        assert llm.temperature == 0.7
        assert llm.retry_count == 1

    def test_init_custom_params(self):
        """Test that OllamaLlm initializes with custom parameters."""
        llm = OllamaLlm(model_name="mistral:latest", base_url="http://192.168.1.100:11434", temperature=0.5, max_tokens=2000, timeout=120, retry_count=2)

        assert llm.provider == "ollama"
        assert llm.model_name == "mistral:latest"
        assert llm.model == "ollama/mistral:latest"
        assert llm.litellm_model == "ollama/mistral:latest"
        assert llm.base_url == "http://192.168.1.100:11434"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 2000
        assert llm.timeout == 120
        assert llm.retry_count == 2

    @pytest.mark.asyncio
    async def test_generate_content_async(self):
        """Test generating content with OllamaLlm."""
        # Patch the LiteLlm.generate_content_async method
        with patch("code_agent.adk.models_v2.LiteLlm.generate_content_async") as mock_parent_method:
            mock_response = MagicMock(spec=LlmResponse)
            mock_response.content = types.Content(parts=[types.Part(text="Ollama response")])
            mock_parent_method.return_value = mock_response

            ollama = OllamaLlm(model_name="llama3.2:latest")
            response_gen = ollama.generate_content_async("Tell me about Ollama")

            # OllamaLlm.generate_content_async returns an async generator
            response = await response_gen.__anext__()

            # Check parent method was called correctly
            mock_parent_method.assert_called_once()
            call_args = mock_parent_method.call_args
            assert call_args[0][0] == "Tell me about Ollama"
            assert call_args[1]["api_base"] == "http://localhost:11434"

            # Check response
            assert response.content.parts[0].text == "Ollama response"

            # Check it's a proper generator (exhausted after one item)
            with pytest.raises(StopAsyncIteration):
                await response_gen.__anext__()


class TestModelConfig:
    """Tests for the ModelConfig class."""

    def test_model_config_defaults(self):
        """Test default values of ModelConfig."""
        config = ModelConfig(provider="openai", model_name="gpt-4")

        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.timeout is None
        assert config.retry_count == 2
        assert config.fallback_provider is None
        assert config.fallback_model is None

    def test_model_config_custom(self):
        """Test custom values of ModelConfig."""
        config = ModelConfig(
            provider="anthropic",
            model_name="claude-3-sonnet",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
            retry_count=3,
            fallback_provider="openai",
            fallback_model="gpt-4",
        )

        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-sonnet"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.retry_count == 3
        assert config.fallback_provider == "openai"
        assert config.fallback_model == "gpt-4"


class TestCreateModel:
    """Tests for the create_model function."""

    @patch("code_agent.adk.models_v2.get_model_providers")
    @patch("code_agent.adk.models_v2.get_api_key")
    @patch("code_agent.adk.models_v2.get_config")
    def test_create_model_default_from_config(self, mock_get_config, mock_get_api_key, mock_get_providers):
        """Test create_model using default values from config."""
        # Configure the mock config with ai_studio as provider
        mock_config = MagicMock()
        mock_config.default_provider = "ai_studio"
        mock_config.default_model = "gemini-2.0-flash"
        mock_config.temperature = 0.7  # Set temperature directly on the mock_config
        mock_get_config.return_value = mock_config

        # Provider list that confirms our target provider is valid
        mock_get_providers.return_value = ["openai", "ai_studio", "anthropic", "ollama", "groq"]

        # Always return a valid API key for whatever provider
        mock_get_api_key.return_value = "test-api-key"

        # Call create_model - expect a string for ai_studio provider
        model = create_model()

        # For ai_studio, it should return the model name as a string
        assert model == "gemini-2.0-flash"
        mock_get_api_key.assert_any_call("ai_studio")

    @patch("code_agent.adk.models_v2.get_api_key")
    @patch("code_agent.adk.models_v2.get_config")
    def test_create_model_explicit_params(self, mock_get_config, mock_get_api_key):
        """Test create_model with explicitly provided parameters."""
        # Configure the mock config
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Configure get_api_key to return a key for anthropic
        mock_get_api_key.return_value = "test-api-key"

        # Create Anthropic model
        with patch("code_agent.adk.models_v2.LiteLlm") as mock_litellm_class:
            mock_model = MagicMock(spec=BaseLlm)
            mock_litellm_class.return_value = mock_model

            model = create_model(provider="anthropic", model_name="claude-3", temperature=0.5, max_tokens=1000, timeout=60, retry_count=3)

            assert model == mock_model
            mock_litellm_class.assert_called_once()
            mock_get_api_key.assert_called_with("anthropic")

    @patch("code_agent.adk.models_v2.get_config")
    def test_create_model_ollama(self, mock_get_config):
        """Test create_model for Ollama provider."""
        mock_config = MagicMock()
        mock_config.ollama = {"url": "http://localhost:11434"}
        mock_get_config.return_value = mock_config

        # Create Ollama model
        with patch("code_agent.adk.models_v2.OllamaLlm") as mock_ollama_class:
            mock_model = MagicMock(spec=BaseLlm)
            mock_ollama_class.return_value = mock_model

            model = create_model(provider="ollama", model_name="llama3.2:latest", temperature=0.8)

            assert model == mock_model
            mock_ollama_class.assert_called_once()

    def test_get_model_providers(self):
        """Test the get_model_providers function."""
        providers = get_model_providers()

        # Check it returns a list of strings
        assert isinstance(providers, list)
        assert all(isinstance(provider, str) for provider in providers)

        # Check for some expected providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
        assert "ai_studio" in providers

    def test_get_default_models_by_provider(self):
        """Test the get_default_models_by_provider function."""
        default_models = get_default_models_by_provider()

        # Check it returns a dict mapping provider to model name
        assert isinstance(default_models, dict)
        assert all(isinstance(provider, str) and isinstance(model, str) for provider, model in default_models.items())

        # Check for some expected providers and their default models
        assert "openai" in default_models
        assert "anthropic" in default_models
        assert "ai_studio" in default_models
        assert "ollama" in default_models
