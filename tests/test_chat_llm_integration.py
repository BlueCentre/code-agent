"""Tests for chat command with advanced LLM interactions and tool calls."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app
from code_agent.config import ApiKeys, SettingsConfig

# --- Fixtures ---


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock config for tests"""
    with patch("code_agent.cli.main.get_config") as mock_get:
        mock_config = SettingsConfig(
            default_provider="test_provider",
            default_model="test_model",
            api_keys=ApiKeys(openai="test_key"),
            native_command_allowlist=["ls", "pwd", "cat"],
            rules=["test_rule"],
            auto_approve_edits=True,  # Auto approve edits for testing
        )
        mock_get.return_value = mock_config
        # Also patch the agent module's config access
        with patch("code_agent.agent.agent.get_config") as mock_agent_get:
            mock_agent_get.return_value = mock_config
            yield mock_config


@pytest.fixture
def mock_agent():
    """Mock agent for tests with customizable behavior"""
    with patch("code_agent.cli.main.CodeAgent") as mock_agent_class:
        # Create mock instance that all tests can customize
        mock_instance = MagicMock()
        mock_instance.history = []  # Initialize with empty history

        # Set default return value for run_turn
        mock_instance.run_turn.return_value = "Mock agent response"

        # Configure the agent class to return our mock instance
        mock_agent_class.return_value = mock_instance

        yield mock_instance


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


def test_chat_with_simple_llm_response(
    runner, mock_config, mock_agent, mock_history_utils
):
    """Test chat command with a simple LLM text response."""
    # Configure the agent's run_turn method to return a response
    mock_agent.run_turn.return_value = "This is a simple test response."

    # Run the chat command with a single message then exit
    result = runner.invoke(app, ["chat"], input="hello\nexit\n")

    # Verify the command executed successfully
    assert result.exit_code == 0

    # Check that the agent was called with the correct prompt
    mock_agent.run_turn.assert_called_with(prompt="hello")

    # Check the response was displayed
    assert "This is a simple test response." in result.stdout


def test_chat_with_tool_calls_integrated(runner, mock_config, mock_history_utils):
    """Test chat with an LLM that makes tool calls, using a more integrated approach."""
    # Create a mock agent that returns a response about handling files
    with patch("code_agent.cli.main.CodeAgent") as mock_agent_class:
        # Mock agent instance
        mock_agent = MagicMock()
        mock_agent.history = []

        # Custom response based on input
        def custom_response(prompt, **kwargs):
            if "read file" in prompt.lower():
                return "I've read the file. It contains Python code."
            elif "analyze" in prompt.lower():
                return "I've analyzed the files in the directory."
            elif "invalid" in prompt.lower():
                return "I encountered an error running that command."
            elif "edit" in prompt.lower():
                return "I've edited the file for you."
            else:
                return "I don't know how to respond to that."

        # Set the mock response
        mock_agent.run_turn = MagicMock(side_effect=custom_response)
        mock_agent_class.return_value = mock_agent

        # Run the chat command with different requests
        inputs = [
            "Please read file example.py\n",
            "Analyze my project directory\n",
            "Try to run an invalid command\n",
            "Edit my test_file.py\n",
            "exit\n",
        ]
        result = runner.invoke(app, ["chat"], input="".join(inputs))

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Check that the agent was called for each prompt
        assert mock_agent.run_turn.call_count == 4  # Four prompts, then exit

        # Check that the expected responses are in the output
        assert "I've read the file. It contains Python code." in result.stdout
        assert "I've analyzed the files in the directory." in result.stdout
        assert "I encountered an error running that command." in result.stdout
        assert "I've edited the file for you." in result.stdout


def test_chat_special_commands(runner, mock_config, mock_agent, mock_history_utils):
    """Test special commands in chat mode without invoking the agent."""
    # Run the chat command with special commands
    result = runner.invoke(app, ["chat"], input="/help\n/clear\n/exit\n")

    # Verify the command executed successfully
    assert result.exit_code == 0

    # Check that special commands were recognized and acted upon
    assert "Available commands" in result.stdout
    assert "History cleared" in result.stdout
    assert "Exiting chat session" in result.stdout

    # Verify agent was not called for special commands
    mock_agent.run_turn.assert_not_called()


def test_chat_error_handling(runner, mock_config, mock_agent, mock_history_utils):
    """Test handling of agent errors during chat."""
    # Configure agent to raise an exception
    mock_agent.run_turn.side_effect = Exception("Test error message")

    # Run chat with a prompt that will trigger the error
    result = runner.invoke(app, ["chat"], input="trigger error\nexit\n")

    # Verify the command handled the error gracefully
    assert result.exit_code == 0

    # Check the error was reported but didn't crash the app
    assert "An unexpected error occurred" in result.stdout
    assert "Test error message" in result.stdout
    assert "Exiting chat session" in result.stdout


def test_chat_keyboard_interrupt(runner, mock_config, mock_history_utils):
    """Test handling of keyboard interrupt (Ctrl+C) during chat."""
    with patch("code_agent.cli.main.CodeAgent") as mock_agent_class:
        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.history = []
        mock_agent_class.return_value = mock_agent

        # Patch the Prompt.ask to simulate keyboard interrupt
        with patch("code_agent.cli.main.Prompt.ask", side_effect=KeyboardInterrupt):
            # Run the chat command
            result = runner.invoke(app, ["chat"])

            # Verify the command handled the interrupt gracefully
            assert result.exit_code == 0
            assert "Chat interrupted" in result.stdout


def test_chat_with_multiple_turns(runner, mock_config, mock_history_utils):
    """Test multiple interaction turns in a chat session."""
    with patch("code_agent.cli.main.CodeAgent") as mock_agent_class:
        # Create a mock agent with different responses for each prompt
        mock_agent = MagicMock()
        mock_agent.history = []

        # Set up different responses for each prompt
        responses = {
            "hello": "Hello! How can I help?",
            "what can you do": "I can help with coding tasks, file operations, and more.",
            "goodbye": "Goodbye! Feel free to chat again later.",
        }

        def get_response(prompt, **kwargs):
            for key, response in responses.items():
                if key in prompt.lower():
                    return response
            return "I'm not sure how to respond to that."

        mock_agent.run_turn = MagicMock(side_effect=get_response)
        mock_agent_class.return_value = mock_agent

        # Run chat with multiple inputs then exit
        inputs = "hello\nwhat can you do\ngoodbye\nexit\n"
        result = runner.invoke(app, ["chat"], input=inputs)

        # Verify the command executed successfully
        assert result.exit_code == 0

        # Check that the agent was called for each prompt
        assert mock_agent.run_turn.call_count == 3

        # Check that all responses are in the output
        for response in responses.values():
            assert response in result.stdout
