"""
Unit tests for the CLI agent initialization code in code_agent/cli/agent/__init__.py.
"""

import unittest
from unittest import mock

# Import the module under test
from code_agent.cli.agent import initialize_agent


class TestCliAgentInit(unittest.TestCase):
    """Unit tests for CLI Agent initialization."""

    @mock.patch("code_agent.cli.agent.agent_print")
    @mock.patch("code_agent.cli.agent.create_model")
    @mock.patch("code_agent.cli.agent.get_config")
    @mock.patch("code_agent.cli.agent.LlmAgent")
    @mock.patch("code_agent.cli.agent.genai")
    @mock.patch("code_agent.cli.agent.initialize_config")
    @mock.patch("code_agent.cli.agent.load_dotenv")
    def test_agent_initialization(self, mock_load_dotenv, mock_initialize_config, mock_genai, mock_llm_agent, mock_get_config, mock_create_model, mock_print):
        """Test that the agent initializes correctly with the proper configuration."""
        # Setup mocks
        mock_config = mock.MagicMock()
        mock_config.default_provider = "fake_provider"
        mock_config.default_model = "fake_model"
        mock_config.google_api_key = "fake_key"
        mock_config.ai_studio_api_key = None
        mock_get_config.return_value = mock_config

        mock_model = mock.MagicMock()
        mock_create_model.return_value = mock_model

        mock_agent = mock.MagicMock()
        mock_llm_agent.return_value = mock_agent

        # Call the function under test
        result = initialize_agent()

        # Assertions
        self.assertEqual(result, mock_agent)
        mock_print.assert_any_call("Initializing configuration...")
        mock_print.assert_any_call(f"Resolved Provider: {mock_config.default_provider}")
        mock_print.assert_any_call(f"Resolved Model: {mock_config.default_model}")
        mock_print.assert_any_call("Configuring genai globally with key from GOOGLE_API_KEY")

        # Verify API key configuration
        mock_genai.configure.assert_called_once_with(api_key="fake_key")

        # Verify model creation
        mock_create_model.assert_called_once()

        # Verify agent creation
        mock_llm_agent.assert_called_once()

        # Verify the agent is returned
        self.assertEqual(result, mock_agent)

    @mock.patch("code_agent.cli.agent.agent_print")
    @mock.patch("code_agent.cli.agent.create_model")
    @mock.patch("code_agent.cli.agent.get_config")
    @mock.patch("code_agent.cli.agent.LlmAgent")
    @mock.patch("code_agent.cli.agent.genai")
    @mock.patch("code_agent.cli.agent.initialize_config")
    @mock.patch("code_agent.cli.agent.load_dotenv")
    def test_agent_initialization_ai_studio_key(
        self, mock_load_dotenv, mock_initialize_config, mock_genai, mock_llm_agent, mock_get_config, mock_create_model, mock_print
    ):
        """Test agent initialization with AI Studio API key."""
        # Setup mocks
        mock_config = mock.MagicMock()
        mock_config.default_provider = "ai_studio"
        mock_config.default_model = "gemini-pro"
        mock_config.google_api_key = None
        mock_config.ai_studio_api_key = "fake_ai_studio_key"
        mock_get_config.return_value = mock_config

        # Setup model and agent mocks
        mock_model = mock.MagicMock()
        mock_create_model.return_value = mock_model

        mock_agent = mock.MagicMock()
        mock_llm_agent.return_value = mock_agent

        # Call the function under test
        result = initialize_agent()

        # Verify prints
        mock_print.assert_any_call("Configuring genai globally with key from AI_STUDIO_API_KEY")

        # Verify API key configuration
        mock_genai.configure.assert_called_once_with(api_key="fake_ai_studio_key")

        # Verify the agent is returned
        self.assertEqual(result, mock_agent)

    @mock.patch("code_agent.cli.agent.agent_print")
    @mock.patch("code_agent.cli.agent.create_model")
    @mock.patch("code_agent.cli.agent.get_config")
    @mock.patch("code_agent.cli.agent.LlmAgent")
    @mock.patch("code_agent.cli.agent.genai")
    @mock.patch("code_agent.cli.agent.initialize_config")
    @mock.patch("code_agent.cli.agent.load_dotenv")
    def test_agent_initialization_no_key(
        self, mock_load_dotenv, mock_initialize_config, mock_genai, mock_llm_agent, mock_get_config, mock_create_model, mock_print
    ):
        """Test agent initialization with no API key."""
        # Setup mocks
        mock_config = mock.MagicMock()
        mock_config.default_provider = "ai_studio"
        mock_config.default_model = "gemini-pro"
        mock_config.google_api_key = None
        mock_config.ai_studio_api_key = None
        mock_get_config.return_value = mock_config

        # Setup model and agent mocks
        mock_model = mock.MagicMock()
        mock_create_model.return_value = mock_model

        mock_agent = mock.MagicMock()
        mock_llm_agent.return_value = mock_agent

        # Call the function under test
        result = initialize_agent()

        # Assertions
        mock_print.assert_any_call("Warning: ai_studio provider selected but no GOOGLE_API_KEY/AI_STUDIO_API_KEY found.")
        mock_print.assert_any_call("         Agent might rely on Application Default Credentials (ADC).")
        mock_genai.configure.assert_not_called()

        # Verify the agent is returned
        self.assertEqual(result, mock_agent)
