import json
from unittest.mock import MagicMock, patch

import pytest
import litellm
from rich.console import Console
from typer.testing import CliRunner

from code_agent.cli.main import app
from code_agent.agent.agent import CodeAgent
from code_agent.config import SettingsConfig, ApiKeys


@pytest.fixture
def mock_litellm():
    """Mock litellm for testing API errors"""
    with patch("code_agent.agent.agent.litellm.completion") as mock_completion:
        yield mock_completion


@pytest.fixture
def agent_with_mock_config():
    """Create an agent with a mocked config"""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = SettingsConfig(
            default_provider="openai",
            default_model="gpt-4",
            api_keys=ApiKeys(openai="mock-key"),
            native_command_allowlist=["ls", "pwd"]
        )
        mock_get_config.return_value = config
        agent = CodeAgent()
        yield agent


@pytest.fixture
def cli_runner():
    """Runner for CLI tests"""
    return CliRunner()


# --- API Error Tests ---

def test_agent_api_connection_error(agent_with_mock_config, mock_litellm):
    """Test handling of connection errors from the API"""
    # Mock litellm to raise a connection error
    mock_litellm.side_effect = litellm.exceptions.ServiceUnavailableError(
        message="API is currently unavailable",
        status_code=503
    )
    
    # Try to run the agent
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Test prompt")
    
    # Check that error was handled and printed
    assert result is None
    mock_print.assert_any_call("[bold red]Error: Service Unavailable (503)[/bold red]")
    mock_print.assert_any_call("API is currently unavailable")


def test_agent_api_rate_limit_error(agent_with_mock_config, mock_litellm):
    """Test handling of rate limit errors"""
    # Mock litellm to raise a rate limit error
    mock_litellm.side_effect = litellm.exceptions.RateLimitError(
        message="Rate limit exceeded. Please try again later.",
        status_code=429
    )
    
    # Try to run the agent
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Test prompt")
    
    # Check that error was handled and printed with helpful message
    assert result is None
    mock_print.assert_any_call("[bold red]Error: Rate Limit Exceeded (429)[/bold red]")
    mock_print.assert_any_call("Rate limit exceeded. Please try again later.")
    mock_print.assert_any_call("[yellow]Suggestion: Try again in a few minutes or use a different provider/model.[/yellow]")


def test_agent_api_invalid_key_error(agent_with_mock_config, mock_litellm):
    """Test handling of invalid API key errors"""
    # Mock litellm to raise an authentication error
    mock_litellm.side_effect = litellm.exceptions.AuthenticationError(
        message="Invalid API key provided",
        status_code=401
    )
    
    # Try to run the agent
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Test prompt")
    
    # Check that error was handled with helpful message
    assert result is None
    mock_print.assert_any_call("[bold red]Error: Authentication Failed (401)[/bold red]")
    mock_print.assert_any_call("Invalid API key provided")
    mock_print.assert_any_call("[yellow]Please check your API key in config.yaml or environment variables.[/yellow]")


def test_agent_api_context_length_error(agent_with_mock_config, mock_litellm):
    """Test handling of context length exceeded errors"""
    # Mock litellm to raise a context length error
    mock_litellm.side_effect = litellm.exceptions.ContextWindowExceededError(
        message="This model's maximum context length is 8192 tokens. You provided 9000 tokens.",
        status_code=400
    )
    
    # Try to run the agent
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Test prompt")
    
    # Check that appropriate error message was printed
    assert result is None
    mock_print.assert_any_call("[bold red]Error: Context Length Exceeded (400)[/bold red]")
    mock_print.assert_any_call("This model's maximum context length is 8192 tokens. You provided 9000 tokens.")
    mock_print.assert_any_call("[yellow]Suggestion: Try shortening your prompt or using a model with a larger context window.[/yellow]")


# --- Tool Error Tests ---

