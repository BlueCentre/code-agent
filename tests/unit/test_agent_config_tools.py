"""
Tests for agent_config_tools.py module.
"""

from unittest.mock import MagicMock, patch

from code_agent.tools.agent_config_tools import get_config_info, set_verbosity, simple_tools_list


class TestAgentConfigTools:
    """Test class for agent configuration tools."""

    @patch("code_agent.tools.agent_config_tools.get_controller")
    @patch("code_agent.tools.agent_config_tools.get_config")
    def test_set_verbosity_quiet(self, mock_get_config, mock_get_controller):
        """Test setting verbosity to QUIET level."""
        # Setup mocks
        mock_controller = MagicMock()
        mock_controller.set_level_from_string.return_value = "Verbosity set to QUIET"
        mock_controller.level_value = 0
        mock_get_controller.return_value = mock_controller

        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Call the function
        result = set_verbosity("QUIET")

        # Verify the controller and config were updated
        mock_controller.set_level_from_string.assert_called_once_with("QUIET")
        assert mock_config.verbosity == 0
        assert "QUIET" in result
        assert "essential information" in result

    @patch("code_agent.tools.agent_config_tools.get_controller")
    @patch("code_agent.tools.agent_config_tools.get_config")
    def test_set_verbosity_normal(self, mock_get_config, mock_get_controller):
        """Test setting verbosity to NORMAL level."""
        # Setup mocks
        mock_controller = MagicMock()
        mock_controller.set_level_from_string.return_value = "Verbosity set to NORMAL"
        mock_controller.level_value = 1
        mock_get_controller.return_value = mock_controller

        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Call the function
        result = set_verbosity("NORMAL")

        # Verify the controller and config were updated
        mock_controller.set_level_from_string.assert_called_once_with("NORMAL")
        assert mock_config.verbosity == 1
        assert "NORMAL" in result
        assert "Standard information" in result

    @patch("code_agent.tools.agent_config_tools.get_controller")
    @patch("code_agent.tools.agent_config_tools.get_config")
    def test_set_verbosity_verbose(self, mock_get_config, mock_get_controller):
        """Test setting verbosity to VERBOSE level."""
        # Setup mocks
        mock_controller = MagicMock()
        mock_controller.set_level_from_string.return_value = "Verbosity set to VERBOSE"
        mock_controller.level_value = 2
        mock_get_controller.return_value = mock_controller

        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Call the function
        result = set_verbosity("VERBOSE")

        # Verify the controller and config were updated
        mock_controller.set_level_from_string.assert_called_once_with("VERBOSE")
        assert mock_config.verbosity == 2
        assert "VERBOSE" in result
        assert "Additional details" in result

    @patch("code_agent.tools.agent_config_tools.get_controller")
    @patch("code_agent.tools.agent_config_tools.get_config")
    def test_set_verbosity_debug(self, mock_get_config, mock_get_controller):
        """Test setting verbosity to DEBUG level."""
        # Setup mocks
        mock_controller = MagicMock()
        mock_controller.set_level_from_string.return_value = "Verbosity set to DEBUG"
        mock_controller.level_value = 3
        mock_get_controller.return_value = mock_controller

        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Call the function
        result = set_verbosity("DEBUG")

        # Verify the controller and config were updated
        mock_controller.set_level_from_string.assert_called_once_with("DEBUG")
        assert mock_config.verbosity == 3
        assert "DEBUG" in result
        assert "diagnostic information" in result

    def test_get_config_info(self):
        """Test getting config information."""
        result = get_config_info()

        # Verify the result contains expected tool information
        assert "Available tools" in result
        assert "read_file" in result
        assert "apply_edit" in result
        assert "run_native_command" in result
        assert "google_search" in result
        assert "set_verbosity" in result

    def test_simple_tools_list(self):
        """Test getting a simple list of tools."""
        result = simple_tools_list()

        # Verify the result contains expected tool information
        assert "Available tools" in result
        assert "read_file" in result
        assert "apply_edit" in result
        assert "run_native_command" in result
        assert "google_search" in result
        assert "set_verbosity" in result
