"""
Tests for LLM interaction with mocked responses and tool calls.

This file focuses on comprehensive testing of the interaction between the agent and
LLM services, with a focus on tool calls and response handling using detailed mocks.
"""

import json
from unittest.mock import MagicMock, patch

import litellm
import pytest

from code_agent.agent.agent import CodeAgent
from code_agent.config import ApiKeys, SettingsConfig
from tests.fixtures.llm_responses import (
    create_text_response,
    create_tool_call_response,
    patch_litellm_completion,
    patch_litellm_with_exception,
)

# --- Test Fixtures ---


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="mock-openai-key",
            anthropic="mock-anthropic-key",
            groq="mock-groq-key",
            ai_studio="mock-ai-studio-key",
        ),
        native_command_allowlist=["ls", "pwd", "find"],
        auto_approve_edits=False,
        auto_approve_native_commands=False,
    )


@pytest.fixture
def agent(mock_config):
    """Create an agent with mocked configuration."""
    with patch("code_agent.agent.agent.get_config", return_value=mock_config):
        yield CodeAgent()


# --- Basic Functionality Tests ---


def test_history_management(agent):
    """Test that the agent correctly manages conversation history."""
    # Add messages of different types
    agent.add_user_message("Hello")
    agent.add_system_message("System instruction")
    agent.add_assistant_message("Hello, how can I help?")

    # Check that messages were added correctly
    assert len(agent.history) == 3
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Hello"
    assert agent.history[1]["role"] == "system"
    assert agent.history[1]["content"] == "System instruction"
    assert agent.history[2]["role"] == "assistant"
    assert agent.history[2]["content"] == "Hello, how can I help?"

    # Test clear_messages
    agent.clear_messages()
    assert len(agent.history) == 0


def test_verbosity_setting(agent):
    """Test that verbosity levels are properly set."""
    # Test default verbosity
    assert agent.verbosity == 1

    # Test setting verbosity to 0
    agent.set_verbosity(0)
    assert agent.verbosity == 0

    # Test setting verbosity to 2
    agent.set_verbosity(2)
    assert agent.verbosity == 2

    # Test clamping values outside the range
    agent.set_verbosity(-1)
    assert agent.verbosity == 0  # Should clamp to 0

    agent.set_verbosity(3)
    assert agent.verbosity == 2  # Should clamp to 2


def test_model_string_formatting(agent):
    """Test model string formatting for different providers."""
    # Test OpenAI model string
    model_string = agent._get_model_string("openai", "gpt-4")
    assert model_string == "gpt-4"

    # Test Google AI Studio model string
    model_string = agent._get_model_string("ai_studio", "gemini-1.5-pro")
    assert model_string == "gemini-1.5-pro"

    # Test Anthropic model string
    model_string = agent._get_model_string("anthropic", "claude-3-opus")
    assert model_string == "anthropic/claude-3-opus"

    # Test other provider model string
    model_string = agent._get_model_string("groq", "llama3-70b-8192")
    assert model_string == "groq/llama3-70b-8192"

    # Test using default provider and model
    with patch.object(agent.config, "default_provider", "openai"):
        with patch.object(agent.config, "default_model", "gpt-3.5-turbo"):
            model_string = agent._get_model_string(None, None)
            assert model_string == "gpt-3.5-turbo"


def test_api_base_selection(agent):
    """Test API base selection for different providers."""
    # All providers should return None as LiteLLM handles API base URLs internally
    api_base = agent._get_api_base("openai")
    assert api_base is None

    api_base = agent._get_api_base("ai_studio")
    assert api_base is None

    api_base = agent._get_api_base("anthropic")
    assert api_base is None


# --- Comprehensive Test Cases ---


def test_text_only_response(agent, mocker):
    """Test that the agent correctly handles a simple text response."""
    # Create a text-only response
    expected_response = "This is a simple text response without any tool calls."
    mock_resp = create_text_response(expected_response)

    # Patch litellm to return our mock response
    patch_litellm_completion(mocker, mock_resp)

    # Run the agent with a test prompt
    result = agent.run_turn("Hello, I need help")

    # Verify the response matches what we expected
    assert result == expected_response

    # Verify history was updated correctly
    assert len(agent.history) == 2
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Hello, I need help"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == expected_response


