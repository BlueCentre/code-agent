"""
Tests for the model factory functions in code_agent.adk.models_v2 module.
"""

from unittest.mock import patch

import pytest
from google.adk.models import Gemini

from code_agent.adk.models_v2 import (
    LiteLlm,
    ModelConfig,
    OllamaLlm,
    create_model,
    get_default_models_by_provider,
    get_model_providers,
)


class TestModelFactory:
    """Test the model factory functions in the models_v2 module."""

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_gemini(self, mock_get_api_key):
        """Test creating a Gemini model."""
        model = create_model(provider="ai_studio", model_name="gemini-1.5-flash")
        assert isinstance(model, Gemini)
        assert model.model == "gemini-1.5-flash"
        assert model.api_key == "fake-api-key"

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_openai(self, mock_get_api_key):
        """Test creating an OpenAI model."""
        model = create_model(provider="openai", model_name="gpt-4-turbo")
        assert isinstance(model, LiteLlm)
        assert model.provider == "openai"
        assert model.model_name == "gpt-4-turbo"
        assert model.api_key == "fake-api-key"
        assert model.litellm_model == "openai/gpt-4-turbo"

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_anthropic(self, mock_get_api_key):
        """Test creating an Anthropic model."""
        model = create_model(provider="anthropic", model_name="claude-3-opus")
        assert isinstance(model, LiteLlm)
        assert model.provider == "anthropic"
        assert model.model_name == "claude-3-opus"
        assert model.api_key == "fake-api-key"
        assert model.litellm_model == "anthropic/claude-3-opus"

    def test_create_model_ollama(self):
        """Test creating an Ollama model."""
        model = create_model(provider="ollama", model_name="llama3.2")
        assert isinstance(model, OllamaLlm)
        assert model.provider == "ollama"
        assert model.model_name == "llama3.2"
        assert model.base_url == "http://localhost:11434"
        assert model.litellm_model == "ollama/llama3.2"

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_with_temperature(self, mock_get_api_key):
        """Test creating a model with a custom temperature."""
        model = create_model(provider="openai", model_name="gpt-4", temperature=0.2)
        assert isinstance(model, LiteLlm)
        assert model.temperature == 0.2

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_with_max_tokens(self, mock_get_api_key):
        """Test creating a model with custom max_tokens."""
        model = create_model(provider="openai", model_name="gpt-4", max_tokens=1000)
        assert isinstance(model, LiteLlm)
        assert model.max_tokens == 1000

    @patch("code_agent.adk.models_v2.get_api_key", return_value=None)
    def test_create_model_missing_api_key(self, mock_get_api_key):
        """Test error when API key is missing for providers that need it."""
        with pytest.raises(ValueError, match="No API key found for provider"):
            create_model(provider="openai", model_name="gpt-4")

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_unknown_provider(self, mock_get_api_key):
        """Test creating a model with an unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_model(provider="unknown", model_name="model")

    @patch("code_agent.adk.models_v2.get_api_key", return_value="fake-api-key")
    def test_create_model_with_fallback(self, mock_get_api_key):
        """Test model creation with fallback configuration."""
        model = create_model(provider="openai", model_name="gpt-4", fallback_provider="anthropic", fallback_model="claude-3-sonnet")
        # Verify the fallback configuration is stored somewhere
        # The exact implementation depends on how fallback is handled
        assert hasattr(model, "_fallback_config")
        assert model._fallback_config.provider == "anthropic"
        assert model._fallback_config.model_name == "claude-3-sonnet"

    def test_get_model_providers(self):
        """Test the get_model_providers function returns a non-empty list."""
        providers = get_model_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert "openai" in providers
        assert "ai_studio" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_get_default_models_by_provider(self):
        """Test the get_default_models_by_provider function returns a non-empty dict."""
        default_models = get_default_models_by_provider()
        assert isinstance(default_models, dict)
        assert len(default_models) > 0
        assert "openai" in default_models
        assert "ai_studio" in default_models
        assert "anthropic" in default_models
        assert "ollama" in default_models


class TestModelConfig:
    """Test the ModelConfig class."""

    def test_model_config_creation(self):
        """Test creating a ModelConfig instance."""
        config = ModelConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
            retry_count=3,
            fallback_provider="anthropic",
            fallback_model="claude-3-opus",
        )
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.retry_count == 3
        assert config.fallback_provider == "anthropic"
        assert config.fallback_model == "claude-3-opus"

    def test_model_config_defaults(self):
        """Test ModelConfig default values."""
        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.temperature == 0.7  # Default value
        assert config.max_tokens is None  # Default value
        assert config.timeout is None  # Default value
        assert config.retry_count == 2  # Default value
        assert config.fallback_provider is None  # Default value
        assert config.fallback_model is None  # Default value
