import json
from unittest.mock import MagicMock, patch

import pytest

from code_agent.agent.agent import CodeAgent
from code_agent.config import ApiKeys, SettingsConfig


@pytest.fixture
def mock_config():
    """Mock config for agent tests"""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(openai="mock-key"),
        rules=["Be helpful", "Be concise"],
        native_command_allowlist=["ls", "pwd"],
        auto_approve_edits=False,
        auto_approve_native_commands=False,
    )
    return config


@pytest.fixture
def mock_litellm():
    """Mock litellm.completion for agent tests"""
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
            rules=["Be helpful", "Be concise"],
            native_command_allowlist=["ls", "pwd"],
        )
        mock_get_config.return_value = config
        agent = CodeAgent()
        yield agent


def test_agent_initialization(agent_with_mock_config):
    """Test that the agent initializes with the correct configuration"""
    agent = agent_with_mock_config

    # Check if base instructions contain the rules
    instructions = "\n".join(agent.base_instruction_parts)
    assert "You are a helpful AI assistant" in instructions
    assert "Follow these instructions:" in instructions
    assert "- Be helpful" in instructions
    assert "- Be concise" in instructions

    # Check if tools are properly described
    assert "read_file(path)" in instructions
    assert "apply_edit(target_file, code_edit)" in instructions
    assert "run_native_command(command)" in instructions


def test_model_string_formatting(agent_with_mock_config):
    """Test that model strings are correctly formatted for different providers"""
    agent = agent_with_mock_config

    # Test OpenAI formatting
    model_string = agent._get_model_string("openai", "gpt-4")
    assert model_string == "gpt-4"

    # Test AI Studio formatting
    model_string = agent._get_model_string("ai_studio", "gemini-1.5-pro")
    assert model_string == "vertex_ai/gemini-1.5-pro"

    # Test generic provider formatting
    model_string = agent._get_model_string("anthropic", "claude-3-opus")
    assert model_string == "anthropic/claude-3-opus"


def test_api_base_selection(agent_with_mock_config):
    """Test that the correct API base URL is selected for different providers"""
    agent = agent_with_mock_config

    # AI Studio should have a specific base URL
    api_base = agent._get_api_base("ai_studio")
    assert api_base == "https://api.ai.studio/v1"

    # Other providers should return None to use LiteLLM defaults
    api_base = agent._get_api_base("openai")
    assert api_base is None