def test_single_tool_call_read_file(agent, mocker):
    """Test agent handling a single tool call to read a file."""
    # Create responses for the interaction flow
    tool_response = create_tool_call_response(tool_name="read_file", tool_args={"path": "test.py"}, content="Let me check the file content")
    final_response = create_text_response("The file contains a Python function.")

    # Patch litellm to return our sequence of responses
    patch_litellm_completion(mocker, [tool_response, final_response])

    # Mock the read_file function to return a predefined result
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "def test_function():\n    return True"

    # Run the agent
    result = agent.run_turn("What's in the test.py file?")

    # Verify the tool was called correctly
    mock_read_file.assert_called_once_with(path="test.py")

    # Verify the final result
    assert result == "The file contains a Python function."


def test_single_tool_call_apply_edit(agent, mocker):
    """Test agent handling a single tool call to edit a file."""
    # Define the edit content
    edit_content = "def new_function():\n    return 'Hello, World!'"

    # Create responses for the interaction flow
    tool_response = create_tool_call_response(
        tool_name="apply_edit",
        tool_args={"target_file": "example.py", "code_edit": edit_content},
        content="I'll add a new function to the file",
    )
    final_response = create_text_response("I've added the new function successfully.")

    # Patch litellm to return our sequence of responses
    patch_litellm_completion(mocker, [tool_response, final_response])

    # Mock the apply_edit function to return a success message
    mock_apply_edit = mocker.patch("code_agent.agent.agent.apply_edit")
    mock_apply_edit.return_value = "Edit applied successfully."

    # Run the agent
    result = agent.run_turn("Add a hello world function to example.py")

    # Verify the tool was called correctly
    mock_apply_edit.assert_called_once_with(target_file="example.py", code_edit=edit_content)

    # Verify the final result
    assert result == "I've added the new function successfully."


def test_single_tool_call_run_command(agent, mocker):
    """Test agent handling a single tool call to run a native command."""
    # Create responses for the interaction flow
    tool_response = create_tool_call_response(
        tool_name="run_native_command",
        tool_args={"command": "find . -name '*.py'"},
        content="Let me search for Python files",
    )
    final_response = create_text_response("I found 3 Python files in the directory.")

    # Patch litellm to return our sequence of responses
    patch_litellm_completion(mocker, [tool_response, final_response])

    # Mock the run_native_command function to return a predefined result
    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "./test.py\n./example.py\n./main.py"

    # Run the agent
    result = agent.run_turn("Find all Python files in the directory")

    # Verify the tool was called correctly
    mock_run_command.assert_called_once_with(command="find . -name '*.py'")

    # Verify the final result
    assert result == "I found 3 Python files in the directory."


def test_multiple_sequential_tool_calls(agent, mocker):
    """Test agent handling multiple tool calls in sequence."""
    # Create a sequence of tool calls and responses
    first_tool_call = create_tool_call_response(tool_name="read_file", tool_args={"path": "main.py"}, content="First, let me check the main file")

    second_tool_call = create_tool_call_response(
        tool_name="run_native_command",
        tool_args={"command": "ls -la"},
        content="Now, let me check the directory contents",
    )

    final_response = create_text_response("Based on my analysis of the files, your project has 3 Python modules.")

    # Patch litellm to return our sequence of responses
    patch_litellm_completion(mocker, [first_tool_call, second_tool_call, final_response])

    # Mock the tool functions
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "def main():\n    print('Hello world')"

    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "main.py\nutils.py\nconfig.py"

    # Run the agent
    result = agent.run_turn("Analyze my Python project")

    # Verify the tools were called in the correct order
    assert mock_read_file.call_count == 1
    assert mock_run_command.call_count == 1
    mock_read_file.assert_called_with(path="main.py")
    mock_run_command.assert_called_with(command="ls -la")

    # Verify the final result
    assert result == "Based on my analysis of the files, your project has 3 Python modules."


