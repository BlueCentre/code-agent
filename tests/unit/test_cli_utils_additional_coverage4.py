"""Additional unit tests for code_agent.cli.utils module to further improve coverage."""

import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console

from code_agent.cli.utils import (
    _resolve_agent_path_str,
    operation_complete,
    operation_error,
    operation_warning,
    setup_logging,
    step_progress,
    thinking_indicator,
)
from code_agent.config import CodeAgentSettings


class TestPathResolution(unittest.TestCase):
    """Test the path resolution functionality in cli.utils."""

    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_with_cli_arg(self, mock_console_class):
        """Test resolving path when CLI argument is provided."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock(spec=CodeAgentSettings)
        mock_cfg.default_agent_path = None

        # Create a temporary path that exists
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.resolve", return_value=Path("/tmp/agent")):
            agent_path_cli = Path("/tmp/agent")
            result = _resolve_agent_path_str(agent_path_cli, mock_cfg)

        # Verify
        self.assertEqual(result, "/tmp/agent")
        mock_console.print.assert_not_called()  # No errors should be printed

    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_with_config_default(self, mock_console_class):
        """Test resolving path when using config default."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock(spec=CodeAgentSettings)
        mock_cfg.default_agent_path = Path("/config/default/agent")

        # Create a temporary path that exists
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.resolve", return_value=Path("/config/default/agent")):
            result = _resolve_agent_path_str(None, mock_cfg)

        # Verify
        self.assertEqual(result, "/config/default/agent")
        mock_console.print.assert_not_called()  # No errors should be printed

    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_with_fallback(self, mock_console_class):
        """Test resolving path when falling back to current directory."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock(spec=CodeAgentSettings)
        mock_cfg.default_agent_path = None

        # Create a temporary path that exists
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.resolve", return_value=Path(".")):
            result = _resolve_agent_path_str(None, mock_cfg)

        # Verify
        self.assertEqual(result, ".")
        # Should print a warning about defaulting to current directory
        mock_console.print.assert_called_once()
        self.assertIn("Warning", str(mock_console.print.call_args))

    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_nonexistent_path(self, mock_console_class):
        """Test resolving path when path doesn't exist."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock(spec=CodeAgentSettings)
        mock_cfg.default_agent_path = None

        # Create a temporary path that doesn't exist
        with patch("pathlib.Path.exists", return_value=False), patch("pathlib.Path.resolve", return_value=Path("/nonexistent/path")):
            agent_path_cli = Path("/nonexistent/path")
            result = _resolve_agent_path_str(agent_path_cli, mock_cfg)

        # Verify
        self.assertIsNone(result)
        # Should print an error about the path not existing
        mock_console.print.assert_called()
        self.assertIn("does not exist", str(mock_console.print.call_args_list[0]))


class TestLoggingSetup(unittest.TestCase):
    """Test the logging setup functionality."""

    def setUp(self):
        """Set up the test case."""
        # Save original logging configuration
        self.original_level = logging.getLogger().level
        self.original_handlers = logging.getLogger().handlers.copy()

    def tearDown(self):
        """Clean up after the test case."""
        # Restore original logging configuration
        logging.getLogger().setLevel(self.original_level)
        logging.getLogger().handlers = self.original_handlers

    def test_setup_logging_with_no_handlers(self):
        """Test setting up logging when there are no handlers."""
        # Remove all handlers
        logging.getLogger().handlers = []

        # Call the function
        setup_logging(verbosity_level=2)  # INFO level

        # Verify
        self.assertEqual(logging.getLogger().level, logging.INFO)
        self.assertEqual(len(logging.getLogger().handlers), 1)
        self.assertEqual(logging.getLogger().handlers[0].level, logging.INFO)

    def test_setup_logging_with_existing_handlers(self):
        """Test setting up logging when there are existing handlers."""
        # Add a handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        logging.getLogger().addHandler(handler)

        # Call the function
        setup_logging(verbosity_level=3)  # DEBUG level

        # Verify
        self.assertEqual(logging.getLogger().level, logging.DEBUG)
        for handler in logging.getLogger().handlers:
            self.assertEqual(handler.level, logging.DEBUG)

    def test_setup_logging_with_invalid_level(self):
        """Test setting up logging with an invalid verbosity level."""
        # Call the function with an invalid level
        setup_logging(verbosity_level=99)  # Invalid level

        # Should default to WARNING
        self.assertEqual(logging.getLogger().level, logging.WARNING)


class TestConsoleHelpers(unittest.TestCase):
    """Test the Rich Console helper functions."""

    def test_thinking_indicator(self):
        """Test the thinking indicator context manager."""
        mock_console = MagicMock(spec=Console)
        message = "Thinking..."

        # Use the context manager
        with thinking_indicator(mock_console, message):
            # Verify that the message is printed
            mock_console.print.assert_called_with(f"[dim]{message}[/dim]", end="\r")
            mock_console.print.reset_mock()

        # Verify that the message is cleared at the end
        mock_console.print.assert_called_with(" " * len(message), end="\r")

    def test_operation_helpers(self):
        """Test the operation helper functions."""
        mock_console = MagicMock(spec=Console)
        message = "Test message"

        # Test operation_complete
        operation_complete(mock_console, message)
        mock_console.print.assert_called_with(f"[bold green]✓[/bold green] {message}")
        mock_console.print.reset_mock()

        # Test operation_error
        operation_error(mock_console, message)
        mock_console.print.assert_called_with(f"[bold red]✗[/bold red] {message}")
        mock_console.print.reset_mock()

        # Test operation_warning
        operation_warning(mock_console, message)
        mock_console.print.assert_called_with(f"[bold yellow]![/bold yellow] {message}")
        mock_console.print.reset_mock()

        # Test step_progress
        step_progress(mock_console, message)
        mock_console.print.assert_called_with(f"[bold cyan]→[/bold cyan] {message}")


if __name__ == "__main__":
    unittest.main()