def test_agent_read_file_error(agent_with_mock_config, mock_litellm):
    """Test handling of file read errors during tool calls"""
    # Mock LLM to call the read_file tool
    tool_call_response = MagicMock()
    tool_call_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": json.dumps({"path": "nonexistent_file.txt"})
                        }
                    }
                ]
            }
        )
    ]
    
    final_response = MagicMock()
    final_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": "I've processed the tool result."
            }
        )
    ]
    
    mock_litellm.side_effect = [tool_call_response, final_response]
    
    # Mock read_file to raise a FileNotFoundError
    with patch("code_agent.agent.agent.read_file") as mock_read_file, \
         patch("code_agent.agent.agent.print") as mock_print:
        mock_read_file.side_effect = FileNotFoundError("File not found: nonexistent_file.txt")
        
        # Run the agent
        result = agent_with_mock_config.run_turn("Show me the contents of nonexistent_file.txt")
    
    # Check that error was properly handled and passed back to the LLM
    assert result == "I've processed the tool result."
    
    # Check that the error was properly formatted in the message to the LLM
    second_call_args = mock_litellm.call_args_list[1][1]["messages"]
    tool_response_msg = [msg for msg in second_call_args if msg.get("role") == "tool"]
    assert len(tool_response_msg) == 1
    assert "Error" in tool_response_msg[0]["content"]
    assert "File not found" in tool_response_msg[0]["content"]


def test_agent_apply_edit_error(agent_with_mock_config, mock_litellm):
    """Test handling of file edit errors during tool calls"""
    # Mock LLM to call the apply_edit tool
    tool_call_response = MagicMock()
    tool_call_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "apply_edit",
                            "arguments": json.dumps({
                                "target_file": "/invalid/path/file.py",
                                "code_edit": "def new_function():\n    pass"
                            })
                        }
                    }
                ]
            }
        )
    ]
    
    final_response = MagicMock()
    final_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": "I've processed the edit result."
            }
        )
    ]
    
    mock_litellm.side_effect = [tool_call_response, final_response]
    
    # Mock apply_edit to raise a PermissionError
    with patch("code_agent.agent.agent.apply_edit") as mock_apply_edit, \
         patch("code_agent.agent.agent.print") as mock_print:
        mock_apply_edit.side_effect = PermissionError("Permission denied: /invalid/path/file.py")
        
        # Run the agent
        result = agent_with_mock_config.run_turn("Edit the file at /invalid/path/file.py")
    
    # Check that error was properly handled and passed back to the LLM
    assert result == "I've processed the edit result."
    
    # Check that the error was properly formatted in the message to the LLM
    second_call_args = mock_litellm.call_args_list[1][1]["messages"]
    tool_response_msg = [msg for msg in second_call_args if msg.get("role") == "tool"]
    assert len(tool_response_msg) == 1
    assert "Error" in tool_response_msg[0]["content"]
    assert "Permission denied" in tool_response_msg[0]["content"]


def test_agent_run_command_error(agent_with_mock_config, mock_litellm):
    """Test handling of command execution errors"""
    # Mock LLM to call the run_native_command tool
    tool_call_response = MagicMock()
    tool_call_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "run_native_command",
                            "arguments": json.dumps({
                                "command": "invalid_command --option"
                            })
                        }
                    }
                ]
            }
        )
    ]
    
    final_response = MagicMock()
    final_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": "I've processed the command result."
            }
        )
    ]
    
    mock_litellm.side_effect = [tool_call_response, final_response]
    
    # Mock run_native_command to raise a subprocess error
    with patch("code_agent.agent.agent.run_native_command") as mock_run_command, \
         patch("code_agent.agent.agent.print") as mock_print:
        mock_run_command.side_effect = Exception("Command 'invalid_command' not found")
        
        # Run the agent
        result = agent_with_mock_config.run_turn("Run the invalid_command")
    
    # Check that error was properly handled and passed back to the LLM
    assert result == "I've processed the command result."
    
    # Check that the error message was passed to the LLM
    second_call_args = mock_litellm.call_args_list[1][1]["messages"]
    tool_response_msg = [msg for msg in second_call_args if msg.get("role") == "tool"]
    assert len(tool_response_msg) == 1
    assert "Error" in tool_response_msg[0]["content"]
    assert "Command 'invalid_command' not found" in tool_response_msg[0]["content"]


# --- CLI Error Handling Tests ---

def test_cli_run_command_no_api_key(cli_runner):
    """Test CLI handling of missing API key"""
    # Mock config to return no API key
    with patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        mock_config = SettingsConfig(
            default_provider="openai",
            default_model="gpt-4",
            api_keys=ApiKeys(openai=None),  # No API key
            native_command_allowlist=["ls"]
        )
        mock_get_config.return_value = mock_config
        
        # Run the command
        result = cli_runner.invoke(app, ["run", "Test prompt"])
    
    # Check that error was handled gracefully
    assert result.exit_code == 0
    assert "Error: No API key found for provider" in result.stdout
    # Should show fallback mode
    assert "Using fallback simple command handling" in result.stdout


