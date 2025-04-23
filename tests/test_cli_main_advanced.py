"""
Tests for the main CLI module focusing on more advanced and edge case behaviors.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app
from code_agent.config import ApiKeys, SettingsConfig


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock config for CLI tests."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="mock-openai-key",
            anthropic="mock-anthropic-key",
            groq="mock-groq-key",
            ai_studio="mock-ai-studio-key",
        ),
        auto_approve_edits=False,
        auto_approve_native_commands=False,
        native_command_allowlist=["ls", "cat", "pwd"],
        rules=["Be helpful", "Write clean code"],
    )
    return config


@pytest.fixture
def temp_history_dir():
    """Create a temporary directory for chat history."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock history file
        history_dir = Path(temp_dir) / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        # Create a test history file
        history_file = history_dir / "chat_20230101_120000.json"
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        with open(history_file, "w") as f:
            json.dump(history, f)

        # Patch the HISTORY_DIR to use our temp directory
        with patch("code_agent.cli.main.HISTORY_DIR", history_dir):
            yield history_dir


# --- Config Command Tests ---


def test_config_show_command(runner, mock_config):
    """Test the 'config show' command."""
    with patch("code_agent.cli.main.get_config", return_value=mock_config):
        result = runner.invoke(app, ["config", "show"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that config values are displayed in the JSON output
    assert "default_provider" in result.stdout
    assert "openai" in result.stdout
    assert "default_model" in result.stdout
    assert "gpt-4" in result.stdout
    assert "api_keys" in result.stdout
    assert "mock-openai-key" in result.stdout


# Configuration command tests for different providers
def test_config_openai_command(runner):
    """Test the 'config openai' command."""
    result = runner.invoke(app, ["config", "openai"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that the command displays the expected information
    assert "OpenAI Configuration" in result.stdout
    assert "Setup Instructions" in result.stdout
    assert "Available Models" in result.stdout
    assert "gpt-4o" in result.stdout
    assert "Usage Examples" in result.stdout


def test_config_anthropic_command(runner):
    """Test the 'config anthropic' command."""
    result = runner.invoke(app, ["config", "anthropic"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that the command displays the expected information
    assert "Anthropic Configuration" in result.stdout
    assert "Setup Instructions" in result.stdout
    assert "Available Models" in result.stdout
    assert "claude-3-5-sonnet" in result.stdout
    assert "Usage Examples" in result.stdout


def test_config_groq_command(runner):
    """Test the 'config groq' command."""
    result = runner.invoke(app, ["config", "groq"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that the command displays the expected information
    assert "Groq Configuration" in result.stdout
    assert "Setup Instructions" in result.stdout
    assert "Available Models" in result.stdout
    assert "llama3-70b-8192" in result.stdout
    assert "Usage Examples" in result.stdout


def test_config_aistudio_command(runner):
    """Test the 'config aistudio' command."""
    result = runner.invoke(app, ["config", "aistudio"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that the command displays the expected information
    assert "Google AI Studio Configuration" in result.stdout
    assert "Setup Instructions" in result.stdout
    assert "Available Models" in result.stdout
    assert "gemini-1.5-pro" in result.stdout
    assert "Usage Examples" in result.stdout


# Test reset config command simulating "yes" input
def test_config_reset_command(runner):
    """Test the 'config reset' command with confirmation."""
    # Skip user input and directly check output messages
    result = runner.invoke(app, ["config", "reset"], input="y\n")

    # Check command executed successfully
    assert result.exit_code == 0
    # Check the success message - it should contain these substrings
    assert "Configuration reset to defaults" in result.stdout
    assert "Edit this file to add your API keys" in result.stdout


# --- Provider Command Tests ---


def test_providers_list_command(runner, mock_config):
    """Test the 'providers list' command."""
    with patch("code_agent.cli.main.get_config", return_value=mock_config):
        result = runner.invoke(app, ["providers", "list"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that provider information is displayed
    assert "Available Providers" in result.stdout
    assert "openai" in result.stdout
    assert "anthropic" in result.stdout
    assert "groq" in result.stdout
    assert "ai_studio" in result.stdout


# --- Chat History Tests ---


def test_load_history(temp_history_dir):
    """Test loading chat history."""
    from code_agent.cli.main import load_latest_history

    # Load the history
    history = load_latest_history()

    # Check that history was loaded correctly
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"


def test_save_history(temp_history_dir):
    """Test saving chat history."""
    from code_agent.cli.main import save_history

    # New history to save
    history = [
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm fine, thanks!"},
    ]

    # Save the history
    save_history("20230102_120000", history)

    # Check that the file was created
    history_file = temp_history_dir / "chat_20230102_120000.json"
    assert history_file.exists()

    # Check that the content is correct
    with open(history_file, "r") as f:
        saved_history = json.load(f)

    assert len(saved_history) == 2
    assert saved_history[0]["role"] == "user"
    assert saved_history[0]["content"] == "How are you?"


def test_chat_with_empty_history(runner, mock_config):
    """Test chat command with no existing history."""
    # Create a temporary directory for history
    with tempfile.TemporaryDirectory() as temp_dir:
        history_dir = Path(temp_dir) / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        # Setup mocks
        mock_agent = MagicMock()
        mock_agent.run_turn.return_value = "This is a test response"

        with (
            patch("code_agent.cli.main.HISTORY_DIR", history_dir),
            patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
            patch("code_agent.cli.main.get_config", return_value=mock_config),
        ):
            # Run chat command with one message and then exit
            result = runner.invoke(app, ["chat"], input="Hello\nexit\n")

        # Check command executed successfully
        assert result.exit_code == 0
        assert "Starting new chat session" in result.stdout
        # Fix the assertion to use assert_called_once_with
        assert mock_agent.run_turn.called
        mock_agent.run_turn.assert_called_with(prompt="Hello")


# --- Error Handling Tests ---


def test_chat_invalid_history_file(runner, mock_config):
    """Test handling of invalid history file format."""
    # Create a temporary directory with an invalid history file
    with tempfile.TemporaryDirectory() as temp_dir:
        history_dir = Path(temp_dir) / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        # Create an invalid history file (not a list)
        history_file = history_dir / "chat_20230101_120000.json"
        with open(history_file, "w") as f:
            f.write('{"not": "a valid history format"}')

        # Setup mocks
        mock_agent = MagicMock()
        mock_agent.run_turn.return_value = "This is a test response"

        with (
            patch("code_agent.cli.main.HISTORY_DIR", history_dir),
            patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
            patch("code_agent.cli.main.get_config", return_value=mock_config),
        ):
            # Run chat command
            result = runner.invoke(app, ["chat"], input="Hello\nexit\n")

        # Check command handled the invalid file gracefully
        assert result.exit_code == 0
        assert "Invalid format in history file" in result.stdout


def test_chat_special_commands(runner, mock_config):
    """Test chat special commands like /help and /clear."""
    # Setup mocks
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "This is a test response"

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
    ):
        # Test the /help command followed by exit
        result = runner.invoke(app, ["chat"], input="/help\nexit\n")

    # Check command executed successfully and showed help
    assert result.exit_code == 0
    assert "Available commands:" in result.stdout
    assert "/help" in result.stdout
    assert "/clear" in result.stdout

    # Test the /clear command
    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
    ):
        # Test the /clear command followed by exit
        result = runner.invoke(app, ["chat"], input="/clear\nexit\n")

    # Check command executed successfully and cleared history
    assert result.exit_code == 0
    assert "History cleared" in result.stdout


# --- CLI Options Tests ---


def test_auto_approve_edits_option(runner, mock_config):
    """Test the --auto-approve-edits option."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "This is a test response"

    with (
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        # No need to mock internal functions - the entire functionality is being
        # tested through the CLI interface
    ):
        # Run command with auto-approve-edits option
        result = runner.invoke(app, ["--auto-approve-edits", "run", "test prompt"])

    # Check the command executed successfully
    assert result.exit_code == 0
    # Verify agent was called with the right prompt
    mock_agent.run_turn.assert_called_once_with(prompt="test prompt", quiet=None)


def test_auto_approve_native_commands_option(runner, mock_config):
    """Test the --auto-approve-native-commands option."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "This is a test response"

    with (
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        # No need to mock internal functions - the entire functionality is being
        # tested through the CLI interface
    ):
        # Run command with auto-approve-native-commands option
        cmd = ["--auto-approve-native-commands", "run", "test prompt"]
        result = runner.invoke(app, cmd)

    # Check the command executed successfully
    assert result.exit_code == 0
    # Verify agent was called with the right prompt
    mock_agent.run_turn.assert_called_once_with(prompt="test prompt", quiet=None)


def test_provider_and_model_override(runner, mock_config):
    """Test overriding provider and model via CLI arguments."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "This is a test response"

    with (
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        # We can check that the provider and model are passed to the command
    ):
        # Run command with provider and model options
        cmd = ["--provider", "anthropic", "--model", "claude-3-opus", "run", "test prompt"]
        result = runner.invoke(app, cmd)

    # Check the command executed successfully
    assert result.exit_code == 0
    # Verify agent was called with the right prompt
    mock_agent.run_turn.assert_called_once_with(prompt="test prompt", quiet=None)


# --- No API Key Tests ---


def test_run_command_with_no_api_key(runner):
    """Test running a command when no API key is configured."""
    # Create a config with no API keys
    empty_config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(),  # No API keys
    )

    # Mock the agent to return a specific error message
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = None  # Simulate API key error

    with (
        patch("code_agent.cli.main.get_config", return_value=empty_config),
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.print"),  # Suppress output
    ):
        # Run command
        result = runner.invoke(app, ["run", "test prompt"])

    # Check that the command handled the missing API key gracefully
    assert result.exit_code == 0
    # Check that the agent was called but no response was processed
    mock_agent.run_turn.assert_called_once_with(prompt="test prompt", quiet=None)
