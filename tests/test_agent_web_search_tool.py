from unittest.mock import MagicMock, patch

from code_agent.agent.agent import CodeAgent
from code_agent.config.settings_based_config import SettingsConfig


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
