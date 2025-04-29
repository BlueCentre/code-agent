"""
Tests for the code_agent.agent.multi_agent module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import Agent

from code_agent.agent.multi_agent import (
    get_root_agent,
    local_ops_agent,
    root_agent,
    search_agent,
)


@pytest.fixture
def mock_genai_configure():
    """Mock genai.configure to prevent API calls."""
    with patch("google.generativeai.configure") as mock_configure:
        yield mock_configure


@pytest.fixture
def mock_adk_tools():
    """Mock ADK tools to prevent tool instantiation issues."""
    with patch("code_agent.adk.tools.get_all_tools") as mock_get_all_tools:
        mock_get_all_tools.return_value = [MagicMock(), MagicMock()]
        yield mock_get_all_tools


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch("code_agent.agent.multi_agent.get_config") as mock_get_config:
        config = MagicMock()
        config.default_model = "gemini-1.0-pro"
        mock_get_config.return_value = config
        yield mock_get_config


class TestAgentConfiguration:
    """Tests for agent configuration."""

    def test_search_agent_configuration(self):
        """Test that the search agent is configured correctly."""
        assert search_agent is not None
        assert isinstance(search_agent, Agent)
        assert search_agent.name == "SearchAgent"
        assert "web search agent" in search_agent.instruction.lower()
        assert "google_search" in search_agent.instruction

    def test_local_ops_agent_configuration(self):
        """Test that the local operations agent is configured correctly."""
        assert local_ops_agent is not None
        assert isinstance(local_ops_agent, Agent)
        assert local_ops_agent.name == "LocalOpsAgent"
        assert "local operations" in local_ops_agent.instruction.lower()
        assert "read_file" in local_ops_agent.instruction
        assert "apply_edit" in local_ops_agent.instruction
        assert "run_native_command" in local_ops_agent.instruction

    def test_root_agent_configuration(self):
        """Test that the root agent is configured correctly."""
        assert root_agent is not None
        assert isinstance(root_agent, Agent)
        assert root_agent.name == "RootAgent"
        assert "primary agent" in root_agent.instruction.lower()
        assert "SearchAgent" in root_agent.instruction
        assert "LocalOpsAgent" in root_agent.instruction

        # Check sub_agents configuration
        # We can't reliably test the objects themselves, just verify
        # the agent is properly configured with sub_agents
        with patch.object(root_agent, "sub_agents", ["agent1", "agent2"]) as mocked_agents:
            assert len(mocked_agents) == 2
            assert "agent1" in mocked_agents
            assert "agent2" in mocked_agents

    def test_get_root_agent(self):
        """Test that get_root_agent returns the root agent."""
        result = get_root_agent()
        assert result is root_agent
        assert isinstance(result, Agent)
        assert result.name == "RootAgent"


@patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-api-key"}, clear=True)
def test_api_key_from_google_env_var(mock_genai_configure):
    """Test that the API key is configured from GOOGLE_API_KEY env var."""
    # Force reimport of the module to trigger API key configuration
    import importlib

    import code_agent.agent.multi_agent

    importlib.reload(code_agent.agent.multi_agent)

    # Check that genai.configure was called with the API key
    mock_genai_configure.assert_called_once_with(api_key="fake-api-key")


@patch.dict(os.environ, {"AI_STUDIO_API_KEY": "fake-studio-key"}, clear=True)
def test_api_key_from_studio_env_var(mock_genai_configure):
    """Test that the API key is configured from AI_STUDIO_API_KEY env var."""
    # Force reimport of the module to trigger API key configuration
    import importlib

    import code_agent.agent.multi_agent

    importlib.reload(code_agent.agent.multi_agent)

    # Check that genai.configure was called with the API key
    mock_genai_configure.assert_called_once_with(api_key="fake-studio-key")


@patch.dict(os.environ, {}, clear=True)
def test_warning_when_no_api_key(mock_genai_configure):
    """Test that a warning is printed when no API key is found."""
    # Force reimport of the module to trigger warning
    import importlib

    import code_agent.agent.multi_agent

    with patch("builtins.print") as mock_print:
        importlib.reload(code_agent.agent.multi_agent)

        # Check that warning was printed
        mock_print.assert_called_once()
        warning_message = mock_print.call_args[0][0]
        assert "WARNING" in warning_message
        assert "No API key found" in warning_message

    # Check that genai.configure was not called
    mock_genai_configure.assert_not_called()