def test_agent_run_turn_simple_response(agent_with_mock_config, mock_litellm):
    """Test a simple agent turn with a text response (no tool calls)"""
    agent = agent_with_mock_config

    # Mock the LiteLLM response for a simple text response
    mock_message = MagicMock()
    mock_message.content = "This is a test response"
    mock_message.tool_calls = None  # No tool calls

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    mock_litellm.return_value = mock_response

    # Run the agent
    result = agent.run_turn("Tell me about Python")

    # Check the result
    assert result == "This is a test response"

    # Check that litellm was called with the correct parameters
    mock_litellm.assert_called_once()
    call_args = mock_litellm.call_args[1]
    assert call_args["model"] == "gpt-4"  # Default from the mock config
    assert call_args["api_key"] == "mock-key"
    assert call_args["tools"] is not None
    assert call_args["tool_choice"] == "auto"

    # Check that the messages include the system prompt and user message
    messages = call_args["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Tell me about Python"


def test_agent_run_turn_with_tool_call(agent_with_mock_config, mock_litellm):
    """Test agent handling a tool call for read_file"""
    agent = agent_with_mock_config

    # First response: Agent wants to call read_file
    first_message = MagicMock()
    first_message.content = None

    # Create a tool call object
    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function = MagicMock()
    tool_call.function.name = "read_file"
    tool_call.function.arguments = json.dumps({"path": "test_file.py"})

    first_message.tool_calls = [tool_call]

    tool_call_response = MagicMock()
    tool_call_response.choices = [MagicMock(message=first_message)]

    # Second response: Agent processes the tool result and gives a final answer
    final_message = MagicMock()
    final_message.content = "I've analyzed the file. It contains test code."
    final_message.tool_calls = None

    final_response = MagicMock()
    final_response.choices = [MagicMock(message=final_message)]

    # Setup mock to return different responses on consecutive calls
    mock_litellm.side_effect = [tool_call_response, final_response]

    # Mock the read_file tool to return some content
    with patch("code_agent.agent.agent.read_file") as mock_read_file:
        mock_read_file.return_value = "def test_function():\n    pass"

        # Run the agent
        result = agent.run_turn("Show me the contents of test_file.py")

    # Check the result
    assert result == "I've analyzed the file. It contains test code."

    # Verify litellm was called twice (initial request + after tool call)
    assert mock_litellm.call_count == 2

    # Check the second call has the tool result
    second_call_args = mock_litellm.call_args[1]["messages"]
    assert any(msg.get("role") == "tool" for msg in second_call_args)
    assert any(msg.get("tool_call_id") == "call_123" for msg in second_call_args)


def test_agent_run_turn_multiple_tool_calls(agent_with_mock_config, mock_litellm):
    """Test agent handling multiple consecutive tool calls"""
    agent = agent_with_mock_config

    # First response: Agent wants to call read_file
    first_message = MagicMock()
    first_message.content = None

    first_tool_call = MagicMock()
    first_tool_call.id = "call_1"
    first_tool_call.function = MagicMock()
    first_tool_call.function.name = "read_file"
    first_tool_call.function.arguments = json.dumps({"path": "file1.py"})

    first_message.tool_calls = [first_tool_call]

    first_response = MagicMock()
    first_response.choices = [MagicMock(message=first_message)]

    # Second response: Agent wants to run a command
    second_message = MagicMock()
    second_message.content = None

    second_tool_call = MagicMock()
    second_tool_call.id = "call_2"
    second_tool_call.function = MagicMock()
    second_tool_call.function.name = "run_native_command"
    second_tool_call.function.arguments = json.dumps({"command": "ls -la"})

    second_message.tool_calls = [second_tool_call]

    second_response = MagicMock()
    second_response.choices = [MagicMock(message=second_message)]

    # Final response: Agent gives a conclusion
    final_message = MagicMock()
    final_message.content = "I've examined the file and directory contents."
    final_message.tool_calls = None

    final_response = MagicMock()
    final_response.choices = [MagicMock(message=final_message)]

    # Set up mock to return different responses
    mock_litellm.side_effect = [first_response, second_response, final_response]

    # Mock the tools
    with (
        patch("code_agent.agent.agent.read_file") as mock_read_file,
        patch("code_agent.agent.agent.run_native_command") as mock_run_command,
    ):
        mock_read_file.return_value = "print('hello')"
        mock_run_command.return_value = "file1.py file2.py"

        # Run the agent
        result = agent.run_turn("Analyze my project files")

    # Check the result
    assert result == "I've examined the file and directory contents."

    # Verify litellm was called three times
    assert mock_litellm.call_count == 3

    # Check history - it should only contain the user request and final assistant response
    assert len(agent.history) == 2
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "Analyze my project files"
    assert agent.history[1]["role"] == "assistant"
    assert (
        agent.history[1]["content"] == "I've examined the file and directory contents."
    )


def test_agent_no_api_key_fallback(agent_with_mock_config):
    """Test that the agent falls back to simple command handling when API key is missing"""
    # Create agent with no API key
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = SettingsConfig(
            default_provider="openai",
            default_model="gpt-4",
            api_keys=ApiKeys(openai=None),  # No API key
            native_command_allowlist=["ls", "pwd"],
        )
        mock_get_config.return_value = config
        agent = CodeAgent()

    # Mock the native command tool
    with patch("code_agent.agent.agent.run_native_command") as mock_run_command:
        mock_run_command.return_value = "/home/user/project"

        # Test with a command that should be handled by the fallback
        result = agent.run_turn("What is the current working directory?")

    # Check that it used the fallback handler
    assert "current working directory" in result
    assert mock_run_command.called
    mock_run_command.assert_called_with("pwd")


def test_agent_max_tool_calls_limit(agent_with_mock_config, mock_litellm):
    """Test that the agent respects the maximum tool calls limit"""
    agent = agent_with_mock_config

    # Setup mock to always return a tool call (which would cause infinite loop without the limit)
    message = MagicMock()
    message.content = None

    tool_call = MagicMock()
    tool_call.id = "call_test"
    tool_call.function = MagicMock()
    tool_call.function.name = "read_file"
    tool_call.function.arguments = json.dumps({"path": "test_file.py"})

    message.tool_calls = [tool_call]

    response = MagicMock()
    response.choices = [MagicMock(message=message)]

    # Always return a tool call response
    mock_litellm.return_value = response

    # Mock the read_file tool
    with patch("code_agent.agent.agent.read_file") as mock_read_file:
        mock_read_file.return_value = "mocked file content"

        # Run the agent - it should eventually stop due to the limit
        result = agent.run_turn("Process my files")

    # Check the call count is limited to max_tool_calls (5 by default in agent.py)
    assert mock_litellm.call_count <= 6  # Initial call + max 5 tool calls
    assert mock_read_file.call_count <= 5  # Max 5 tool calls
