"""Additional unit tests for code_agent.cli.utils module to improve coverage."""

import signal
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from code_agent.cli.utils import (
    run_cli,
    save_config_data,
)


class TestSaveConfigData(unittest.TestCase):
    """Test the save_config_data function for different scenarios."""

    @patch("code_agent.cli.utils.Console")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_dump")
    def test_save_config_data_creates_parent_directories(self, mock_yaml_safe_dump, mock_file_open, mock_console_class):
        """Test save_config_data creates parent directories."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Create a mock Path with parent property
        mock_path = MagicMock()
        mock_parent = MagicMock()
        mock_path.parent = mock_parent

        # Create test data
        config_data = {"key": "value"}

        # Call the function
        save_config_data(mock_path, config_data)

        # Verify
        mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once_with(mock_path, "w")
        mock_yaml_safe_dump.assert_called_once()
        # Verify the arguments to yaml.safe_dump
        args, kwargs = mock_yaml_safe_dump.call_args
        self.assertEqual(args[0], config_data)  # First arg should be the config data
        self.assertEqual(kwargs.get("default_flow_style"), False)
        self.assertEqual(kwargs.get("sort_keys"), False)


class TestRunCliWithSignals(unittest.TestCase):
    """Test the run_cli function's signal handling capabilities."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.signal.getsignal")
    def test_run_cli_handles_sigint_registration(self, mock_getsignal, mock_signal, mock_console_class):
        """Test run_cli registers a SIGINT handler correctly."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock original handler
        original_handler = MagicMock()
        mock_getsignal.return_value = original_handler

        # Mock asyncio.run to return immediately
        with patch("code_agent.cli.utils.asyncio.run") as mock_asyncio_run:
            # Mock necessary objects
            mock_agent = MagicMock()
            mock_session_service = MagicMock()
            mock_asyncio_run.return_value = ("test_session_id", True)

            # Ensure no real interrupts occur during test
            mock_signal.side_effect = None

            # Call function
            run_cli(agent=mock_agent, app_name="test_app", session_service=mock_session_service, initial_instruction="Test instruction")

            # Verify signal handler was registered
            mock_signal.assert_any_call(signal.SIGINT, unittest.mock.ANY)

            # Get the registered handler
            handler = mock_signal.call_args_list[0][0][1]
            self.assertIsNotNone(handler)

            # Verify original signal was retrieved
            mock_getsignal.assert_called_once_with(signal.SIGINT)

    @patch("code_agent.cli.utils.Console")
    @patch("asyncio.run")
    @patch("code_agent.cli.utils.thinking_indicator")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.signal.getsignal")
    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.operation_error")
    def test_run_cli_prints_final_error_on_exception(
        self, mock_operation_error, mock_runner_class, mock_getsignal, mock_signal, mock_thinking_indicator, mock_asyncio_run, mock_console_class
    ):
        """Test run_cli shows error message when asyncio.run raises exception."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock runner
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Make asyncio.run raise an exception
        test_error = RuntimeError("Test error")
        mock_asyncio_run.side_effect = test_error

        # Mock necessary objects
        mock_agent = MagicMock()
        mock_session_service = MagicMock()

        # Mock signal handling
        original_handler = MagicMock()
        mock_getsignal.return_value = original_handler

        # Since run_cli will re-raise the exception, we need to catch it
        with pytest.raises(RuntimeError):
            run_cli(agent=mock_agent, app_name="test_app", session_service=mock_session_service, initial_instruction="Test instruction")

        # Verify operation_error was called with an error message containing our error
        mock_operation_error.assert_called_once()
        args, _ = mock_operation_error.call_args
        console_arg, error_msg = args

        # Check that the console is passed in and error message contains our test error
        self.assertEqual(console_arg, mock_console)
        self.assertIn("Test error", error_msg)


class TestCliLogHandling(unittest.TestCase):
    """Test CLI logger suppression and setup functionality."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.logging")
    def test_run_cli_suppresses_specific_loggers(self, mock_logging, mock_console_class):
        """Test run_cli suppresses specific loggers to reduce noise."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Create mock loggers
        mock_adk_logger = MagicMock()
        mock_genai_logger = MagicMock()

        # Setup logging.getLogger to return our mocks
        def get_logger_side_effect(name):
            if name == "google.adk.tools.function_parameter_parse_util":
                return mock_adk_logger
            elif name == "google_genai.types":
                return mock_genai_logger
            return MagicMock()

        mock_logging.getLogger.side_effect = get_logger_side_effect

        # Mock other dependencies to prevent actual execution
        with (
            patch("code_agent.cli.utils.signal.signal"),
            patch("code_agent.cli.utils.signal.getsignal"),
            patch("code_agent.cli.utils.asyncio.run", return_value=("test_session_id", True)),
        ):
            # Call function with minimal arguments
            run_cli(agent=MagicMock(), app_name="test_app", session_service=MagicMock(), initial_instruction="Test instruction")

            # Verify specific loggers were set to ERROR level
            mock_adk_logger.setLevel.assert_called_once_with(mock_logging.ERROR)
            mock_genai_logger.setLevel.assert_called_once_with(mock_logging.ERROR)

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_run_cli_simple_error_handling(self, mock_asyncio_run, mock_console_class):
        """Test that run_cli prints a final error message when an exception occurs."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        agent = MagicMock()
        mock_asyncio_run.side_effect = ValueError("Test error")

        # Run with a test exception - providing initial_instruction to avoid Prompt.ask
        with pytest.raises(ValueError):
            run_cli(agent=agent, app_name="test_app", initial_instruction="Test instruction")

        # Verify the error was printed with the correct format
        # The actual implementation uses "✗" symbol instead of "Error:"
        mock_console.print.assert_any_call("[bold red]✗[/bold red] An error occurred: Test error")


if __name__ == "__main__":
    unittest.main()
