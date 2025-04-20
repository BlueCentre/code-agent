"""
Tests for interactions between the agent and LLM services via LiteLLM.

These tests focus on how the agent interacts with the LLM, 
including tool calling sequences, handling of responses, and error conditions.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

import litellm
from litellm.exceptions import BadRequestError, RateLimitError, AuthenticationError

from code_agent.agent.agent import CodeAgent
from code_agent.config import SettingsConfig, ApiKeys

# Import our mock response fixtures
from tests.fixtures.llm_responses import (
    create_text_response,
    create_tool_call_response,
    patch_litellm_completion,
    patch_litellm_with_exception,
    DEFAULT_TEXT_RESPONSE,
    READ_FILE_TOOL_CALL,
    EDIT_FILE_TOOL_CALL,
    RUN_COMMAND_TOOL_CALL,
    SEQUENTIAL_TOOL_CALLS,
    PARALLEL_TOOL_CALLS,
)


# --- Fixtures ---

@pytest.fixture
def mock_config():
    """Mock config for agent tests with all needed API keys."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="mock-openai-key",
            ai_studio="mock-ai-studio-key",
            anthropic="mock-anthropic-key",
            groq="mock-groq-key"
        ),
        rules=["Be helpful", "Write clean code"],
        native_command_allowlist=["ls", "pwd", "cat"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    return config


@pytest.fixture
def agent_with_mock_config(mock_config):
    """Create an agent with a mocked config."""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config
        agent = CodeAgent()
        yield agent


# --- Basic Interaction Tests ---

def test_simple_text_response(agent_with_mock_config, mocker):
    """Test the agent handling a simple text response from the LLM."""
    expected_response = "This is a simple text response."
    mock_resp = create_text_response(expected_response)
    
    # Patch litellm to return our mock response
    patch_litellm_completion(mocker, [mock_resp])
    
    # Run the agent with a simple prompt
    result = agent_with_mock_config.run_turn("Hello, agent!")
    
    # Verify the result matches our mock response
    assert result == expected_response
    
    # Verify the history was updated correctly
    assert len(agent_with_mock_config.history) == 2
    assert agent_with_mock_config.history[0]["role"] == "user"
    assert agent_with_mock_config.history[0]["content"] == "Hello, agent!"
    assert agent_with_mock_config.history[1]["role"] == "assistant"
    assert agent_with_mock_config.history[1]["content"] == expected_response


def test_tool_call_read_file(agent_with_mock_config, mocker):
    """Test the agent handling a tool call to read a file."""
    # Define the sequence: LLM asks to read file -> we return content -> LLM gives final answer
    mock_responses = [
        READ_FILE_TOOL_CALL,
        create_text_response("The file contains: print('hello world')")
    ]
    
    # Patch litellm and the read_file tool
    patch_litellm_completion(mocker, mock_responses)
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "print('hello world')"
    
    # Run the agent
    result = agent_with_mock_config.run_turn("What's in example.py?")
    
    # Verify result and tool was called correctly
    assert "The file contains: print('hello world')" == result
    mock_read_file.assert_called_once_with(path="example.py")


def test_tool_call_apply_edit(agent_with_mock_config, mocker):
    """Test the agent handling a tool call to edit a file."""
    # Define the sequence: LLM asks to edit file -> we confirm edit -> LLM gives final answer
    mock_responses = [
        EDIT_FILE_TOOL_CALL,
        create_text_response("I've added the new function to the file.")
    ]
    
    # Patch litellm and the apply_edit tool
    patch_litellm_completion(mocker, mock_responses)
    mock_apply_edit = mocker.patch("code_agent.agent.agent.apply_edit")
    mock_apply_edit.return_value = "Edit applied successfully."
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Add a hello world function to example.py")
    
    # Verify result and tool was called correctly
    assert "I've added the new function to the file." == result
    mock_apply_edit.assert_called_once()
    args = mock_apply_edit.call_args[1]
    assert args["target_file"] == "example.py"
    assert "def new_function()" in args["code_edit"]


def test_tool_call_run_command(agent_with_mock_config, mocker):
    """Test the agent handling a tool call to run a command."""
    # Define the sequence: LLM asks to run command -> we return output -> LLM gives final answer
    mock_responses = [
        RUN_COMMAND_TOOL_CALL,
        create_text_response("Here's what I found in the directory.")
    ]
    
    # Patch litellm and the run_command tool
    patch_litellm_completion(mocker, mock_responses)
    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "file1.py file2.py"
    
    # Run the agent
    result = agent_with_mock_config.run_turn("List files in the current directory")
    
    # Verify result and tool was called correctly
    assert "Here's what I found in the directory." == result
    mock_run_command.assert_called_once_with(command="ls -la")


# --- Complex Interaction Tests ---

def test_sequential_tool_calls(agent_with_mock_config, mocker):
    """Test the agent handling a sequence of tool calls."""
    # Patch litellm to return our sequence of responses
    patch_litellm_completion(mocker, SEQUENTIAL_TOOL_CALLS)
    
    # Patch both tools that will be called
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "def example():\n    pass"
    
    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "example.py"
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Analyze example.py and list files")
    
    # Verify final result
    assert "I've analyzed the file and directory." == result
    
    # Verify both tools were called in sequence
    assert mock_read_file.call_count == 1
    assert mock_run_command.call_count == 1
    
    # Verify only initial prompt and final result are in history
    assert len(agent_with_mock_config.history) == 2


def test_parallel_tool_calls(agent_with_mock_config, mocker):
    """Test the agent handling parallel tool calls in a single response."""
    # Define the sequence: LLM asks to do multiple things -> we return results -> LLM gives final answer
    mock_responses = [
        PARALLEL_TOOL_CALLS,
        create_text_response("I've gathered all the information.")
    ]
    
    # Patch litellm and the tools
    patch_litellm_completion(mocker, mock_responses)
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "def example():\n    pass"
    
    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "example.py"
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Analyze project structure")
    
    # Verify result and both tools were called
    assert "I've gathered all the information." == result
    assert mock_read_file.call_count == 1
    assert mock_run_command.call_count == 1


# --- Provider-Specific Tests ---

def test_openai_model_string_formatting(agent_with_mock_config):
    """Test that OpenAI model strings are formatted correctly."""
    model_string = agent_with_mock_config._get_model_string("openai", "gpt-4")
    assert model_string == "gpt-4"


def test_ai_studio_model_string_formatting(agent_with_mock_config):
    """Test that AI Studio model strings are formatted correctly."""
    model_string = agent_with_mock_config._get_model_string("ai_studio", "gemini-1.5-pro")
    assert model_string == "vertex_ai/gemini-1.5-pro"


def test_anthropic_model_string_formatting(agent_with_mock_config):
    """Test that Anthropic model strings are formatted correctly."""
    model_string = agent_with_mock_config._get_model_string("anthropic", "claude-3-opus")
    assert model_string == "anthropic/claude-3-opus"


def test_api_base_selection(agent_with_mock_config):
    """Test that the correct API base URL is selected for different providers."""
    api_base = agent_with_mock_config._get_api_base("ai_studio")
    assert api_base == "https://api.ai.studio/v1"
    
    api_base = agent_with_mock_config._get_api_base("openai")
    assert api_base is None


# --- Error Handling Tests ---

def test_connection_error(agent_with_mock_config, mocker):
    """Test handling of connection errors."""
    connection_error = litellm.exceptions.ServiceUnavailableError(
        message="Connection refused",
        model="gpt-4",
        llm_provider="openai"
    )
    
    # Patch litellm to raise the error
    patch_litellm_with_exception(mocker, connection_error)
    
    # Mock print to capture error messages
    mock_print = mocker.patch("code_agent.agent.agent.print")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Hello, agent!")
    
    # Verify error handling
    assert result is None
    mock_print.assert_any_call("[bold red]Error during agent execution (ServiceUnavailableError):[/bold red]")


def test_api_key_error(agent_with_mock_config, mocker):
    """Test handling of invalid API key errors."""
    auth_error = litellm.exceptions.AuthenticationError(
        message="Invalid API key",
        model="gpt-4",
        llm_provider="openai"
    )
    
    # Patch litellm to raise the error
    patch_litellm_with_exception(mocker, auth_error)
    
    # Mock print to capture error messages
    mock_print = mocker.patch("code_agent.agent.agent.print")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Hello, agent!")
    
    # Verify error handling
    assert result is None
    mock_print.assert_any_call("[bold red]Error during agent execution (AuthenticationError):[/bold red]")


def test_rate_limit_error(agent_with_mock_config, mocker):
    """Test handling of rate limit errors."""
    rate_limit_error = litellm.exceptions.RateLimitError(
        message="Rate limit exceeded",
        model="gpt-4",
        llm_provider="openai"
    )
    
    # Patch litellm to raise the error
    patch_litellm_with_exception(mocker, rate_limit_error)
    
    # Mock print to capture error messages
    mock_print = mocker.patch("code_agent.agent.agent.print")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Hello, agent!")
    
    # Verify error handling
    assert result is None
    mock_print.assert_any_call("[bold red]Error during agent execution (RateLimitError):[/bold red]")


def test_context_length_error(agent_with_mock_config, mocker):
    """Test handling of context length exceeded errors."""
    context_error = litellm.exceptions.ContextWindowExceededError(
        message="This model's maximum context length is 8192 tokens. You provided 10000 tokens.",
        model="gpt-4",
        llm_provider="openai"
    )
    
    # Patch litellm to raise the error
    patch_litellm_with_exception(mocker, context_error)
    
    # Mock print to capture error messages
    mock_print = mocker.patch("code_agent.agent.agent.print")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("Hello, agent!" * 1000)  # Long input
    
    # Verify error handling
    assert result is None
    mock_print.assert_any_call("[bold red]Error during agent execution (ContextWindowExceededError):[/bold red]")


# --- Tool Error Tests ---

def test_tool_error_handled_gracefully(agent_with_mock_config, mocker):
    """Test that errors during tool execution are handled gracefully."""
    # Define the sequence: LLM asks to read file -> tool raises error -> LLM handles error
    mock_responses = [
        READ_FILE_TOOL_CALL,
        create_text_response("I couldn't access that file. Let me suggest an alternative.")
    ]
    
    # Patch litellm and make read_file raise an error
    patch_litellm_completion(mocker, mock_responses)
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.side_effect = FileNotFoundError("File not found: example.py")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("What's in example.py?")
    
    # Verify result contains the handled error message
    assert "I couldn't access that file" in result


def test_max_tool_calls_limit(agent_with_mock_config, mocker):
    """Test that the agent enforces the maximum number of tool calls."""
    # Create a sequence of 6 identical tool calls (one more than the limit)
    mock_responses = [READ_FILE_TOOL_CALL] * 6
    
    # Patch litellm and read_file
    patch_litellm_completion(mocker, mock_responses)
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "Content of example.py"
    
    # Mock print to capture warning messages
    mock_print = mocker.patch("code_agent.agent.agent.print")
    
    # Run the agent
    result = agent_with_mock_config.run_turn("What's in example.py?")
    
    # Verify max tool calls warning was printed
    warning_message = f"[yellow]Warning: Maximum tool call limit reached (5)[/yellow]"
    mock_print.assert_any_call(warning_message)
    
    # Verify read_file was called exactly 5 times (the limit)
    assert mock_read_file.call_count == 5 