"""
Tests for the provider commands in code_agent.cli.main module.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestProviderList:
    """Tests for the 'provider list' command."""

    @patch("code_agent.cli.commands.provider.get_api_key")
    @patch("code_agent.cli.commands.provider.get_config")
    def test_provider_list_all_configured(self, mock_get_config, mock_get_api_key, runner):
        """Test 'provider list' when all cloud providers have keys."""
        # Arrange
        mock_config = MagicMock()
        mock_config.llm.provider = "openai"  # Example default
        mock_config.llm.model = "gpt-4o"
        mock_config.ollama = None  # Use default Ollama URL
        mock_get_config.return_value = mock_config

        # Simulate all keys found
        mock_get_api_key.side_effect = lambda provider_id: f"fake-key-for-{provider_id}"

        # Act
        result = runner.invoke(app, ["providers", "list"])

        # Assert
        assert result.exit_code == 0
        assert "Configured LLM Providers:" in result.stdout
        assert "Current Default Provider: openai" in result.stdout
        assert "Current Default Model:    gpt-4o" in result.stdout
        assert "Google AI Studio: ✓ Configured (API Key Found)" in result.stdout
        assert "OpenAI: ✓ Configured (API Key Found) (DEFAULT)" in result.stdout  # Check default marker
        assert "Groq: ✓ Configured (API Key Found)" in result.stdout
        assert "Anthropic: ✓ Configured (API Key Found)" in result.stdout
        assert "Ollama (Local): ✓ Available (Local)" in result.stdout
        assert "Warning: No cloud providers seem to have configured API keys." not in result.stdout  # Should not appear
        assert "Quick Tips:" in result.stdout
        # Check get_api_key was called for cloud providers
        mock_get_api_key.assert_any_call("ai_studio")
        mock_get_api_key.assert_any_call("openai")
        mock_get_api_key.assert_any_call("groq")
        mock_get_api_key.assert_any_call("anthropic")
        # Should not be called for ollama
        with pytest.raises(AssertionError):  # Check it wasn't called for ollama
            mock_get_api_key.assert_any_call("ollama")

    @patch("code_agent.cli.commands.provider.get_api_key")
    @patch("code_agent.cli.commands.provider.get_config")
    def test_provider_list_none_configured_ollama_default(self, mock_get_config, mock_get_api_key, runner):
        """Test 'provider list' when no cloud keys found and Ollama is default."""
        # Arrange
        mock_config = MagicMock()
        mock_config.llm.provider = "ollama"  # Ollama default
        mock_config.llm.model = "llama3"
        mock_config.ollama.url = "http://custom-ollama:11434"  # Custom Ollama URL
        mock_get_config.return_value = mock_config

        # Simulate no keys found
        mock_get_api_key.return_value = None

        # Act
        result = runner.invoke(app, ["providers", "list"])

        # Assert
        assert result.exit_code == 0
        assert "Current Default Provider: ollama" in result.stdout
        assert "Current Default Model:    llama3" in result.stdout
        # Check for core parts, avoiding exact markup
        assert "Google AI Studio:" in result.stdout
        assert "Not configured" in result.stdout
        assert "AI_STUDIO_API_KEY" in result.stdout
        assert "OpenAI:" in result.stdout
        assert "Not configured" in result.stdout
        assert "OPENAI_API_KEY" in result.stdout
        assert "Groq:" in result.stdout
        assert "Not configured" in result.stdout
        assert "GROQ_API_KEY" in result.stdout
        assert "Anthropic:" in result.stdout
        assert "Not configured" in result.stdout
        assert "ANTHROPIC_API_KEY" in result.stdout
        assert "Ollama (Local):" in result.stdout
        assert "Available (Local)" in result.stdout
        assert "(URL: http://custom-ollama:11434)" in result.stdout
        assert "(DEFAULT)" in result.stdout
        # Should not appear if ollama is default
        assert "Warning: No cloud providers seem to have configured API keys." not in result.stdout
        assert "Quick Tips:" in result.stdout

    @patch("code_agent.cli.commands.provider.get_api_key")
    @patch("code_agent.cli.commands.provider.get_config")
    def test_provider_list_none_configured_cloud_default(self, mock_get_config, mock_get_api_key, runner):
        """Test 'provider list' when no cloud keys found and a cloud provider is default."""
        # Arrange
        mock_config = MagicMock()
        mock_config.llm.provider = "anthropic"  # Cloud default, but key missing
        mock_config.llm.model = "claude-3-haiku"
        mock_config.ollama = None  # Default Ollama URL
        mock_get_config.return_value = mock_config

        # Simulate no keys found
        mock_get_api_key.return_value = None

        # Act
        result = runner.invoke(app, ["providers", "list"])

        # Assert
        assert result.exit_code == 0
        assert "Current Default Provider: anthropic" in result.stdout
        assert "Current Default Model:    claude-3-haiku" in result.stdout
        # Check for core parts, avoiding exact markup
        assert "Google AI Studio:" in result.stdout and "Not configured" in result.stdout
        assert "OpenAI:" in result.stdout and "Not configured" in result.stdout
        assert "Groq:" in result.stdout and "Not configured" in result.stdout
        # Default provider should still be marked, even if not configured
        assert "Anthropic:" in result.stdout and "Not configured" in result.stdout and "ANTHROPIC_API_KEY" in result.stdout and "(DEFAULT)" in result.stdout
        assert "Ollama (Local):" in result.stdout and "Available (Local)" in result.stdout
        assert "Warning: No cloud providers seem to have configured API keys." in result.stdout  # Should appear now
        assert "Quick Tips:" in result.stdout


# Add more tests if needed, e.g., for specific edge cases or formatting details
