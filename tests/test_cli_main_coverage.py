"""
Tests to improve coverage for the CLI main module.

These tests focus on specific functionality in code_agent/cli/main.py
that isn't fully covered by existing tests.
"""

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


# Test the CLI callbacks
def test_main_callback_with_provider_model_override(runner):
    """Test that the main callback correctly handles provider and model overrides."""
    with patch("code_agent.cli.main.initialize_config") as mock_init:
        # Call the CLI with provider and model overrides
        runner.invoke(app, ["--provider", "anthropic", "--model", "claude-3", "run", "test prompt"])
        
        # Check that initialize_config was called with the right parameters
        mock_init.assert_called_once()
        args, kwargs = mock_init.call_args
        assert kwargs["cli_provider"] == "anthropic"
        assert kwargs["cli_model"] == "claude-3"
        assert kwargs["cli_auto_approve_edits"] is None
        assert kwargs["cli_auto_approve_native_commands"] is None


def test_main_callback_with_auto_approve_flags(runner):
    """Test that the main callback correctly handles auto-approve flags."""
    with patch("code_agent.cli.main.initialize_config") as mock_init:
        # Call the CLI with auto-approve flags
        runner.invoke(app, ["--auto-approve-edits", "--auto-approve-native-commands", "run", "test prompt"])
        
        # Check that initialize_config was called with the right parameters
        mock_init.assert_called_once()
        args, kwargs = mock_init.call_args
        assert kwargs["cli_provider"] is None
        assert kwargs["cli_model"] is None
        assert kwargs["cli_auto_approve_edits"] is True
        assert kwargs["cli_auto_approve_native_commands"] is True


# Test chat command with special commands
def test_chat_with_special_help_command(runner, mock_config):
    """Test chat command with /help special command."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "Test response"

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.save_history"),
    ):
        # Send /help command then exit
        result = runner.invoke(app, ["chat"], input="/help\nexit\n")

        # Verify help text is shown
        assert "Available commands:" in result.stdout
        assert "/help" in result.stdout
        assert "/clear" in result.stdout
        assert "/exit" in result.stdout

        # Ensure run_turn wasn't called for a special command
        mock_agent.run_turn.assert_not_called()


def test_chat_with_special_clear_command(runner, mock_config):
    """Test chat command with /clear special command."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "Test response"
    mock_agent.history = [{"role": "user", "content": "Previous message"}]

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.save_history"),
    ):
        # Send /clear command, then a prompt, then exit
        result = runner.invoke(app, ["chat"], input="/clear\nHello\nexit\n")

        # Verify clear message is shown
        assert "History cleared" in result.stdout

        # Verify run_turn was called after clearing
        mock_agent.run_turn.assert_called_once_with(prompt="Hello")

        # Verify history was cleared
        assert mock_agent.history == [] or len(mock_agent.history) == 2  # Either cleared or contains the new message pair


def test_chat_with_unknown_special_command(runner, mock_config):
    """Test chat command with unknown special command."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "Test response"

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.save_history"),
    ):
        # Send unknown command then exit
        result = runner.invoke(app, ["chat"], input="/unknown\nexit\n")

        # Verify error message is shown
        assert "Unknown command: /unknown" in result.stdout
        assert "Type /help for available commands" in result.stdout

        # Ensure run_turn wasn't called for an unknown command
        mock_agent.run_turn.assert_not_called()


# Test empty inputs and direct exit commands
def test_chat_with_empty_input(runner, mock_config):
    """Test chat command with empty input."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "Test response"

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.save_history"),
    ):
        # Send empty input then exit
        result = runner.invoke(app, ["chat"], input="\nexit\n")

        # Verify warning is shown
        assert "Please enter a non-empty message" in result.stdout

        # Ensure run_turn wasn't called for empty input
        mock_agent.run_turn.assert_not_called()


def test_chat_direct_exit_commands(runner, mock_config):
    """Test chat command with direct exit commands (without slash)."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = "Test response"

    with (
        patch("code_agent.cli.main.CodeAgent", return_value=mock_agent),
        patch("code_agent.cli.main.get_config", return_value=mock_config),
        patch("code_agent.cli.main.save_history"),
    ):
        # Test "exit" command
        result = runner.invoke(app, ["chat"], input="exit\n")
        assert "Exiting chat session" in result.stdout

        # Test "quit" command
        result = runner.invoke(app, ["chat"], input="quit\n")
        assert "Exiting chat session" in result.stdout


# Test config commands
def test_config_validate_command_valid(runner, mock_config):
    """Test the config validate command with valid configuration."""
    with patch("code_agent.cli.main.get_config", return_value=mock_config), patch("code_agent.config.config.validate_config", return_value=True):
        # Run with verbose flag
        result = runner.invoke(app, ["config", "validate", "--verbose"])

        # Check command executed successfully (no exit code 1)
        assert result.exit_code == 0


def test_config_validate_command_invalid(runner, mock_config):
    """Test the config validate command with invalid configuration."""
    with patch("code_agent.cli.main.get_config", return_value=mock_config), patch("code_agent.config.config.validate_config", return_value=False):
        # The command should exit with code 1 when validation fails
        result = runner.invoke(app, ["config", "validate"])

        # Check that the command exited with code 1 (validation failed)
        assert result.exit_code == 1


def test_config_ollama_command(runner):
    """Test the 'config ollama' command."""
    result = runner.invoke(app, ["config", "ollama"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that the command displays the expected information
    assert "Ollama Configuration" in result.stdout
    assert "Setup Instructions" in result.stdout
    assert "Usage Examples" in result.stdout
    assert "http://localhost:11434" in result.stdout


# Test run command with failing agent
def test_run_command_with_failing_agent(runner, mock_config):
    """Test run command when agent.run_turn returns None."""
    mock_agent = MagicMock()
    mock_agent.run_turn.return_value = None  # Simulate failure

    with patch("code_agent.cli.main.CodeAgent", return_value=mock_agent), patch("code_agent.cli.main.get_config", return_value=mock_config):
        result = runner.invoke(app, ["run", "test prompt"])

        # Check that the error message is displayed
        assert "Failed to get response" in result.stdout

        # Verify agent was called
        mock_agent.run_turn.assert_called_once_with(prompt="test prompt")


# Test history saving with errors
def test_save_history_with_error(runner):
    """Test saving history when an exception occurs."""
    from code_agent.cli.main import save_history

    # Create a history to save
    history = [{"role": "user", "content": "Test"}]

    with patch("builtins.open", side_effect=PermissionError("Permission denied")), patch("code_agent.cli.main.print") as mock_print:
        # Try to save history
        save_history("test_session", history)

        # Check that error message was passed to print
        mock_print.assert_any_call("[red]Error saving chat history:[/red] Permission denied")


# Test test mode
def test_chat_test_mode(runner, mock_config):
    """Test chat command with test mode."""
    mock_agent = MagicMock()

    with patch("code_agent.cli.main.CodeAgent", return_value=mock_agent), patch("code_agent.cli.main.get_config", return_value=mock_config):
        # Send test mode command
        result = runner.invoke(app, ["chat"], input="/test\n")

        # Verify test success message is shown
        assert "TEST_SUCCESS" in result.stdout

        # Ensure agent wasn't called for test mode
        mock_agent.run_turn.assert_not_called()
