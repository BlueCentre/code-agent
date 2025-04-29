"""
Tests for code_agent.verbosity.controller module.
"""

import os
from unittest.mock import MagicMock, patch

from code_agent.verbosity.controller import VerbosityController, VerbosityLevel, get_controller


class TestVerbosityLevel:
    """Test class for VerbosityLevel enum."""

    def test_verbosity_level_values(self):
        """Test that VerbosityLevel enum has correct values."""
        assert VerbosityLevel.QUIET.value == 0
        assert VerbosityLevel.NORMAL.value == 1
        assert VerbosityLevel.VERBOSE.value == 2
        assert VerbosityLevel.DEBUG.value == 3

    def test_from_string_valid_name(self):
        """Test conversion from valid string names to VerbosityLevel."""
        assert VerbosityLevel.from_string("QUIET") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("quiet") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("NORMAL") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("normal") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("VERBOSE") == VerbosityLevel.VERBOSE
        assert VerbosityLevel.from_string("verbose") == VerbosityLevel.VERBOSE
        assert VerbosityLevel.from_string("DEBUG") == VerbosityLevel.DEBUG
        assert VerbosityLevel.from_string("debug") == VerbosityLevel.DEBUG

    def test_from_string_valid_number(self):
        """Test conversion from valid string numbers to VerbosityLevel."""
        assert VerbosityLevel.from_string("0") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("1") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("2") == VerbosityLevel.VERBOSE
        assert VerbosityLevel.from_string("3") == VerbosityLevel.DEBUG

    def test_from_string_invalid_input(self):
        """Test conversion from invalid strings defaults to NORMAL."""
        assert VerbosityLevel.from_string("INVALID") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("4") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("-1") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("abc123") == VerbosityLevel.NORMAL


