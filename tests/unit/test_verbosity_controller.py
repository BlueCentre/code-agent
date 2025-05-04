"""
Tests for the verbosity controller module.
"""

from unittest.mock import patch

from code_agent.verbosity import VerbosityLevel, get_controller


class TestVerbosityLevel:
    """Tests for VerbosityLevel enum."""

    def test_verbosity_level_values(self):
        """Test that the verbosity levels have the expected values."""
        assert VerbosityLevel.QUIET.value == 0
        assert VerbosityLevel.NORMAL.value == 1
        assert VerbosityLevel.VERBOSE.value == 2
        assert VerbosityLevel.DEBUG.value == 3

    def test_verbosity_level_from_string(self):
        """Test the from_string class method."""
        # Test valid level names
        assert VerbosityLevel.from_string("QUIET") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("quiet") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("NORMAL") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("VERBOSE") == VerbosityLevel.VERBOSE
        assert VerbosityLevel.from_string("DEBUG") == VerbosityLevel.DEBUG

        # Test valid level numbers
        assert VerbosityLevel.from_string("0") == VerbosityLevel.QUIET
        assert VerbosityLevel.from_string("1") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("2") == VerbosityLevel.VERBOSE
        assert VerbosityLevel.from_string("3") == VerbosityLevel.DEBUG

        # Test invalid input (should default to NORMAL)
        assert VerbosityLevel.from_string("INVALID") == VerbosityLevel.NORMAL
        assert VerbosityLevel.from_string("999") == VerbosityLevel.NORMAL


class TestVerbosityController:
    """Tests for VerbosityController class."""

    def test_singleton_pattern(self):
        """Test that the VerbosityController follows the singleton pattern."""
        controller1 = get_controller()
        controller2 = get_controller()
        assert controller1 is controller2  # Same instance

    def test_default_level(self):
        """Test that the default verbosity level is NORMAL."""
        controller = get_controller()
        assert controller.level == VerbosityLevel.NORMAL
        assert controller.level_name == "NORMAL"
        assert controller.level_value == 1

    def test_set_level(self):
        """Test setting the verbosity level."""
        controller = get_controller()

        # Save original level to restore later
        original_level = controller.level

        try:
            # Test setting to each level
            controller.set_level(VerbosityLevel.QUIET)
            assert controller.level == VerbosityLevel.QUIET

            controller.set_level(VerbosityLevel.VERBOSE)
            assert controller.level == VerbosityLevel.VERBOSE

            controller.set_level(VerbosityLevel.DEBUG)
            assert controller.level == VerbosityLevel.DEBUG

            # Test set_level_from_string
            controller.set_level_from_string("NORMAL")
            assert controller.level == VerbosityLevel.NORMAL

            controller.set_level_from_string("2")  # VERBOSE
            assert controller.level == VerbosityLevel.VERBOSE
        finally:
            # Restore original level
            controller.set_level(original_level)

    def test_is_level_enabled(self):
        """Test is_level_enabled method."""
        controller = get_controller()

        # Save original level to restore later
        original_level = controller.level

        try:
            # Set to NORMAL and test
            controller.set_level(VerbosityLevel.NORMAL)
            assert controller.is_level_enabled(VerbosityLevel.QUIET) is True
            assert controller.is_level_enabled(VerbosityLevel.NORMAL) is True
            assert controller.is_level_enabled(VerbosityLevel.VERBOSE) is False
            assert controller.is_level_enabled(VerbosityLevel.DEBUG) is False

            # Set to VERBOSE and test
            controller.set_level(VerbosityLevel.VERBOSE)
            assert controller.is_level_enabled(VerbosityLevel.QUIET) is True
            assert controller.is_level_enabled(VerbosityLevel.NORMAL) is True
            assert controller.is_level_enabled(VerbosityLevel.VERBOSE) is True
            assert controller.is_level_enabled(VerbosityLevel.DEBUG) is False
        finally:
            # Restore original level
            controller.set_level(original_level)

    @patch("code_agent.verbosity.controller.rich_print")
    def test_show_methods(self, mock_rich_print):
        """Test the show_* methods."""
        controller = get_controller()

        # Save original level to restore later
        original_level = controller.level

        try:
            # Set to NORMAL level for testing
            controller.set_level(VerbosityLevel.NORMAL)

            # Test show_quiet (always shown)
            controller.show_quiet("Test quiet message")
            mock_rich_print.assert_called()
            mock_rich_print.reset_mock()

            # Test show_normal (shown at NORMAL and above)
            controller.show_normal("Test normal message")
            mock_rich_print.assert_called()
            mock_rich_print.reset_mock()

            # Test show_verbose (not shown at NORMAL)
            controller.show_verbose("Test verbose message")
            mock_rich_print.assert_not_called()
            mock_rich_print.reset_mock()

            # Test show_debug (not shown at NORMAL)
            controller.show_debug("Test debug message")
            mock_rich_print.assert_not_called()
            mock_rich_print.reset_mock()

            # Test show_error (always shown)
            controller.show_error("Test error message")
            mock_rich_print.assert_called()
            assert "Error" in mock_rich_print.call_args[0][0]
            mock_rich_print.reset_mock()

            # Test show_info (shown at NORMAL and above)
            controller.show_info("Test info message")
            mock_rich_print.assert_called()
            assert "Info" in mock_rich_print.call_args[0][0]
            mock_rich_print.reset_mock()

            # Now set to VERBOSE and test
            controller.set_level(VerbosityLevel.VERBOSE)

            # Test show_warning (shown at VERBOSE and above)
            controller.show_warning("Test warning message")
            mock_rich_print.assert_called()
            assert "Warning" in mock_rich_print.call_args[0][0]
            mock_rich_print.reset_mock()

            # Test show_success (shown at NORMAL and above)
            controller.show_success("Test success message")
            mock_rich_print.assert_called()
            assert "Success" in mock_rich_print.call_args[0][0]
            mock_rich_print.reset_mock()
        finally:
            # Restore original level
            controller.set_level(original_level)

    @patch("code_agent.verbosity.controller.Console.print")
    def test_show_debug_info(self, mock_console_print):
        """Test the show_debug_info method."""
        controller = get_controller()

        # Save original level to restore later
        original_level = controller.level

        try:
            # First test at NORMAL level (should not show debug info)
            controller.set_level(VerbosityLevel.NORMAL)
            controller.show_debug_info({"test": "data"})
            mock_console_print.assert_not_called()
            mock_console_print.reset_mock()

            # Now test at DEBUG level
            controller.set_level(VerbosityLevel.DEBUG)
            controller.show_debug_info({"test": "data"})
            mock_console_print.assert_called_once()
            # Testing for Panel is hard, so just verify that a call happened
        finally:
            # Restore original level
            controller.set_level(original_level)
