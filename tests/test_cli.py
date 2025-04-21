from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent import __version__ as agent_version

# Assuming cli.main defines the 'app'
from code_agent.cli.main import app
from code_agent.config import (  # Changed Config -> SettingsConfig
    ApiKeys,
    SettingsConfig,
)

# --- Fixtures ---

runner = CliRunner()


@pytest.fixture
def mock_get_config():
    """Mocks config.get_config for CLI tests."""
    # Use the same mock pattern as in test_native_tools
    with patch("code_agent.cli.main.get_config") as mock_get:
        # Simulate returning a valid config object
        mock_config = MagicMock(spec=SettingsConfig)
        mock_config.default_provider = "openai"
        mock_config.default_model = "gpt-4"
        mock_config.api_keys = MagicMock(spec=ApiKeys)
        mock_config.api_keys.openai = "test-key"
        # Add other necessary attributes if tests require them
        mock_get.return_value = mock_config
        yield mock_get


@pytest.fixture
def mock_run_agent_turn():
    """Mocks agent.run_agent_turn for CLI tests."""
    # Patch the run_turn method within the CodeAgent class
    with patch("code_agent.agent.agent.CodeAgent.run_turn") as mock_run:
        yield mock_run


@pytest.fixture
def mock_prompt_ask():
    """Mocks rich.prompt.Prompt.ask for CLI tests."""
    with patch("code_agent.cli.main.Prompt.ask") as mock_ask:
        # Default behavior: return 'exit' to stop loop quickly
        mock_ask.return_value = "exit"
        yield mock_ask


@pytest.fixture
def mock_load_history():
    """Mocks history loading."""
    with patch("code_agent.cli.main.load_latest_history") as mock_load:
        mock_load.return_value = []  # Default to no history
        yield mock_load


@pytest.fixture
def mock_save_history():
    """Mocks history saving."""
    with patch("code_agent.cli.main.save_history") as mock_save:
        yield mock_save


# --- Test Cases ---


def test_cli_version():
    """Test the --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"Code Agent version: {agent_version}" in result.stdout


def test_cli_config_show(mock_get_config: MagicMock):
    """Test the 'config show' command."""
    # Configure the mock return value for this specific test if needed
    mock_config = SettingsConfig(
        default_provider="test-openai",
        default_model="test-gpt",
        api_keys=ApiKeys(openai="key1", groq="key2"),
        auto_approve_edits=True,
        native_command_allowlist=["echo"],
    )
    mock_get_config.return_value = mock_config

    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Current Effective Configuration" in result.stdout
    assert "test-openai" in result.stdout
    assert "test-gpt" in result.stdout
    assert "groq" in result.stdout
    assert "echo" in result.stdout


def test_cli_providers_list(mock_get_config: MagicMock):
    """Test the 'providers list' command."""
    mock_config = SettingsConfig(
        default_provider="groq",
        default_model="llama3",
        api_keys=ApiKeys(openai="key1", groq="key2", anthropic=None),  # Mock keys
    )
    mock_get_config.return_value = mock_config

    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "Configured LLM Providers:" in result.stdout
    assert "groq / llama3" in result.stdout
    assert "OpenAI:" in result.stdout
    assert "Groq:" in result.stdout
    assert "✓ Configured" in result.stdout
    assert "Anthropic:" in result.stdout
    assert "✗ Not configured" in result.stdout


def test_cli_run_basic(mock_run_agent_turn: MagicMock):
    """Test the basic 'run' command, mocking the agent call."""
    prompt_text = "Tell me a joke."
    mock_run_agent_turn.return_value = "Why don't scientists trust atoms? Because they make up everything!"
    result = runner.invoke(app, ["run", prompt_text])

    assert result.exit_code == 0
    assert prompt_text in result.stdout
    assert "Response:" in result.stdout
    assert mock_run_agent_turn.return_value in result.stdout
    mock_run_agent_turn.assert_called_once_with(prompt=prompt_text)


def test_cli_run_with_overrides(mock_run_agent_turn: MagicMock):
    """Test the 'run' command with provider and model overrides."""
    prompt_text = "Explain FastAPI."
    provider = "test_provider"
    model = "test_model_xl"
    mock_run_agent_turn.return_value = "FastAPI is a modern, fast web framework."
    result = runner.invoke(app, ["--provider", provider, "--model", model, "run", prompt_text])

    assert result.exit_code == 0
    mock_run_agent_turn.assert_called_once_with(prompt=prompt_text)
    assert mock_run_agent_turn.return_value in result.stdout


def test_cli_chat_single_turn(
    mock_get_config: MagicMock,
    mock_run_agent_turn: MagicMock,
    mock_prompt_ask: MagicMock,
    mock_load_history: MagicMock,
    mock_save_history: MagicMock,
):
    """Test starting chat, asking one question, and exiting."""
    user_input = "Hello Agent"
    agent_response = "Hello User!"

    # Configure mocks
    mock_prompt_ask.side_effect = [user_input, "quit"]  # First input, then quit
    mock_run_agent_turn.return_value = agent_response  # Set return value
    mock_load_history.return_value = []  # Start fresh

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0
    # Check startup messages (these are printed before mocks take over)
    assert "Starting interactive chat session..." in result.stdout
    assert "Starting new chat session." in result.stdout
    # Check agent response is present
    assert "Agent:" in result.stdout
    assert agent_response in result.stdout
    # Check calls
    mock_run_agent_turn.assert_called_once_with(prompt=user_input)
    mock_load_history.assert_called_once()
    mock_save_history.assert_called_once()


def test_cli_chat_load_history(
    mock_get_config: MagicMock,
    mock_run_agent_turn: MagicMock,
    mock_prompt_ask: MagicMock,
    mock_load_history: MagicMock,
    mock_save_history: MagicMock,
):
    """Test loading history and continuing the conversation."""
    initial_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    user_input = "Follow up question"
    agent_response = "Follow up answer"

    # Configure mocks
    mock_prompt_ask.side_effect = [user_input, "exit"]
    mock_run_agent_turn.return_value = agent_response  # Set return value
    mock_load_history.return_value = initial_history  # Load this history

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0
    # Check startup messages (these are printed before mocks take over)
    assert "Starting interactive chat session..." in result.stdout
    # Check agent response is present
    assert "Agent:" in result.stdout
    assert agent_response in result.stdout
    # Check that the loading function was called (but don't check its print output)
    mock_load_history.assert_called_once()
    # Check other calls
    mock_run_agent_turn.assert_called_once_with(prompt=user_input)
    mock_save_history.assert_called_once()


# TODO [HIGH PRIORITY]: Add tests for 'chat' command (more complex due to interaction)
