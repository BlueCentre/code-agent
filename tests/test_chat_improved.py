from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app
from code_agent.config import ApiKeys, SettingsConfig


class MockAgent:
    """Mock Agent class for testing that simulates the real CodeAgent behavior"""

    def __init__(self):
        self.history = []
        # Predefined responses for specific prompts
        self.responses = {
            "hello": "Hello! I'm the mock agent.",
            "help": "I can assist with coding tasks, run commands, and edit files.",
            "version": "I'm running version mock-1.0.",
            "empty": "",
        }
        self.call_count = 0

    def run_turn(self, prompt, **kwargs):
        """Simulate a turn in the conversation"""
        self.call_count += 1

        # Save the prompt to history
        self.history.append({"role": "user", "content": prompt})

        # Get predefined response or use a default one
        prompt_lower = prompt.lower()
        for key, response in self.responses.items():
            if key in prompt_lower:
                self.history.append({"role": "assistant", "content": response})
                return response

        # Default response for any other prompt
        default_response = f"Mock response to: {prompt}"
        self.history.append({"role": "assistant", "content": default_response})
        return default_response


# --- Fixtures ---


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_agent_class():
    """Patch the CodeAgent class with our MockAgent"""
    with patch("code_agent.cli.main.CodeAgent") as mock_class:
        mock_instance = MockAgent()
        mock_class.return_value = mock_instance
        yield mock_class, mock_instance


@pytest.fixture
def mock_config():
    """Mock config for tests"""
    with patch("code_agent.cli.main.get_config") as mock_get:
        mock_config = SettingsConfig(
            default_provider="test_provider",
            default_model="test_model",
            api_keys=ApiKeys(openai="test_key"),
            native_command_allowlist=["ls"],
            rules=["test_rule"],
        )
        mock_get.return_value = mock_config
        yield mock_get


@pytest.fixture
def mock_history_utils():
    """Mock history saving and loading utilities"""
    with (
        patch("code_agent.cli.main.save_history") as mock_save,
        patch("code_agent.cli.main.load_latest_history") as mock_load,
    ):
        # Default empty history
        mock_load.return_value = []
        yield mock_save, mock_load


# --- Test Cases ---


def test_chat_basic_interaction(
    runner, mock_agent_class, mock_config, mock_history_utils
):
    """Test basic chat interaction with simulated input."""
    _, mock_agent = mock_agent_class

    # Simulate typing 'hello', then 'exit'
    result = runner.invoke(app, ["chat"], input="hello\nexit\n")

    # Check command executed successfully
    assert result.exit_code == 0

    # Check expected output is shown
    assert "Starting interactive chat session" in result.stdout
    assert "You:" in result.stdout
    assert "Agent:" in result.stdout
    assert mock_agent.responses["hello"] in result.stdout
    assert "Exiting chat session" in result.stdout

    # Verify agent was called once
    assert mock_agent.call_count == 1


def test_chat_multiple_turns(runner, mock_agent_class, mock_config, mock_history_utils):
    """Test multiple interaction turns in chat session."""
    _, mock_agent = mock_agent_class

    # Simulate three interactions then exit
    result = runner.invoke(app, ["chat"], input="hello\nhelp\nversion\nexit\n")

    # Check all responses
    assert mock_agent.responses["hello"] in result.stdout
    assert mock_agent.responses["help"] in result.stdout
    assert mock_agent.responses["version"] in result.stdout

    # Check agent was called the right number of times
    assert mock_agent.call_count == 3

    # Verify the history was updated correctly
    assert len(mock_agent.history) == 6  # 3 user messages + 3 responses


def test_chat_with_empty_input(
    runner, mock_agent_class, mock_config, mock_history_utils
):
    """Test handling of empty inputs during chat."""
    _, mock_agent = mock_agent_class

    # Simulate empty inputs between valid ones
    result = runner.invoke(app, ["chat"], input="\n  \nhello\nexit\n")

    # Check agent was only called for valid inputs
    assert mock_agent.call_count == 1
    assert "Please enter a non-empty message" in result.stdout


def test_special_commands(runner, mock_agent_class, mock_config, mock_history_utils):
    """Test special commands in chat mode."""
    _, mock_agent = mock_agent_class

    # Simulate special commands
    result = runner.invoke(app, ["chat"], input="/help\n/clear\n/exit\n")

    # Verify special commands were recognized
    assert "Available commands" in result.stdout
    assert "History cleared" in result.stdout
    assert "Exiting chat session" in result.stdout

    # Check agent was not called for special commands
    assert mock_agent.call_count == 0