class TestVerbosityController:
    """Test class for VerbosityController."""

    def setup_method(self):
        """Reset the VerbosityController singleton before each test."""
        VerbosityController._instance = None

    def test_singleton_pattern(self):
        """Test that VerbosityController follows singleton pattern."""
        controller1 = VerbosityController()
        controller2 = VerbosityController()
        assert controller1 is controller2

    def test_get_controller(self):
        """Test get_controller function returns singleton instance."""
        controller1 = get_controller()
        controller2 = get_controller()
        assert controller1 is controller2
        assert isinstance(controller1, VerbosityController)

    def test_default_level(self):
        """Test default level is NORMAL."""
        controller = VerbosityController()
        assert controller.level == VerbosityLevel.NORMAL
        assert controller.level_value == 1
        assert controller.level_name == "NORMAL"

    def test_custom_initial_level(self):
        """Test setting a custom initial level."""
        controller = VerbosityController(initial_level=VerbosityLevel.DEBUG)
        assert controller.level == VerbosityLevel.DEBUG
        assert controller.level_value == 3
        assert controller.level_name == "DEBUG"

    @patch.dict(os.environ, {"CODE_AGENT_VERBOSITY": "DEBUG"}, clear=True)
    def test_env_var_override(self):
        """Test that environment variable overrides initial level."""
        controller = VerbosityController()  # Should read from env var
        assert controller.level == VerbosityLevel.DEBUG

    def test_set_level(self):
        """Test setting the verbosity level."""
        controller = VerbosityController()
        # Start with default NORMAL
        assert controller.level == VerbosityLevel.NORMAL

        # Change to DEBUG
        result = controller.set_level(VerbosityLevel.DEBUG)
        assert controller.level == VerbosityLevel.DEBUG
        assert "NORMAL to DEBUG" in result

        # Change to QUIET
        result = controller.set_level(VerbosityLevel.QUIET)
        assert controller.level == VerbosityLevel.QUIET
        assert "DEBUG to QUIET" in result

    def test_set_level_from_string(self):
        """Test setting the verbosity level from a string."""
        controller = VerbosityController()

        result = controller.set_level_from_string("DEBUG")
        assert controller.level == VerbosityLevel.DEBUG
        assert "NORMAL to DEBUG" in result

        result = controller.set_level_from_string("0")  # QUIET
        assert controller.level == VerbosityLevel.QUIET
        assert "DEBUG to QUIET" in result

    def test_is_level_enabled(self):
        """Test is_level_enabled method."""
        controller = VerbosityController(initial_level=VerbosityLevel.NORMAL)

        # At NORMAL level
        assert controller.is_level_enabled(VerbosityLevel.QUIET) is True
        assert controller.is_level_enabled(VerbosityLevel.NORMAL) is True
        assert controller.is_level_enabled(VerbosityLevel.VERBOSE) is False
        assert controller.is_level_enabled(VerbosityLevel.DEBUG) is False

        # Change to DEBUG level
        controller.set_level(VerbosityLevel.DEBUG)
        assert controller.is_level_enabled(VerbosityLevel.QUIET) is True
        assert controller.is_level_enabled(VerbosityLevel.NORMAL) is True
        assert controller.is_level_enabled(VerbosityLevel.VERBOSE) is True
        assert controller.is_level_enabled(VerbosityLevel.DEBUG) is True

        # Change to QUIET level
        controller.set_level(VerbosityLevel.QUIET)
        assert controller.is_level_enabled(VerbosityLevel.QUIET) is True
        assert controller.is_level_enabled(VerbosityLevel.NORMAL) is False
        assert controller.is_level_enabled(VerbosityLevel.VERBOSE) is False
        assert controller.is_level_enabled(VerbosityLevel.DEBUG) is False

    @patch("code_agent.verbosity.controller.rich_print")
    def test_show(self, mock_rich_print):
        """Test show method respects verbosity levels."""
        controller = VerbosityController(initial_level=VerbosityLevel.NORMAL)

        # At NORMAL level
        controller.show("Test message", VerbosityLevel.QUIET)
        controller.show("Test message", VerbosityLevel.NORMAL)
        controller.show("Test message", VerbosityLevel.VERBOSE)
        controller.show("Test message", VerbosityLevel.DEBUG)

        # Should have printed only QUIET and NORMAL messages
        assert mock_rich_print.call_count == 2

        # Change to DEBUG level and reset mock
        controller.set_level(VerbosityLevel.DEBUG)
        mock_rich_print.reset_mock()

        controller.show("Test message", VerbosityLevel.QUIET)
        controller.show("Test message", VerbosityLevel.NORMAL)
        controller.show("Test message", VerbosityLevel.VERBOSE)
        controller.show("Test message", VerbosityLevel.DEBUG)

        # Should have printed all messages
        assert mock_rich_print.call_count == 4

    @patch("code_agent.verbosity.controller.rich_print")
    def test_convenience_methods(self, mock_rich_print):
        """Test convenience show methods."""
        controller = VerbosityController(initial_level=VerbosityLevel.NORMAL)

        # These should print at NORMAL level
        controller.show_quiet("Quiet message")
        controller.show_normal("Normal message")
        controller.show_error("Error message")
        controller.show_info("Info message")
        controller.show_success("Success message")

        # These should not print at NORMAL level
        controller.show_verbose("Verbose message")
        controller.show_debug("Debug message")
        controller.show_warning("Warning message")

        # Check the number of calls (5 should have printed)
        assert mock_rich_print.call_count == 5

        # Set to DEBUG level and test all methods
        controller.set_level(VerbosityLevel.DEBUG)
        mock_rich_print.reset_mock()

        controller.show_quiet("Quiet message")
        controller.show_normal("Normal message")
        controller.show_verbose("Verbose message")
        controller.show_debug("Debug message")
        controller.show_error("Error message")
        controller.show_warning("Warning message")
        controller.show_info("Info message")
        controller.show_success("Success message")

        # All 8 should have printed
        assert mock_rich_print.call_count == 8

    @patch("code_agent.verbosity.controller.Console")
    def test_show_debug_info(self, mock_console):
        """Test show_debug_info method."""
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # At NORMAL level, should not print
        controller = VerbosityController(initial_level=VerbosityLevel.NORMAL)
        controller.show_debug_info({"test": "data"})
        mock_console_instance.print.assert_not_called()

        # At DEBUG level, should print
        controller.set_level(VerbosityLevel.DEBUG)
        controller.show_debug_info({"test": "data"})
        assert mock_console_instance.print.call_count == 1

    @patch("code_agent.verbosity.controller.rich_print")
    def test_start_stop_methods(self, mock_rich_print):
        """Test start and stop methods."""
        # At NORMAL level, should not print
        controller = VerbosityController(initial_level=VerbosityLevel.NORMAL)
        controller.start()
        controller.stop()
        mock_rich_print.assert_not_called()

        # At DEBUG level, should print start and stop messages
        controller.set_level(VerbosityLevel.DEBUG)
        controller.start()
        controller.stop()
        assert mock_rich_print.call_count == 2
        assert mock_rich_print.call_args_list[0][0][0] == "VerbosityController started"
        assert mock_rich_print.call_args_list[1][0][0] == "VerbosityController stopped"
