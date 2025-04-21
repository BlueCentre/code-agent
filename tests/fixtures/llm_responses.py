"""
Mock LLM response fixtures for testing LiteLLM integration.

This module provides standardized mock responses that simulate what would be
returned by various LLM providers via the LiteLLM library.
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


def create_mock_tool_call(name: str, args: Dict[str, Any], call_id: str = "call_123") -> MagicMock:
    """Creates a mock tool call object with the expected structure."""
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.type = "function"

    # Create the function object
    function = MagicMock()
    function.name = name
    function.arguments = json.dumps(args)

    # Attach function to tool call
    tool_call.function = function

    return tool_call


# --- Simple text responses ---


def create_text_response(text: str) -> MagicMock:
    """Create a simple text response with no tool calls."""
    # Create message with content but no tool calls
    message = MagicMock()
    message.content = text
    message.tool_calls = None

    # Create choice with the message
    choice = MagicMock()
    choice.message = message

    # Create response with the choice
    response = MagicMock()
    response.choices = [choice]

    return response


# Common response shortcuts
DEFAULT_TEXT_RESPONSE = create_text_response("This is a default response.")
EMPTY_RESPONSE = create_text_response("")
ERROR_RESPONSE = create_text_response("I encountered an error processing your request.")


# --- Tool call responses ---


def create_tool_call_response(tool_name: str, tool_args: Dict[str, Any], call_id: str = "call_123", content: Optional[str] = None) -> MagicMock:
    """Create a response with a single tool call."""
    # Create message with tool call
    message = MagicMock()
    message.content = content

    # Create the tool call
    tool_call = create_mock_tool_call(tool_name, tool_args, call_id)
    message.tool_calls = [tool_call]

    # Create choice with the message
    choice = MagicMock()
    choice.message = message

    # Create response with the choice
    response = MagicMock()
    response.choices = [choice]

    return response


def create_multi_tool_call_response(tool_calls: List[Dict[str, Any]], content: Optional[str] = None) -> MagicMock:
    """Create a response with multiple tool calls."""
    # Create message with multiple tool calls
    message = MagicMock()
    message.content = content

    # Create mock tool calls
    mock_tool_calls = []
    for i, call in enumerate(tool_calls):
        call_id = call.get("id", f"call_{i}")
        tool_call = create_mock_tool_call(name=call["name"], args=call["args"], call_id=call_id)
        mock_tool_calls.append(tool_call)

    message.tool_calls = mock_tool_calls

    # Create choice with the message
    choice = MagicMock()
    choice.message = message

    # Create response with the choice
    response = MagicMock()
    response.choices = [choice]

    return response


# Common tool call response shortcuts
READ_FILE_TOOL_CALL = create_tool_call_response(tool_name="read_file", tool_args={"path": "example.py"}, content="I need to check the contents of example.py")

EDIT_FILE_TOOL_CALL = create_tool_call_response(
    tool_name="apply_edit",
    tool_args={"target_file": "example.py", "code_edit": "def new_function():\n    return 'Hello, World!'"},
    content="I'll add a new function to example.py",
)

RUN_COMMAND_TOOL_CALL = create_tool_call_response(
    tool_name="run_native_command", tool_args={"command": "ls -la"}, content="Let me check the directory contents"
)

SEQUENTIAL_TOOL_CALLS = [
    # First call - read a file
    create_tool_call_response(
        tool_name="read_file",
        tool_args={"path": "example.py"},
    ),
    # Second call - run a command
    create_tool_call_response(
        tool_name="run_native_command",
        tool_args={"command": "ls -la"},
    ),
    # Final response after tool calls
    create_text_response("I've analyzed the file and directory."),
]

PARALLEL_TOOL_CALLS = create_multi_tool_call_response(
    tool_calls=[{"name": "read_file", "args": {"path": "example.py"}}, {"name": "run_native_command", "args": {"command": "ls -la"}}],
    content="I need to gather information from multiple sources.",
)


# --- Function to patch litellm.completion ---


def patch_litellm_completion(mocker, responses):
    """
    Patch litellm.completion to return the provided mock responses in sequence.

    Args:
        mocker: The pytest-mock fixture
        responses: A single response or list of response objects to return in sequence

    Returns:
        The mock object for litellm.completion
    """
    mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")

    # Handle both single response and list of responses
    if isinstance(responses, list):
        mock_completion.side_effect = responses
    else:
        mock_completion.return_value = responses

    return mock_completion


def patch_litellm_with_exception(mocker, exception: Exception):
    """
    Patch litellm.completion to raise the specified exception.

    Args:
        mocker: The pytest-mock fixture
        exception: The exception to raise

    Returns:
        The mock object for litellm.completion
    """
    mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
    mock_completion.side_effect = exception
    return mock_completion
