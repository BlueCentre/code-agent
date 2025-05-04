"""
Simplified tests for code_agent.adk.models_v2 module.
"""

from unittest.mock import MagicMock

from google.adk.models import LlmRequest
from google.genai import types

from code_agent.adk.models_v2 import LiteLlm, ModelConfig, OllamaLlm


class TestLiteLlmSimple:
    """Test the LiteLlm class basic functionality."""

    def test_litellm_initialization(self):
        """Test initialization of LiteLlm with various parameters."""
        # Test with default parameters
        model = LiteLlm()
        assert model.provider == "openai"
        assert model.model_name == "gpt-3.5-turbo"
        assert model.temperature == 0.7
        assert model.max_tokens is None
        assert model.retry_count == 2

        # Test with custom parameters
        model = LiteLlm(provider="anthropic", model_name="claude-3-opus", api_key="test-key", temperature=0.2, max_tokens=1000, timeout=60, retry_count=3)
        assert model.provider == "anthropic"
        assert model.model_name == "claude-3-opus"
        assert model.api_key == "test-key"
        assert model.temperature == 0.2
        assert model.max_tokens == 1000
        assert model.timeout == 60
        assert model.retry_count == 3
        assert model.litellm_model == "anthropic/claude-3-opus"

    def test_generate_prompt_string(self):
        """Test _generate_prompt with a string input."""
        model = LiteLlm()
        prompt = "Hello, how are you?"
        messages = model._generate_prompt(prompt)

        assert isinstance(messages, list)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, how are you?"

    def test_generate_prompt_messages(self):
        """Test _generate_prompt with a list of messages."""
        model = LiteLlm()
        messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Tell me a joke."}]
        result = model._generate_prompt(messages)

        assert result == messages

    def test_generate_prompt_llm_request(self):
        """Test _generate_prompt with an LlmRequest."""
        model = LiteLlm()

        # Create a mock LlmRequest
        content1 = types.Content(role="system", parts=[types.Part(text="You are a helpful assistant.")])
        content2 = types.Content(role="user", parts=[types.Part(text="Tell me a joke.")])
        request = LlmRequest(contents=[content1, content2])

        result = model._generate_prompt(request)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Tell me a joke."

    def test_extract_content(self):
        """Test _extract_content to extract text from LLM response."""
        model = LiteLlm()

        # Create a mock response object with the expected structure
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is the extracted content"

        result = model._extract_content(mock_response)

        assert result == "This is the extracted content"


class TestOllamaLlmSimple:
    """Test the OllamaLlm class basic functionality."""

    def test_ollama_initialization(self):
        """Test initialization of OllamaLlm with various parameters."""
        # Test with default parameters
        model = OllamaLlm()
        assert model.provider == "ollama"
        assert model.model_name == "llama3.2:latest"
        assert model.base_url == "http://localhost:11434"
        assert model.temperature == 0.7
        assert model.max_tokens is None
        assert model.retry_count == 1

        # Test with custom parameters
        model = OllamaLlm(model_name="mistral", base_url="http://example.com:11434", temperature=0.3, max_tokens=500, timeout=30, retry_count=2)
        assert model.provider == "ollama"
        assert model.model_name == "mistral"
        assert model.base_url == "http://example.com:11434"
        assert model.temperature == 0.3
        assert model.max_tokens == 500
        assert model.timeout == 30
        assert model.retry_count == 2
        assert model.litellm_model == "ollama/mistral"


class TestModelConfigSimple:
    """Test the ModelConfig class functionality."""

    def test_model_config_initialization(self):
        """Test initialization of ModelConfig with various parameters."""
        # Test with required parameters only
        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7  # default value
        assert config.max_tokens is None  # default value
        assert config.timeout is None  # default value
        assert config.retry_count == 2  # default value
        assert config.fallback_provider is None  # default value
        assert config.fallback_model is None  # default value

        # Test with all parameters
        config = ModelConfig(
            provider="anthropic",
            model_name="claude-3-opus",
            temperature=0.2,
            max_tokens=1000,
            timeout=60,
            retry_count=3,
            fallback_provider="openai",
            fallback_model="gpt-4",
        )
        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-opus"
        assert config.temperature == 0.2
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.retry_count == 3
        assert config.fallback_provider == "openai"
        assert config.fallback_model == "gpt-4"

    def test_model_config_field_types(self):
        """Test that ModelConfig fields have the correct types."""
        config = ModelConfig(provider="openai", model_name="gpt-4")

        # Check types of fields
        assert isinstance(config.provider, str)
        assert isinstance(config.model_name, str)
        assert isinstance(config.temperature, float)
        assert config.max_tokens is None or isinstance(config.max_tokens, int)
        assert config.timeout is None or isinstance(config.timeout, int)
        assert isinstance(config.retry_count, int)

        # Test with different temperature values
        config = ModelConfig(provider="openai", model_name="gpt-4", temperature=0.0)
        assert config.temperature == 0.0

        config = ModelConfig(provider="openai", model_name="gpt-4", temperature=1.0)
        assert config.temperature == 1.0


class TestModelUtilitiesSimple:
    """Test the model utility functions in the models_v2 module."""

    def test_get_model_providers(self):
        """Test the get_model_providers function returns expected providers."""
        from code_agent.adk.models_v2 import get_model_providers

        providers = get_model_providers()

        assert isinstance(providers, list)
        assert len(providers) > 0

        # Check for expected providers
        expected_providers = ["ai_studio", "openai", "anthropic", "groq", "ollama"]
        for provider in expected_providers:
            assert provider in providers

    def test_get_default_models_by_provider(self):
        """Test the get_default_models_by_provider function returns expected models."""
        from code_agent.adk.models_v2 import get_default_models_by_provider

        models = get_default_models_by_provider()

        assert isinstance(models, dict)
        assert len(models) > 0

        # Check for expected providers and model patterns
        assert "ai_studio" in models
        assert "gemini" in models["ai_studio"].lower()

        assert "openai" in models
        assert "gpt" in models["openai"].lower()

        assert "anthropic" in models
        assert "claude" in models["anthropic"].lower()

        assert "ollama" in models
        assert "llama" in models["ollama"].lower()