def test_parallel_tool_calls(agent, mocker):
    """Test agent handling multiple parallel tool calls in a single response."""
    # Create a mock message with multiple tool calls
    message = MagicMock()
    message.content = "I need to collect information from multiple sources"

    # Create two tool calls
    tool_call_1 = MagicMock()
    tool_call_1.id = "call_1"
    tool_call_1.type = "function"
    tool_call_1.function.name = "read_file"
    tool_call_1.function.arguments = json.dumps({"path": "config.py"})

    tool_call_2 = MagicMock()
    tool_call_2.id = "call_2"
    tool_call_2.type = "function"
    tool_call_2.function.name = "run_native_command"
    tool_call_2.function.arguments = json.dumps({"command": "pwd"})

    # Attach tool calls to the message
    message.tool_calls = [tool_call_1, tool_call_2]

    # Create a response with the parallel tool calls
    parallel_response = MagicMock()
    parallel_response.choices = [MagicMock()]
    parallel_response.choices[0].message = message

    # Create final response after tool calls
    final_response = create_text_response("Analysis complete. Configuration is in /home/user/project.")

    # Patch litellm to return our responses
    patch_litellm_completion(mocker, [parallel_response, final_response])

    # Mock the tool functions
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.return_value = "API_KEY = 'test123'"

    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "/home/user/project"

    # Run the agent
    result = agent.run_turn("Analyze my project configuration")

    # Verify both tools were called
    mock_read_file.assert_called_once_with(path="config.py")
    mock_run_command.assert_called_once_with(command="pwd")

    # Verify the final result
    assert result == "Analysis complete. Configuration is in /home/user/project."


def test_malformed_tool_call_arguments(agent, mocker):
    """Test agent handling malformed JSON in tool call arguments."""
    # Create a tool call with invalid JSON in arguments
    message = MagicMock()
    message.content = "Let me check that file"

    tool_call = MagicMock()
    tool_call.id = "invalid_call"
    tool_call.type = "function"
    tool_call.function.name = "read_file"
    tool_call.function.arguments = "{path: broken json}"  # Invalid JSON

    message.tool_calls = [tool_call]

    invalid_response = MagicMock()
    invalid_response.choices = [MagicMock()]
    invalid_response.choices[0].message = message

    # Create a recovery response
    recovery_response = create_text_response("I apologize for the error. Let me try again.")

    # Patch litellm to return our responses
    patch_litellm_completion(mocker, [invalid_response, recovery_response])

    # Mock the print function to check error logging
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Run the agent
    result = agent.run_turn("Check the content of test.py")

    # Verify error was logged
    error_logged = False
    for call_args in mock_print.call_args_list:
        if "Error parsing function arguments" in str(call_args):
            error_logged = True
            break

    assert error_logged, "Error about malformed JSON should have been logged"

    # Verify we got the recovery response
    assert result == "I apologize for the error. Let me try again."


def test_unknown_tool_call(agent, mocker):
    """Test agent handling a request for an unknown tool."""
    # Create a tool call for a non-existent tool
    message = MagicMock()
    message.content = "Let me use a special tool"

    tool_call = MagicMock()
    tool_call.id = "unknown_call"
    tool_call.type = "function"
    tool_call.function.name = "non_existent_tool"
    tool_call.function.arguments = json.dumps({"param": "value"})

    message.tool_calls = [tool_call]

    unknown_tool_response = MagicMock()
    unknown_tool_response.choices = [MagicMock()]
    unknown_tool_response.choices[0].message = message

    # Create a recovery response
    recovery_response = create_text_response("I apologize for the confusion. Let me use available tools instead.")

    # Patch litellm to return our responses
    patch_litellm_completion(mocker, [unknown_tool_response, recovery_response])

    # Mock the print function to check error logging
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Run the agent
    result = agent.run_turn("Use a special tool to analyze the code")

    # Verify error was logged
    error_logged = False
    for call_args in mock_print.call_args_list:
        if "Unknown tool" in str(call_args):
            error_logged = True
            break

    assert error_logged, "Error about unknown tool should have been logged"

    # Verify we got the recovery response
    assert result == "I apologize for the confusion. Let me use available tools instead."


