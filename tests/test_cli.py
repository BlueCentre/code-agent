import json
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
    with patch("code_agent.cli.main.config_module.get_config") as mock_get:
        # Default mock config unless overridden in test
        mock_config = SettingsConfig(
            default_provider="mock_provider",
            default_model="mock_model",
            api_keys=ApiKeys(openai="mock_key", groq=None),
            native_command_allowlist=["ls"],
            rules=["test_rule"]
        )
        mock_get.return_value = mock_config
        yield mock_get

@pytest.fixture
def mock_run_agent_turn():
    """Mocks agent.run_agent_turn for CLI tests."""
    with patch("code_agent.cli.main.run_agent_turn") as mock_run:
        mock_run.return_value = "Mocked agent response."
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
        mock_load.return_value = [] # Default to no history
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
        native_command_allowlist=["echo"]
    )
    mock_get_config.return_value = mock_config

    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Current Configuration:" in result.stdout
    # Check if the output is valid JSON and contains expected values
    try:
        output_json = json.loads(result.stdout.split("Current Configuration:")[1].strip())
        assert output_json["default_provider"] == "test-openai"
        assert output_json["default_model"] == "test-gpt"
        assert output_json["api_keys"]["openai"] == "key1"
        assert output_json["api_keys"]["groq"] == "key2"
        assert output_json["auto_approve_edits"] is True
        assert output_json["native_command_allowlist"] == ["echo"]
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        pytest.fail(
            f"Failed to parse config show output or find keys: {e}\n"
            f"Output:\n{result.stdout}"
        )

def test_cli_providers_list(mock_get_config: MagicMock):
    """Test the 'providers list' command."""
    mock_config = SettingsConfig(
        default_provider="groq",
        default_model="llama3",
        api_keys=ApiKeys(openai="key1", groq="key2", anthropic=None) # Mock keys
    )
    mock_get_config.return_value = mock_config

    result = runner.invoke(app, ["providers", "list"])
    assert result.exit_code == 0
    assert "Configured Providers (with API keys):" in result.stdout
    assert "- openai" in result.stdout
    assert "- groq" in result.stdout
    assert "- anthropic" not in result.stdout # Key is None
    assert "Default Provider: groq" in result.stdout
    assert "Default Model: llama3" in result.stdout

def test_cli_run_basic(mock_run_agent_turn: MagicMock):
    """Test the basic 'run' command, mocking the agent call."""
    prompt_text = "Tell me a joke."
    result = runner.invoke(app, ["run", prompt_text])

    assert result.exit_code == 0
    assert f"Prompt: {prompt_text}" in result.stdout
    # Check that the agent runner was called correctly (without overrides)
    mock_run_agent_turn.assert_called_once_with(
        prompt=prompt_text,
        provider=None, # No override specified
        model=None     # No override specified
    )
    # Check if the mocked response is in the output (rendered as Markdown)
    assert "Mocked agent response." in result.stdout # Simple check

def test_cli_run_with_overrides(mock_run_agent_turn: MagicMock):
    """Test the 'run' command with provider and model overrides."""
    prompt_text = "Explain FastAPI."
    provider = "test_provider"
    model = "test_model_xl"
    result = runner.invoke(app, [
        "--provider", provider,
        "--model", model,
        "run",
        prompt_text
    ])

    assert result.exit_code == 0
    assert f"Prompt: {prompt_text}" in result.stdout
    # Check that the agent runner was called with overrides
    mock_run_agent_turn.assert_called_once_with(
        prompt=prompt_text,
        provider=provider, # Check override
        model=model      # Check override
    )
    assert "Mocked agent response." in result.stdout

def test_cli_chat_single_turn(
    mock_get_config: MagicMock,
    mock_run_agent_turn: MagicMock,
    mock_prompt_ask: MagicMock,
    mock_load_history: MagicMock,
    mock_save_history: MagicMock
):
    """Test starting chat, asking one question, and exiting."""
    user_input = "Hello Agent"
    agent_response = "Hello User!"

    # Configure mocks
    mock_prompt_ask.side_effect = [user_input, "quit"] # First input, then quit
    mock_run_agent_turn.return_value = agent_response
    mock_load_history.return_value = [] # Start fresh

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0
    # Check startup messages
    assert "Starting interactive chat session..." in result.stdout
    assert "Starting new chat session." in result.stdout
    # Check prompts and responses
    assert "You:" in result.stdout # Check if prompt is shown (rich formatting might complicate exact match)
    assert "Agent:" in result.stdout
    assert agent_response in result.stdout
    assert "Exiting chat session." in result.stdout

    # Verify mocks
    mock_load_history.assert_called_once()
    assert mock_prompt_ask.call_count == 2
    mock_run_agent_turn.assert_called_once_with(
        prompt=user_input,
        provider="mock_provider", # From mock_get_config
        model="mock_model",      # From mock_get_config
        history=[{"role": "user", "content": user_input}]
    )
    # Verify history saved on quit
    expected_history = [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": agent_response}
    ]
    # Need to check the second argument of the call
    assert mock_save_history.call_count == 1
    saved_history_args = mock_save_history.call_args[0]
    assert len(saved_history_args) == 2 # session_id, history
    assert saved_history_args[1] == expected_history # Check the history list

def test_cli_chat_load_history(
    mock_get_config: MagicMock,
    mock_run_agent_turn: MagicMock,
    mock_prompt_ask: MagicMock,
    mock_load_history: MagicMock,
    mock_save_history: MagicMock
):
    """Test loading history and continuing the conversation."""
    initial_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]
    user_input = "Follow up question"
    agent_response = "Follow up answer"

    # Configure mocks
    mock_prompt_ask.side_effect = [user_input, "exit"]
    mock_run_agent_turn.return_value = agent_response
    mock_load_history.return_value = initial_history # Load this history

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0
    # Check startup messages
    assert "Loading history from" in result.stdout
    assert f"Loaded {len(initial_history)} messages" in result.stdout
    assert "Agent:" in result.stdout
    assert agent_response in result.stdout
    assert "Exiting chat session." in result.stdout

    # Verify agent was called with loaded history + new prompt
    expected_call_history = [*initial_history, {"role": "user", "content": user_input}]
    mock_run_agent_turn.assert_called_once_with(
        prompt=user_input,
        provider="mock_provider",
        model="mock_model",
        history=expected_call_history
    )

    # Verify history saved on exit includes everything
    expected_saved_history = [
        *expected_call_history,
        {"role": "assistant", "content": agent_response}
    ]
    assert mock_save_history.call_count == 1
    saved_history_args = mock_save_history.call_args[0]
    assert saved_history_args[1] == expected_saved_history

# TODO: Add tests for 'chat' command (more complex due to interaction)
# A simple test could check the startup message and mock the first agent call.
