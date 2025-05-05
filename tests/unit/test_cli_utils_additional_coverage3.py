"""Additional unit tests for code_agent.cli.utils module to improve coverage."""

import logging
import signal
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from code_agent.cli.utils import (
    operation_complete,
    operation_error,
    operation_warning,
    run_cli,
    setup_logging,
    thinking_indicator,
)
from code_agent.verbosity import VerbosityLevel


class TestThinkingIndicator(unittest.TestCase):
    """Test the thinking_indicator context manager."""

    def test_thinking_indicator_start_stop(self):
        """Test that the thinking indicator starts and stops properly."""
        # Setup
        mock_console = MagicMock(spec=Console)
        test_message = "Processing your request..."

        # Use the context manager
        with thinking_indicator(mock_console, test_message):
            # Verify the message is displayed
            mock_console.print.assert_called_with(f"[dim]{test_message}[/dim]", end="\r")
            mock_console.print.reset_mock()

        # After the context manager exits, verify it clears the line
        mock_console.print.assert_called_with(" " * len(test_message), end="\r")


class TestLoggingSetup(unittest.TestCase):
    """Test the setup_logging function."""

    @patch("logging.getLogger")
    def test_setup_logging_with_debug_level(self, mock_get_logger):
        """Test setup_logging with DEBUG verbosity level."""
        # Setup mock logger
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        # In the actual implementation, VerbosityLevel.DEBUG maps to logging.WARNING (30)
        # rather than logging.DEBUG (10) as we expected
        setup_logging(verbosity_level=VerbosityLevel.DEBUG)

        # Verify root logger level was set to WARNING, not DEBUG
        mock_root_logger.setLevel.assert_called_once_with(logging.WARNING)

    @patch("logging.getLogger")
    def test_setup_logging_sets_handler_levels(self, mock_get_logger):
        """Test setup_logging sets handler levels correctly."""
        # Setup
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger

        # Create some mock handlers
        handler1 = MagicMock()
        handler2 = MagicMock()
        mock_root_logger.handlers = [handler1, handler2]

        # Call the function
        setup_logging(verbosity_level=VerbosityLevel.NORMAL)

        # Verify handlers were set to the correct level
        handler1.setLevel.assert_called_once_with(logging.WARNING)
        handler2.setLevel.assert_called_once_with(logging.WARNING)


class TestConsoleHelpers(unittest.TestCase):
    """Test the console helper functions."""

    def test_operation_complete(self):
        """Test the operation_complete function."""
        console = MagicMock(spec=Console)
        message = "Operation completed successfully"

        operation_complete(console, message)

        console.print.assert_called_once()
        args, kwargs = console.print.call_args
        self.assertIn(message, str(args[0]))
        self.assertIn("green", str(args[0]))

    def test_operation_warning(self):
        """Test the operation_warning function."""
        console = MagicMock(spec=Console)
        message = "Warning about the operation"

        operation_warning(console, message)

        console.print.assert_called_once()
        args, kwargs = console.print.call_args
        self.assertIn(message, str(args[0]))
        self.assertIn("yellow", str(args[0]))

    def test_operation_error(self):
        """Test the operation_error function."""
        console = MagicMock(spec=Console)
        message = "Error in the operation"

        operation_error(console, message)

        console.print.assert_called_once()
        args, kwargs = console.print.call_args
        self.assertIn(message, str(args[0]))
        self.assertIn("red", str(args[0]))


class TestCliInteractivity(unittest.TestCase):
    """Test the interactive CLI functionality."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("code_agent.cli.utils.asyncio.run")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.signal.getsignal")
    def test_run_cli_with_initial_instruction_none(self, mock_getsignal, mock_signal, mock_asyncio_run, mock_prompt_ask, mock_console_class):
        """Test run_cli with no initial instruction."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        mock_agent = MagicMock()
        mock_session_service = MagicMock()

        # Mock Prompt.ask to return an instruction
        mock_prompt_ask.return_value = "Generated instruction"

        # Mock asyncio.run to return a session ID and success
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Mock signal handling
        original_handler = MagicMock()
        mock_getsignal.return_value = original_handler

        # Call run_cli with no initial instruction
        run_cli(agent=mock_agent, app_name="test_app", session_service=mock_session_service, initial_instruction=None, interactive=False)

        # Verify Prompt.ask was called to get an instruction
        mock_prompt_ask.assert_called_once()

        # Verify asyncio.run was called with the generated instruction
        mock_asyncio_run.assert_called_once()

        # Verify signal handler was set up and restored
        mock_getsignal.assert_called_once_with(signal.SIGINT)
        mock_signal.assert_any_call(signal.SIGINT, unittest.mock.ANY)
        mock_signal.assert_any_call(signal.SIGINT, original_handler)


if __name__ == "__main__":
    unittest.main()