def test_cli_chat_command_user_interrupt(cli_runner):
    """Test handling of user interrupts (Ctrl+C) during chat"""
    # Mock prompt to raise KeyboardInterrupt
    with patch("code_agent.cli.main.Prompt.ask") as mock_ask, \
         patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        mock_config = SettingsConfig(
            default_provider="openai",
            default_model="gpt-4",
            api_keys=ApiKeys(openai="mock-key")
        )
        mock_get_config.return_value = mock_config
        
        # Simulate keyboard interrupt
        mock_ask.side_effect = KeyboardInterrupt()
        
        # Run the command
        result = cli_runner.invoke(app, ["chat"])
    
    # Check that keyboard interrupt was handled gracefully
    assert result.exit_code == 0
    assert "Interrupted by user" in result.stdout


def test_cli_config_show_with_missing_config(cli_runner):
    """Test handling of missing config file"""
    # Mock get_config to raise FileNotFoundError
    with patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        mock_get_config.side_effect = FileNotFoundError("Config file not found")
        
        # Run the command
        result = cli_runner.invoke(app, ["config", "show"])
    
    # Check that error was handled gracefully
    assert result.exit_code == 0
    assert "Error" in result.stdout
    assert "Config file not found" in result.stdout
    assert "Creating a default configuration" in result.stdout


# --- LLM Error Handling Tests ---

def test_agent_malformed_tool_call(agent_with_mock_config, mock_litellm):
    """Test handling of malformed tool calls from the LLM"""
    # Mock LLM to return an invalid tool call (missing required arguments)
    invalid_tool_call = MagicMock()
    invalid_tool_call.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": "{}"  # Missing required 'path' argument
                        }
                    }
                ]
            }
        )
    ]
    
    # Second response is normal
    normal_response = MagicMock()
    normal_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": "I'll try again with a valid request."
            }
        )
    ]
    
    mock_litellm.side_effect = [invalid_tool_call, normal_response]
    
    # Run the agent with tool error handling
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Read a file please")
    
    # Check result and error handling
    assert result == "I'll try again with a valid request."
    
    # Check that error was logged
    mock_print.assert_any_call("[bold red]Error executing tool 'read_file'[/bold red]")
    
    # Check that error was sent back to LLM in the message
    second_call_args = mock_litellm.call_args_list[1][1]["messages"]
    tool_response_msg = [msg for msg in second_call_args if msg.get("role") == "tool"]
    assert len(tool_response_msg) == 1
    assert "Error" in tool_response_msg[0]["content"]
    assert "Missing required argument: path" in tool_response_msg[0]["content"] or "required parameter" in tool_response_msg[0]["content"].lower()


def test_agent_unknown_tool_call(agent_with_mock_config, mock_litellm):
    """Test handling of unknown tool calls from the LLM"""
    # Mock LLM to call a non-existent tool
    unknown_tool_call = MagicMock()
    unknown_tool_call.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "nonexistent_tool",
                            "arguments": "{}"
                        }
                    }
                ]
            }
        )
    ]
    
    # Second response is normal
    normal_response = MagicMock()
    normal_response.choices = [
        MagicMock(
            message={
                "role": "assistant",
                "content": "I see the tool doesn't exist."
            }
        )
    ]
    
    mock_litellm.side_effect = [unknown_tool_call, normal_response]
    
    # Run the agent
    with patch("code_agent.agent.agent.print") as mock_print:
        result = agent_with_mock_config.run_turn("Use a tool")
    
    # Check result and error handling
    assert result == "I see the tool doesn't exist."
    
    # Check that error was logged
    mock_print.assert_any_call("[bold red]Unknown tool 'nonexistent_tool' requested by LLM[/bold red]")
    
    # Check that error was sent back to LLM in the message
    second_call_args = mock_litellm.call_args_list[1][1]["messages"]
    tool_response_msg = [msg for msg in second_call_args if msg.get("role") == "tool"]
    assert len(tool_response_msg) == 1
    assert "Error" in tool_response_msg[0]["content"]
    assert "Unknown tool" in tool_response_msg[0]["content"] 