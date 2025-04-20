import json
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest
from typer.testing import CliRunner
from pathlib import Path

from code_agent.cli.main import app
from code_agent.config import SettingsConfig, ApiKeys
from code_agent.cli.chat import Chat, save_history, load_latest_history

# --- Fixtures ---

runner = CliRunner()


@pytest.fixture
def mock_get_config():
    """Mocks config.get_config for chat tests."""
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
def mock_agent():
    """Mocks the CodeAgent class for chat tests."""
    with patch("code_agent.cli.main.CodeAgent") as mock_agent_class:
        # Setup mock agent instance
        mock_instance = MagicMock()
        mock_instance.history = []
        mock_instance.run_turn.return_value = "Mocked agent response"
        mock_agent_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_prompt_ask():
    """Mocks rich.prompt.Prompt.ask for chat tests."""
    with patch("code_agent.cli.main.Prompt.ask") as mock_ask:
        yield mock_ask


@pytest.fixture
def mock_print():
    """Mocks rich.print for chat tests."""
    with patch("code_agent.cli.main.print") as mock_print:
        yield mock_print


@pytest.fixture
def mock_history_io():
    """Mocks history file operations."""
    # Mock both save_history and load_latest_history
    with (
        patch("code_agent.cli.main.save_history") as mock_save,
        patch("code_agent.cli.main.load_latest_history") as mock_load,
    ):
        mock_load.return_value = []  # Default to empty history
        yield mock_save, mock_load


# --- Test Cases ---


def test_chat_new_session(
    mock_get_config, mock_agent, mock_prompt_ask, mock_print, mock_history_io
):
    """Test starting a new chat session and handling multiple turns."""
    mock_save, mock_load = mock_history_io

    # Setup mock prompt responses - several queries then exit
    mock_prompt_ask.side_effect = ["Hello, agent!", "What can you do?", "exit"]

    # Setup agent responses
    mock_agent.run_turn.side_effect = [
        "Hello! I'm a code assistant.",
        "I can help with coding tasks, run commands, and edit files.",
    ]

    # Run the command
    result = runner.invoke(app, ["chat"])

    # Check success and key output messages
    assert result.exit_code == 0
    assert "Starting interactive chat session" in result.stdout
    assert "Starting new chat session" in result.stdout
    assert "Exiting chat session" in result.stdout

    # Check agent was initialized and called correctly
    assert mock_agent.run_turn.call_count == 2

    # First call should have just the first message
    first_call_args = mock_agent.run_turn.call_args_list[0][1]
    assert first_call_args["prompt"] == "Hello, agent!"
    assert first_call_args["provider"] == "test_provider"
    assert first_call_args["model"] == "test_model"
    assert isinstance(first_call_args["history"], list)
    assert len(first_call_args["history"]) == 1

    # Second call should include first exchange in history
    second_call_args = mock_agent.run_turn.call_args_list[1][1]
    assert second_call_args["prompt"] == "What can you do?"
    assert len(second_call_args["history"]) == 3  # user1 + assistant1 + user2

    # Check history was saved with both exchanges
    mock_save.assert_called_once()
    save_history_args = mock_save.call_args[0]
    assert len(save_history_args) == 2  # session_id, history
    saved_history = save_history_args[1]
    assert len(saved_history) == 4  # Two complete exchanges (2 user + 2 assistant)


def test_chat_load_history(
    mock_get_config, mock_agent, mock_prompt_ask, mock_print, mock_history_io
):
    """Test loading existing history and continuing the conversation."""
    mock_save, mock_load = mock_history_io

    # Setup existing history
    existing_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    mock_load.return_value = existing_history

    # One user input then exit
    mock_prompt_ask.side_effect = ["Follow-up question", "exit"]
    mock_agent.run_turn.return_value = "Follow-up answer"

    # Run the command
    result = runner.invoke(app, ["chat"])

    # Check the result
    assert result.exit_code == 0
    assert "Loading history" in result.stdout
    assert "Loaded 2 messages" in result.stdout

    # Agent should receive history + new prompt
    mock_agent.run_turn.assert_called_once()
    agent_call_args = mock_agent.run_turn.call_args[1]
    assert agent_call_args["prompt"] == "Follow-up question"
    assert len(agent_call_args["history"]) == 3  # 2 existing + 1 new user message

    # History should be saved with the new exchange
    mock_save.assert_called_once()
    saved_history = mock_save.call_args[0][1]
    assert len(saved_history) == 4  # 2 existing + new Q&A pair


def test_chat_empty_input_handling(
    mock_get_config, mock_agent, mock_prompt_ask, mock_print, mock_history_io
):
    """Test handling of empty inputs during chat."""
    # Mock user entering empty strings then valid input then exit
    mock_prompt_ask.side_effect = ["", "  ", "valid input", "exit"]
    mock_agent.run_turn.return_value = "Response to valid input"

    # Run the command
    result = runner.invoke(app, ["chat"])

    # Check that empty inputs were handled properly
    assert result.exit_code == 0
    assert "Please enter a non-empty message" in result.stdout

    # Check that the agent was only called once with the valid input
    mock_agent.run_turn.assert_called_once_with(
        prompt="valid input",
        provider="test_provider",
        model="test_model",
        history=[{"role": "user", "content": "valid input"}],
    )


