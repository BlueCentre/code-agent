"""
Tests for agent.py to improve coverage.

These tests specifically target the code_agent.agent.agent module.
"""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from code_agent.agent.agent import CodeAgent

# Define role constants since they're not in the module
class Role:
    """Role constants for messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        config = MagicMock()
        config.default_model = "gpt-4"
        config.api_keys = MagicMock()
        config.api_keys.openai = "test-key"
        config.verbosity = 1
        mock_get_config.return_value = config
        yield config


@pytest.fixture
def mock_chat_completion():
    """Create a mock for chat completion."""
    with patch("code_agent.agent.agent.litellm.acompletion") as mock_acompletion:
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message = MagicMock()
        mock_chat_response.choices[0].message.content = "This is a mock response."
        mock_acompletion.return_value = mock_chat_response
        yield mock_acompletion


@pytest.fixture
def agent(mock_config, mock_chat_completion):
    """Create a CodeAgent instance for testing."""
    agent = CodeAgent(
        verbosity=mock_config.verbosity,
    )
    return agent


# Basic functionality tests
def test_init(agent):
    """Test agent initialization."""
    assert agent.verbosity == 1
    assert len(agent.messages) == 0


def test_add_user_message(agent):
    """Test adding a user message."""
    agent.add_user_message("Hello agent")
    assert len(agent.messages) == 1
    assert agent.messages[0]["role"] == "user"
    assert agent.messages[0]["content"] == "Hello agent"


def test_add_system_message(agent):
    """Test adding a system message."""
    agent.add_system_message("You are a helpful assistant")
    assert len(agent.messages) == 1
    assert agent.messages[0]["role"] == "system"
    assert agent.messages[0]["content"] == "You are a helpful assistant"


def test_add_assistant_message(agent):
    """Test adding an assistant message."""
    agent.add_assistant_message("I'm here to help")
    assert len(agent.messages) == 1
    assert agent.messages[0]["role"] == "assistant"
    assert agent.messages[0]["content"] == "I'm here to help"


def test_clear_messages(agent):
    """Test clearing messages."""
    agent.add_user_message("Hello")
    agent.add_assistant_message("Hi")
    assert len(agent.messages) == 2
    
    agent.clear_messages()
    assert len(agent.messages) == 0


def test_set_verbosity(agent):
    """Test setting verbosity level."""
    assert agent.verbosity == 1
    
    agent.set_verbosity(2)
    assert agent.verbosity == 2


@pytest.mark.asyncio
async def test_run_turn_success(agent, mock_chat_completion):
    """Test running a turn successfully."""
    agent.add_user_message("What is 2+2?")
    
    mock_chat_completion.return_value.choices[0].message.content = "4"
    
    response = await agent.run_turn("What is 2+2?")
    assert response == "4"


@pytest.mark.asyncio
async def test_run_turn_json_response(agent, mock_chat_completion):
    """Test running a turn with JSON response."""
    agent.add_user_message("Give me a JSON response")
    
    # Create a mock JSON response
    json_content = json.dumps({"answer": "This is JSON", "code": 200})
    mock_chat_completion.return_value.choices[0].message.content = json_content
    
    response = await agent.run_turn("Give me a JSON response")
    assert response == json_content


@pytest.mark.asyncio
async def test_run_turn_error_handling(agent, mock_chat_completion):
    """Test error handling during run_turn."""
    agent.add_user_message("Trigger an error")
    
    # Simulate an API error
    mock_chat_completion.side_effect = Exception("API Error")
    
    response = await agent.run_turn("Trigger an error")
    assert "Error" in response
    assert "API Error" in response


@pytest.mark.asyncio
async def test_run_turn_with_function_calling(agent, mock_chat_completion):
    """Test run_turn with function calling enabled."""
    agent.add_user_message("Call a function")
    
    # Mock response with function call
    tool_call_response = {
        "id": "response-id",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call-id",
                    "type": "function",
                    "function": {
                        "name": "test_function",
                        "arguments": "{\"arg1\": \"value1\"}"
                    }
                }]
            }
        }]
    }
    
    mock_chat_completion.return_value = MagicMock(**tool_call_response)
    
    with patch.object(agent, "_execute_function_calls") as mock_execute:
        mock_execute.return_value = "Function result"
        response = await agent.run_turn("Call a function", use_tools=True, tools=[{"name": "test_function"}])
        
        assert response == "Function result"
        mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_execute_function_calls(agent):
    """Test executing function calls."""
    function_calls = [{
        "id": "call-id",
        "type": "function",
        "function": {
            "name": "test_function",
            "arguments": "{\"arg1\": \"value1\"}"
        }
    }]
    
    # Mock the function registry
    test_function = MagicMock(return_value="Function output")
    
    with patch.dict(agent.tool_registry, {"test_function": test_function}):
        result = await agent._execute_function_calls(function_calls)
        
        assert "Function output" in result
        test_function.assert_called_once_with(arg1="value1")


@pytest.mark.asyncio
async def test_execute_function_error_handling(agent):
    """Test error handling in function execution."""
    function_calls = [{
        "id": "call-id",
        "type": "function",
        "function": {
            "name": "test_function",
            "arguments": "{\"arg1\": \"value1\"}"
        }
    }]
    
    # Mock function that raises an exception
    test_function = MagicMock(side_effect=Exception("Function error"))
    
    with patch.dict(agent.tool_registry, {"test_function": test_function}):
        result = await agent._execute_function_calls(function_calls)
        
        assert "Error" in result
        assert "Function error" in result 