def test_test_command(runner, mock_agent_class, mock_config, mock_history_utils):
    """Test the /test command for automated testing."""
    _, mock_agent = mock_agent_class

    # Run chat with just the test command
    result = runner.invoke(app, ["chat"], input="/test\n")

    # Verify the test command works
    assert result.exit_code == 0
    assert "TEST_SUCCESS" in result.stdout

    # Check agent was not called for test command
    assert mock_agent.call_count == 0

    # Make sure we exited without saving (no exit message)
    assert "Exiting chat session" not in result.stdout
    mock_save, _ = mock_history_utils
    mock_save.assert_not_called()


def test_chat_with_existing_history(
    runner, mock_agent_class, mock_config, mock_history_utils
):
    """Test loading and continuing from existing history."""
    _, mock_agent = mock_agent_class
    mock_save, mock_load = mock_history_utils

    # Create some existing history
    existing_history = [
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
    ]
    mock_load.return_value = existing_history

    # Run chat with a single message then exit
    result = runner.invoke(app, ["chat"], input="hello\nexit\n")

    # Check that history was loaded
    assert "Loaded 2 messages" in result.stdout
    assert mock_agent.call_count == 1

    # Verify combined history was saved (existing + new exchange)
    mock_save.assert_called_once()
    saved_history = mock_save.call_args[0][1]
    assert len(saved_history) == 4  # 2 existing + 2 new messages


def test_history_saving_mechanism(runner, mock_agent_class, mock_config):
    """Test the actual file writing mechanics of history saving."""
    _, mock_agent = mock_agent_class

    # Create a timestamp for the test
    test_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Patch datetime and file operations
    with (
        patch("datetime.datetime") as mock_dt,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("builtins.open", mock_open()) as mock_file,
    ):
        # Configure datetime mock
        mock_now = MagicMock()
        mock_now.strftime.return_value = test_timestamp
        mock_dt.now.return_value = mock_now

        # Run chat with a single message
        result = runner.invoke(app, ["chat"], input="hello\nexit\n")

        # Verify success
        assert result.exit_code == 0

        # Check directory was created
        mock_mkdir.assert_called()

        # Check file writing (without asserting the exact number of write calls)
        mock_file.assert_called()
        file_handle = mock_file()
        # Verify writing happened at least once
        assert file_handle.write.call_count > 0

        # Instead of checking call count, check that JSON-like content was written
        # by looking at some of the calls
        write_calls = [call[0][0] for call in file_handle.write.call_args_list]
        json_parts = "".join(write_calls)

        # Check basic JSON structure elements are present
        assert '"role": "user"' in json_parts
        assert '"content": "hello"' in json_parts
        assert '"role": "assistant"' in json_parts


def test_chat_with_cli_overrides(
    runner, mock_agent_class, mock_config, mock_history_utils
):
    """Test chat when CLI overrides for provider and model are provided."""
    mock_class, mock_agent = mock_agent_class

    # Run with overrides
    result = runner.invoke(
        app,
        ["--provider", "cli-provider", "--model", "cli-model", "chat"],
        input="hello\nexit\n",
    )

    # Verify command succeeded
    assert result.exit_code == 0

    # Check the agent is created
    mock_class.assert_called_once()

    # And that agent.run_turn was called with our message
    assert mock_agent.call_count == 1
    assert mock_agent.history[0]["content"] == "hello"


def test_error_handling(runner, mock_agent_class, mock_config, mock_history_utils):
    """Test graceful handling of errors during chat."""
    _, mock_agent = mock_agent_class

    # Make agent raise an exception
    mock_agent.run_turn = MagicMock(side_effect=Exception("Test error"))

    # Run chat with a message that will trigger the error
    result = runner.invoke(app, ["chat"], input="trigger error\nexit\n")

    # Check the error was handled gracefully
    assert result.exit_code == 0
    assert "unexpected error" in result.stdout.lower()
    assert "Test error" in result.stdout
    assert "Exiting chat session" in result.stdout


def test_keyboard_interrupt_handling(runner, mock_agent_class, mock_config):
    """Test handling of keyboard interrupts."""
    # Mock prompt to raise KeyboardInterrupt
    with patch("code_agent.cli.main.Prompt.ask", side_effect=KeyboardInterrupt()):
        # Run the command
        result = runner.invoke(app, ["chat"])

    # Check that keyboard interrupt was handled gracefully
    assert result.exit_code == 0
    assert "interrupted" in result.stdout.lower()
    assert "exiting" in result.stdout.lower()