def test_tool_execution_exception(agent, mocker):
    """Test agent handling an exception during tool execution."""
    # Create a tool call that will raise an exception
    tool_response = create_tool_call_response(tool_name="read_file", tool_args={"path": "missing_file.py"}, content="Let me check this file")

    recovery_response = create_text_response("I couldn't find the file you mentioned.")

    # Patch litellm to return our responses
    patch_litellm_completion(mocker, [tool_response, recovery_response])

    # Mock read_file to raise an exception
    mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
    mock_read_file.side_effect = Exception("File not found")

    # Mock the print function to check error logging
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Run the agent
    result = agent.run_turn("Check the content of missing_file.py")

    # Verify error was logged
    error_logged = False
    for call_args in mock_print.call_args_list:
        if "Error executing" in str(call_args):
            error_logged = True
            break

    assert error_logged, "Error during tool execution should have been logged"

    # Verify we got the recovery response
    assert result == "I couldn't find the file you mentioned."


def test_max_tool_calls_limit(agent, mocker):
    """Test that the agent respects the maximum tool call limit."""
    # Create a recursive tool call that would repeat forever
    repeating_tool_call = create_tool_call_response(tool_name="run_native_command", tool_args={"command": "echo 'hello'"}, content="Let me run this command")

    # Patch litellm to always return the same response (creating an infinite loop)
    patch_litellm_completion(mocker, repeating_tool_call)

    # Mock the run_native_command function
    mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
    mock_run_command.return_value = "hello"

    # Mock the console.print function in progress_indicators which is used by operation_warning
    mock_console_print = mocker.patch("code_agent.tools.progress_indicators.console.print")

    # Run the agent - it should eventually stop due to max_tool_calls
    agent.run_turn("Run a command repeatedly")

    # Verify warning about max tool calls was logged
    max_calls_warning = False
    for call_args in mock_console_print.call_args_list:
        if "Maximum tool call limit reached" in str(call_args):
            max_calls_warning = True
            break

    assert max_calls_warning, "Warning about maximum tool calls should have been logged"

    # Verify the tool was called multiple times but stopped eventually
    assert mock_run_command.call_count > 1
    assert mock_run_command.call_count <= 20  # default max_tool_calls is 20


def test_litellm_exception(agent, mocker):
    """Test agent handling exceptions from the LiteLLM library."""
    # Create an exception to be raised by litellm
    api_error = litellm.exceptions.APIError(status_code=500, message="Internal server error", request="test request", llm_provider="openai", model="gpt-4")

    # Patch litellm to raise the exception
    patch_litellm_with_exception(mocker, api_error)

    # Mock the print function to check error logging
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Run the agent
    result = agent.run_turn("Generate some Python code")

    # Verify error was logged
    error_logged = False
    for call_args in mock_print.call_args_list:
        if "Error during agent execution" in str(call_args):
            error_logged = True
            break

    assert error_logged, "Error during LiteLLM execution should have been logged"

    # Result should be None on critical errors
    assert result is None


def test_provider_specific_parameters(agent, mocker):
    """Test that provider-specific parameters are correctly applied."""
    # Create a simple response
    mock_resp = create_text_response("This is a test response")

    # Patch litellm.completion to capture call parameters
    mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
    mock_completion.return_value = mock_resp

    # Run with custom provider settings
    agent.run_turn("Test prompt", provider="ai_studio", model="gemini-1.5-pro")

    # Check that provider-specific parameters were set
    call_args = mock_completion.call_args[1]
    assert call_args["model"] == "gemini-1.5-pro"
    assert call_args["custom_llm_provider"] == "gemini"