def test_chat_history_saving_mechanism(mock_get_config, mock_agent, mock_prompt_ask):
    """Test the actual implementation of history saving."""
    # Mock open for file operations
    mock_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    expected_filename = f"chat_{mock_timestamp}.json"

    # Use patch to mock datetime.now() to return a fixed timestamp
    with (
        patch("code_agent.cli.main.datetime", MagicMock()) as mock_datetime,
        patch("os.path.exists", return_value=False) as mock_exists,
        patch("os.makedirs") as mock_makedirs,
        patch("builtins.open", mock_open()) as mock_file,
    ):
        # Set up datetime mock
        mock_dt = MagicMock()
        mock_dt.now.return_value = datetime.strptime(mock_timestamp, "%Y%m%d_%H%M%S")
        mock_datetime.datetime = mock_dt
        mock_datetime.now.return_value = mock_dt.now()
        mock_datetime.strptime = datetime.strptime

        # Setup chat sequence
        mock_prompt_ask.side_effect = ["test message", "exit"]
        mock_agent.run_turn.return_value = "test response"

        # Run chat command
        result = runner.invoke(app, ["chat"])

        # Check the command succeeded
        assert result.exit_code == 0

        # Verify directory was created
        mock_makedirs.assert_called_once()

        # Verify file was opened and written
        mock_file.assert_called()
        # Get the call for writing the file
        file_handle = mock_file()
        file_handle.write.assert_called_once()

        # Check that the written data is valid JSON and contains our messages
        write_call_args = file_handle.write.call_args[0]
        assert len(write_call_args) == 1
        try:
            written_data = json.loads(write_call_args[0])
            assert len(written_data) == 2
            assert written_data[0]["role"] == "user"
            assert written_data[0]["content"] == "test message"
            assert written_data[1]["role"] == "assistant"
            assert written_data[1]["content"] == "test response"
        except json.JSONDecodeError:
            pytest.fail("Written history is not valid JSON")


def test_chat_command_errors(mock_get_config, mock_agent, mock_prompt_ask):
    """Test error handling in the chat command."""
    # Set up agent to raise an exception
    mock_agent.run_turn.side_effect = Exception("Test error in agent")

    # User enters one message then exits
    mock_prompt_ask.side_effect = ["trigger error", "exit"]

    # Run the command
    result = runner.invoke(app, ["chat"])

    # Check the command handled the error gracefully
    assert result.exit_code == 0
    assert "Error" in result.stdout
    assert "Test error in agent" in result.stdout


def test_chat_special_commands(
    mock_get_config, mock_agent, mock_prompt_ask, mock_print, mock_history_io
):
    """Test handling of special commands in chat mode."""
    mock_save, mock_load = mock_history_io

    # Test commands: /help, /clear, and /exit
    mock_prompt_ask.side_effect = ["/help", "/clear", "/exit"]

    # Run the command
    result = runner.invoke(app, ["chat"])

    # Check that special commands were handled correctly
    assert result.exit_code == 0

    # Help command should show available commands
    assert "Available commands" in result.stdout
    assert "/help" in result.stdout
    assert "/clear" in result.stdout
    assert "/exit" in result.stdout

    # Clear command should reset history
    assert "History cleared" in result.stdout

    # Should exit properly
    assert "Exiting chat session" in result.stdout

    # Check that we didn't call the agent for special commands
    assert mock_agent.run_turn.call_count == 0


def test_chat_with_model_provider_overrides(
    mock_get_config, mock_agent, mock_prompt_ask
):
    """Test chat with CLI overrides for model and provider."""
    # Setup single message then exit
    mock_prompt_ask.side_effect = ["test message", "exit"]

    # Custom provider and model
    custom_provider = "custom-provider"
    custom_model = "custom-model"

    # Run with overrides
    result = runner.invoke(
        app, ["--provider", custom_provider, "--model", custom_model, "chat"]
    )

    # Verify success
    assert result.exit_code == 0

    # Just verify the agent was called
    mock_agent.run_turn.assert_called_once()
    # Note: Actual parameter checking would require inspecting how the CLI passes these values to the agent


def test_special_test_command(
    mock_get_config: MagicMock,
    mock_agent: MagicMock,
    mock_prompt_ask: MagicMock,
    mock_history_io,
):
    """Test the /test special command for automated testing."""
    # Configure mock config with proper values
    mock_config = SettingsConfig(
        default_provider="test_provider",
        default_model="test_model",
        api_keys=ApiKeys(openai="test_key"),
        native_command_allowlist=["ls"],
        rules=["test_rule"],
    )
    mock_get_config.return_value = mock_config

    # Configure mocks
    mock_prompt_ask.side_effect = ["/test"]  # User types /test command

    # Run the chat command
    result = runner.invoke(app, ["chat"])

    # Verify results
    assert result.exit_code == 0
    assert "TEST_SUCCESS" in result.stdout

    # Check that agent was not called (special command is handled directly)
    mock_agent.run_turn.assert_not_called()

    # Ensure session exited after /test command
    assert "Exiting chat session" not in result.stdout  # No standard exit message
