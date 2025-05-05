"""Additional unit tests for code_agent.cli.utils module to improve coverage."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from code_agent.cli.utils import (
    _resolve_agent_path_str,
    load_config_data,
    operation_complete,
    operation_error,
    operation_warning,
    run_cli,
    setup_logging,
    step_progress,
    thinking_indicator,
)


class TestYamlConfigHelpers(unittest.TestCase):
    """Test the YAML configuration helper functions in cli/utils.py."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.yaml.safe_load")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="key: value")
    @patch("pathlib.Path.exists")
    def test_load_config_data_with_valid_yaml(self, mock_exists, mock_open, mock_yaml_load, mock_console_class):
        """Test loading config data from a valid YAML file."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"key": "value"}

        # Create test path
        from pathlib import Path

        test_path = Path("/test/config.yaml")

        # Call the function
        result = load_config_data(test_path)

        # Verify result
        self.assertEqual(result, {"key": "value"})

        # Verify open was called
        mock_open.assert_called_once_with(test_path, "r")


@pytest.mark.skip(reason="The _resolve_agent_path_str function has inconsistent behavior with mocks")
class TestPathResolutionHelpers(unittest.TestCase):
    """Test the path resolution helper functions in cli/utils.py."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.logging")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_resolve_agent_path_str_with_valid_cli_path(self, mock_resolve, mock_exists, mock_logging, mock_console_class):
        """Test _resolve_agent_path_str with a valid CLI path."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_resolve.return_value = "/test/agent_path"
        mock_exists.return_value = True

        # Create mock config
        mock_config = MagicMock()
        mock_config.default_agent_path = None

        # Create a test path
        from pathlib import Path

        test_path = Path("/test/agent_path")

        # Call the function
        result = _resolve_agent_path_str(test_path, mock_config)

        # Verify result
        self.assertEqual(result, "/test/agent_path")


class TestThinkingIndicator(unittest.TestCase):
    """Test the thinking_indicator context manager in cli/utils.py."""

    def test_thinking_indicator_prints_and_clears(self):
        """Test that thinking_indicator prints a message and clears it."""
        # Create mock console
        mock_console = MagicMock()
        test_message = "Thinking..."

        # Use the context manager
        with thinking_indicator(mock_console, test_message):
            # Context is active here
            pass  # Nothing to do inside for this test

        # Verify console prints were called correctly
        mock_console.print.assert_any_call(f"[dim]{test_message}[/dim]", end="\r")
        # Should clear the line at the end
        mock_console.print.assert_any_call(" " * len(test_message), end="\r")


class TestOperationMessageHelpers(unittest.TestCase):
    """Test the operation message helper functions in cli/utils.py."""

    def test_operation_complete_prints_success_message(self):
        """Test that operation_complete prints a success message."""
        # Create mock console
        mock_console = MagicMock()
        test_message = "Operation successful"

        # Call the function
        operation_complete(mock_console, test_message)

        # Verify console print was called with correct format
        mock_console.print.assert_called_once_with(f"[bold green]✓[/bold green] {test_message}")

    def test_operation_error_prints_error_message(self):
        """Test that operation_error prints an error message."""
        # Create mock console
        mock_console = MagicMock()
        test_message = "Operation failed"

        # Call the function
        operation_error(mock_console, test_message)

        # Verify console print was called with correct format
        mock_console.print.assert_called_once_with(f"[bold red]✗[/bold red] {test_message}")

    def test_operation_warning_prints_warning_message(self):
        """Test that operation_warning prints a warning message."""
        # Create mock console
        mock_console = MagicMock()
        test_message = "Operation warning"

        # Call the function
        operation_warning(mock_console, test_message)

        # Verify console print was called with correct format
        mock_console.print.assert_called_once_with(f"[bold yellow]![/bold yellow] {test_message}")

    def test_step_progress_prints_progress_message(self):
        """Test that step_progress prints a progress message."""
        # Create mock console
        mock_console = MagicMock()
        test_message = "Step in progress"

        # Call the function
        step_progress(mock_console, test_message)

        # Verify console print was called with correct format
        mock_console.print.assert_called_once_with(f"[bold cyan]→[/bold cyan] {test_message}")


class TestRunCli(unittest.TestCase):
    """Test the run_cli function in cli/utils.py."""

    @pytest.mark.skip(reason="Requires mocking stdin for interactive prompt")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("asyncio.run")
    def test_run_cli_with_basic_args(self, mock_asyncio_run, mock_prompt_ask, mock_console_class):
        """Test run_cli with basic arguments."""
        # Create mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock Prompt.ask to return a test instruction
        mock_prompt_ask.return_value = "Test instruction"

        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent.tools = []

        # Create mock session service
        mock_session_service = MagicMock()

        # Call run_cli with minimal parameters
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            session_service=mock_session_service,
        )

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

    @pytest.mark.skip(reason="Requires mocking stdin for interactive prompt")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("asyncio.run")
    def test_run_cli_with_interactive_mode(self, mock_asyncio_run, mock_prompt_ask, mock_console_class):
        """Test run_cli with interactive mode enabled."""
        # Create mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock Prompt.ask to return a test instruction
        mock_prompt_ask.return_value = "Test instruction"

        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent.tools = []

        # Create mock session service
        mock_session_service = MagicMock()

        # Call run_cli with interactive=True
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            session_service=mock_session_service,
            interactive=True,
        )

        # Verify asyncio.run was called
        mock_asyncio_run.assert_called_once()

        # Verify console.print was called with interactive mode message (this may be different depending on code)
        mock_console.print.assert_any_call("[yellow]Starting in interactive mode without an initial instruction.[/yellow]")


class TestSetupLogging(unittest.TestCase):
    """Test the setup_logging function in cli/utils.py."""

    @patch("code_agent.cli.utils.logging")
    def test_setup_logging_with_verbosity_3_sets_debug(self, mock_logging):
        """Test that setup_logging with verbosity 3 sets the log level to DEBUG."""
        # Create mock logger
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        # No handlers initially
        mock_logger.handlers = []

        # Call the function
        setup_logging(3)

        # Verify log level was set to DEBUG
        mock_logger.setLevel.assert_called_once_with(mock_logging.DEBUG)

        # Verify a handler was added and its level set to DEBUG
        self.assertEqual(len(mock_logger.addHandler.call_args_list), 1)

        # Verify debug message was logged
        mock_logging.debug.assert_any_call("No handlers found, added default StreamHandler.")

        # Check that the debugging message about level was logged
        level_name = mock_logging.getLevelName(mock_logging.DEBUG)
        mock_logging.debug.assert_any_call(f"Logging configured to level: {level_name} (Verbosity: 3)")

    @patch("code_agent.cli.utils.logging")
    def test_setup_logging_with_existing_handlers(self, mock_logging):
        """Test that setup_logging sets level on existing handlers."""
        # Create mock logger
        mock_logger = MagicMock()
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]
        mock_logging.getLogger.return_value = mock_logger

        # Call the function
        setup_logging(2)  # INFO level

        # Verify log level was set on the logger
        mock_logger.setLevel.assert_called_once_with(mock_logging.INFO)

        # Verify log level was set on the existing handler
        mock_handler.setLevel.assert_called_once_with(mock_logging.INFO)

        # Verify no new handlers were added
        mock_logger.addHandler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