# --- Error Handling and Edge Cases ---


def test_run_turn_missing_api_key(agent, mocker):
    """Test handling missing API key in run_turn."""
    # Mock config to have a missing API key
    with patch.object(agent.config.api_keys, "openai", None):
        # Mock print to verify output
        mock_print = mocker.patch("code_agent.agent.agent.print")

        # Run the agent
        result = agent.run_turn("Tell me about this project")

        # Verify error message about API key
        api_key_error = False
        for call_args in mock_print.call_args_list:
            if "Error: No API key found for provider" in str(call_args):
                api_key_error = True
                break

        assert api_key_error, "Error about missing API key should have been logged"

        # Result should be a fallback response mentioning API key
        assert result is not None
        assert "API key" in result.lower() or "Sorry" in result


def test_fallback_command_handling(agent, mocker):
    """Test the fallback command handling when API key is missing."""
    # Mock the API key to be missing
    with patch.object(agent.config.api_keys, "openai", None):
        # Mock run_native_command
        mock_run_command = mocker.patch("code_agent.agent.agent.run_native_command")
        mock_run_command.return_value = "/home/user/project"

        # Test with different basic command types
        pwd_result = agent.run_turn("What is the current directory?")
        assert "current working directory" in pwd_result.lower()
        mock_run_command.assert_called_with("pwd")

        # Reset and test ls command
        mock_run_command.reset_mock()
        mock_run_command.return_value = "file1.py\nfile2.py"

        ls_result = agent.run_turn("List files")
        assert "files in the current directory" in ls_result.lower()
        mock_run_command.assert_called_with("ls -la")

        # Reset and test python files command
        mock_run_command.reset_mock()
        mock_run_command.return_value = "./file1.py\n./file2.py"

        python_result = agent.run_turn("Show me Python files in the src directory")
        assert "python files in" in python_result.lower()
        assert "find" in mock_run_command.call_args[0][0]


def test_model_not_found_error_handling(agent, mocker):
    """Test handling of model not found errors."""
    # Create a model not found exception
    model_error = litellm.exceptions.NotFoundError(message="Model 'wrong-model' not found", model="wrong-model", llm_provider="openai")

    # Patch litellm to raise the exception
    patch_litellm_with_exception(mocker, model_error)

    # Mock print to verify error messages
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Mock _handle_model_not_found_error to ensure it returns a consistent response
    mock_handle_model = mocker.patch("code_agent.agent.agent.CodeAgent._handle_model_not_found_error")
    mock_handle_model.return_value = "Cannot list available models. Try installing google-generativeai package."

    # Run the agent
    result = agent.run_turn("Test with wrong model")

    # Verify error message about model not found was logged
    model_not_found_error = False
    for call_args in mock_print.call_args_list:
        if "is not found" in str(call_args).lower() or "notfounderror" in str(call_args).lower():
            model_not_found_error = True
            break

    assert model_not_found_error, "Error about model not found should have been logged"

    # Verify the handler was called
    assert mock_handle_model.called, "Model not found handler should have been called"

    # Result should contain the mocked response text
    assert result == "Cannot list available models. Try installing google-generativeai package."


def test_rate_limit_error_handling(agent, mocker):
    """Test handling of rate limit errors."""
    # Create a rate limit exception
    rate_limit_error = litellm.exceptions.RateLimitError(message="Rate limit exceeded", model="gpt-4", llm_provider="openai")

    # Patch litellm to raise the exception
    patch_litellm_with_exception(mocker, rate_limit_error)

    # Mock the print function
    mock_print = mocker.patch("code_agent.agent.agent.print")

    # Run the agent
    result = agent.run_turn("Generate a complex response")

    # Verify error message about rate limit
    rate_limit_message = False
    for call_args in mock_print.call_args_list:
        if "rate limit" in str(call_args).lower():
            rate_limit_message = True
            break

    assert rate_limit_message, "Message about rate limit should have been logged"

    # Result should be None due to error
    assert result is None
