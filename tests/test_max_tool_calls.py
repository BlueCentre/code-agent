"""
Tests for maximum tool call limits in the agent.

These tests verify that the agent correctly handles the maximum
number of tool calls in a conversation turn.
"""

import pytest
from unittest.mock import patch, MagicMock

from code_agent.agent.agent import CodeAgent
from code_agent.config import SettingsConfig
from code_agent.config.config import ApiKeys


@pytest.fixture
def mock_config():
    """Mock config for agent tests."""
    config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4",
        api_keys=ApiKeys(
            openai="test-openai-key"
        ),
        rules=["Be helpful"],
        auto_approve_edits=False,
        auto_approve_native_commands=False
    )
    return config


@pytest.fixture
def tool_call_response_chain(mocker):
    """Create a chain of tool call responses that will exceed the max calls limit."""
    # Create a series of responses that always request another tool call
    responses = []
    
    # Generate 6 tool call responses (exceeding the default max of 5)
    for i in range(6):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message = MagicMock()
        
        # Create a tool call that reads a file
        tool_call = MagicMock()
        tool_call.id = f"call_{i}"
        tool_call.type = "function"
        tool_call.function = MagicMock()
        tool_call.function.name = "read_file"
        tool_call.function.arguments = f'{{"path": "test_file_{i}.txt"}}'
        
        response.choices[0].message.content = None
        response.choices[0].message.tool_calls = [tool_call]
        
        responses.append(response)
    
    # Final response after max tool calls is reached
    final_response = MagicMock()
    final_response.choices = [MagicMock()]
    final_response.choices[0].message = MagicMock()
    final_response.choices[0].message.content = "Max tool calls reached"
    final_response.choices[0].message.tool_calls = None
    
    responses.append(final_response)
    
    return responses


def test_agent_enforces_max_tool_calls_limit(mock_config, tool_call_response_chain, mocker):
    """Test that the agent enforces the maximum number of tool calls."""
    # Patch the get_config function to return our mock
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config
        
        # Patch litellm.completion to return our chain of responses
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = tool_call_response_chain
        
        # Patch the read_file tool to return a simple response
        mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
        mock_read_file.return_value = "File content"
        
        # Create agent and run a turn that will trigger the tool call chain
        agent = CodeAgent()
        result = agent.run_turn("Read multiple files")
        
        # Verify that we hit exactly 5 tool calls (the default max)
        assert mock_read_file.call_count == 5
        
        # Verify that the completion was called 5 times:
        # 1 initial request + 4 tool responses (5th tool call doesn't trigger completion)
        assert mock_completion.call_count == 5
        
        # Check if the result indicates an issue with tool calls
        assert result is not None
        # The agent should return a default message about not getting a clear response
        assert "No clear response was generated" in result


def test_agent_completes_before_max_tool_calls(mock_config, mocker):
    """Test that the agent can complete work before hitting max tool calls."""
    # Patch the get_config function to return our mock
    with patch("code_agent.agent.agent.get_config") as mock_get_config:
        mock_get_config.return_value = mock_config
        
        # Create a sequence of responses: tool call -> tool call -> final response
        responses = []
        
        # First tool call
        response1 = MagicMock()
        response1.choices = [MagicMock()]
        response1.choices[0].message = MagicMock()
        tool_call1 = MagicMock()
        tool_call1.id = "call_1"
        tool_call1.type = "function"
        tool_call1.function = MagicMock()
        tool_call1.function.name = "read_file"
        tool_call1.function.arguments = '{"path": "file1.txt"}'
        response1.choices[0].message.content = None
        response1.choices[0].message.tool_calls = [tool_call1]
        responses.append(response1)
        
        # Second tool call
        response2 = MagicMock()
        response2.choices = [MagicMock()]
        response2.choices[0].message = MagicMock()
        tool_call2 = MagicMock()
        tool_call2.id = "call_2"
        tool_call2.type = "function"
        tool_call2.function = MagicMock()
        tool_call2.function.name = "read_file"
        tool_call2.function.arguments = '{"path": "file2.txt"}'
        response2.choices[0].message.content = None
        response2.choices[0].message.tool_calls = [tool_call2]
        responses.append(response2)
        
        # Final response with content
        final_response = MagicMock()
        final_response.choices = [MagicMock()]
        final_response.choices[0].message = MagicMock()
        final_response.choices[0].message.content = "Completed successfully"
        final_response.choices[0].message.tool_calls = None
        responses.append(final_response)
        
        # Patch litellm.completion to return our sequence
        mock_completion = mocker.patch("code_agent.agent.agent.litellm.completion")
        mock_completion.side_effect = responses
        
        # Patch the read_file tool to return a simple response
        mock_read_file = mocker.patch("code_agent.agent.agent.read_file")
        mock_read_file.return_value = "File content"
        
        # Create agent and run a turn
        agent = CodeAgent()
        result = agent.run_turn("Read two files")
        
        # Verify we made exactly 2 tool calls
        assert mock_read_file.call_count == 2
        
        # Verify that the completion was called 3 times:
        # 1 initial request + 2 tool responses
        assert mock_completion.call_count == 3
        
        # Check the final result
        assert result == "Completed successfully" 