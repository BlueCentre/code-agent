import json
from unittest.mock import MagicMock, patch

import pytest

from code_agent.agent.agent import CodeAgent
from code_agent.config.settings_based_config import SettingsConfig


@pytest.fixture
def mock_litellm_completion_with_web_search_tool_call():
    """Mock a LiteLLM completion response that requests the web_search tool."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="Let me search for information on that.",
                tool_calls=[MagicMock(id="tool_1", function=MagicMock(name="web_search", arguments=json.dumps({"query": "test search query"})))],
            )
        )
    ]
    return mock_response


@pytest.fixture
def mock_litellm_final_answer():
    """Mock a LiteLLM completion response with a final answer using search results."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Based on the search results, the answer is: test answer", tool_calls=None))]
    return mock_response


@patch("code_agent.agent.agent.get_config")
@patch("code_agent.agent.agent.litellm.completion")
@patch("code_agent.agent.agent.web_search")
@patch("code_agent.agent.agent.thinking_indicator")
def test_agent_with_web_search_tool(
    mock_thinking, mock_web_search, mock_litellm, mock_get_config, mock_litellm_completion_with_web_search_tool_call, mock_litellm_final_answer
):
    """Test that CodeAgent properly calls the web_search tool when requested."""
    # Setup mocks
    mock_thinking.return_value.__enter__.return_value = None
    mock_thinking.return_value.__exit__.return_value = None

    mock_config = MagicMock(spec=SettingsConfig)
    mock_config.default_provider = "test_provider"
    mock_config.default_model = "test_model"
    mock_config.api_keys = MagicMock(test_provider="test_api_key")
    mock_config.rules = []
    mock_get_config.return_value = mock_config

    # Mock web_search response
    mock_web_search.return_value = "### Web Search Results\n\nTest search results"

    # Setup litellm.completion to return first a tool call, then a final answer
    mock_litellm.side_effect = [mock_litellm_completion_with_web_search_tool_call, mock_litellm_final_answer]

    # Run the agent
    agent = CodeAgent()
    result = agent.run_turn("What is the capital of France?")

    # Verify the web_search tool was called with expected parameters
    mock_web_search.assert_called_once_with(query="test search query")

    # Verify litellm was called twice (once for initial query, once after tool execution)
    assert mock_litellm.call_count == 2

    # Verify the final answer was returned
    assert result == "Based on the search results, the answer is: test answer"

    # Verify the conversation history was updated correctly
    assert len(agent.history) == 2
    assert agent.history[0]["role"] == "user"
    assert agent.history[0]["content"] == "What is the capital of France?"
    assert agent.history[1]["role"] == "assistant"
    assert agent.history[1]["content"] == "Based on the search results, the answer is: test answer"


@patch("code_agent.agent.agent.get_config")
@patch("code_agent.agent.agent.litellm.completion")
@patch("code_agent.agent.agent.web_search")
@patch("code_agent.agent.agent.thinking_indicator")
def test_agent_with_web_search_error(
    mock_thinking, mock_web_search, mock_litellm, mock_get_config, mock_litellm_completion_with_web_search_tool_call, mock_litellm_final_answer
):
    """Test that CodeAgent correctly handles errors from the web_search tool."""
    # Setup mocks
    mock_thinking.return_value.__enter__.return_value = None
    mock_thinking.return_value.__exit__.return_value = None

    mock_config = MagicMock(spec=SettingsConfig)
    mock_config.default_provider = "test_provider"
    mock_config.default_model = "test_model"
    mock_config.api_keys = MagicMock(test_provider="test_api_key")
    mock_config.rules = []
    mock_get_config.return_value = mock_config

    # Mock web_search to return an error
    mock_web_search.return_value = "Error: Web search failed due to network issues"

    # Setup litellm.completion to return first a tool call, then a final answer
    mock_litellm.side_effect = [mock_litellm_completion_with_web_search_tool_call, mock_litellm_final_answer]

    # Run the agent
    agent = CodeAgent()
    result = agent.run_turn("What is the capital of France?")

    # Verify the web_search tool was called
    mock_web_search.assert_called_once()

    # Verify the error was passed back to the LLM
    tool_response_call = mock_litellm.call_args_list[1]
    messages = tool_response_call[1]["messages"]
    tool_message = [msg for msg in messages if msg.get("role") == "tool"][0]
    assert "Error: Web search failed" in tool_message["content"]

    # Verify the final answer was still returned
    assert result == "Based on the search results, the answer is: test answer"


@patch("code_agent.agent.agent.get_config")
@patch("code_agent.agent.agent.litellm.completion")
@patch("code_agent.agent.agent.thinking_indicator")
def test_agent_with_tool_definitions(mock_thinking, mock_litellm, mock_get_config):
    """Test that CodeAgent includes the web_search tool in tool definitions."""
    # Setup mocks
    mock_thinking.return_value.__enter__.return_value = None
    mock_thinking.return_value.__exit__.return_value = None

    mock_config = MagicMock(spec=SettingsConfig)
    mock_config.default_provider = "test_provider"
    mock_config.default_model = "test_model"
    mock_config.api_keys = MagicMock(test_provider="test_api_key")
    mock_config.rules = []
    mock_get_config.return_value = mock_config

    # Mock litellm response to avoid full execution
    mock_litellm.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Test response", tool_calls=None))])

    # Run the agent
    agent = CodeAgent()
    agent.run_turn("Test prompt")

    # Verify web_search is in the tool definitions
    litellm_call = mock_litellm.call_args_list[0]
    tools = litellm_call[1]["tools"]

    # Get tool names
    tool_names = [tool["function"]["name"] for tool in tools]

    # Verify web_search is included
    assert "web_search" in tool_names

    # Get web_search tool definition
    web_search_tool = [tool for tool in tools if tool["function"]["name"] == "web_search"][0]

    # Verify it has the correct schema
    assert web_search_tool["function"]["description"] == "Searches the web for information using a query string"
    assert "query" in web_search_tool["function"]["parameters"]["properties"]
    assert web_search_tool["function"]["parameters"]["required"] == ["query"]
