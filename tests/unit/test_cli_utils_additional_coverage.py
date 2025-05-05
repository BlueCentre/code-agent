"""
Tests to increase coverage for code_agent.cli.utils module,
focusing on the run_cli function and its async helpers.
"""

from unittest.mock import MagicMock, patch

from rich.console import Console

from code_agent.cli.utils import (
    load_config_data,
    operation_complete,
    operation_error,
    operation_warning,
    run_cli,
    save_config_data,
    step_progress,
    thinking_indicator,
)


class TestRunCliAsyncHelpers:
    """Tests for the async helper functions used by run_cli."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.InMemorySessionService")
    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_process_message_async_indirectly(self, mock_asyncio_run, mock_runner_class, mock_session_service, mock_console_class):
        """Test the process_message_async inner function of run_cli indirectly."""
        # Create mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_session_service_instance = MagicMock()
        mock_session_service.return_value = mock_session_service_instance

        mock_runner_instance = MagicMock()
        mock_runner_class.return_value = mock_runner_instance

        # Mock asyncio.run to return a session ID and success flag
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Call run_cli with the minimum required arguments
        result = run_cli(agent=MagicMock(), app_name="test_app", user_id="test_user", initial_instruction="Test message")

        # Verify asyncio.run was called once (to run process_message_async)
        mock_asyncio_run.assert_called_once()

        # Verify we got back the session ID from asyncio.run
        assert result == "test_session_id"

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.InMemorySessionService")
    @patch("code_agent.cli.utils.asyncio.run")
    @patch("code_agent.cli.utils.Prompt")
    def test_run_interactively_async_indirectly(self, mock_prompt, mock_asyncio_run, mock_session_service, mock_console_class):
        """Test the run_interactively_async inner function of run_cli indirectly."""
        # Create mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_session_service_instance = MagicMock()
        mock_session_service.return_value = mock_session_service_instance

        # First async call returns a session ID
        mock_asyncio_run.side_effect = [
            ("test_session_id", True),  # process_message_async
            "interactive_session_id",  # run_interactively_async
        ]

        # Call run_cli with interactive=True
        result = run_cli(agent=MagicMock(), app_name="test_app", user_id="test_user", initial_instruction="Test message", interactive=True)

        # Verify asyncio.run was called twice (once for process_message_async, once for run_interactively_async)
        assert mock_asyncio_run.call_count == 2

        # Verify we got back the session ID from the second asyncio.run call (run_interactively_async)
        assert result == "interactive_session_id"


class TestConsoleHelpers:
    """Tests for the console helper functions in utils.py."""

    def test_thinking_indicator(self):
        """Test the thinking_indicator context manager."""
        mock_console = MagicMock(spec=Console)
        message = "Thinking..."

        with thinking_indicator(mock_console, message):
            # Check that the thinking message was printed
            mock_console.print.assert_called_with(f"[dim]{message}[/dim]", end="\r")

        # Check that the line was cleared
        mock_console.print.assert_called_with(" " * len(message), end="\r")

    def test_operation_complete(self):
        """Test the operation_complete function."""
        mock_console = MagicMock(spec=Console)
        message = "Operation complete"

        operation_complete(mock_console, message)

        mock_console.print.assert_called_with(f"[bold green]✓[/bold green] {message}")

    def test_operation_error(self):
        """Test the operation_error function."""
        mock_console = MagicMock(spec=Console)
        message = "Operation failed"

        operation_error(mock_console, message)

        mock_console.print.assert_called_with(f"[bold red]✗[/bold red] {message}")

    def test_operation_warning(self):
        """Test the operation_warning function."""
        mock_console = MagicMock(spec=Console)
        message = "Operation warning"

        operation_warning(mock_console, message)

        mock_console.print.assert_called_with(f"[bold yellow]![/bold yellow] {message}")

    def test_step_progress(self):
        """Test the step_progress function."""
        mock_console = MagicMock(spec=Console)
        message = "Step in progress"

        step_progress(mock_console, message)

        mock_console.print.assert_called_with(f"[bold cyan]→[/bold cyan] {message}")


class TestConfigHelpers:
    """Tests for the config helper functions in utils.py."""

    @patch("builtins.open", new_callable=MagicMock)
    @patch("yaml.safe_load")
    def test_load_config_data_empty_file(self, mock_safe_load, mock_open):
        """Test loading config data from an empty file."""
        # Set up mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        # Mock file content as empty
        mock_file = MagicMock()
        mock_file.read.return_value = ""
        mock_open.return_value.__enter__.return_value = mock_file

        # Call the function
        result = load_config_data(mock_path)

        # Check that the function returned an empty dict
        assert result == {}, "Should return empty dict for empty file"

        # Verify that safe_load was not called with empty content
        mock_safe_load.assert_not_called()

    @patch("builtins.open", new_callable=MagicMock)
    @patch("yaml.safe_dump")
    def test_save_config_data(self, mock_safe_dump, mock_open):
        """Test saving config data to a file."""
        # Set up mocks
        mock_path = MagicMock()
        mock_path.parent = MagicMock()

        # Call the function
        config_data = {"key": "value"}
        save_config_data(mock_path, config_data)

        # Verify directory was created
        mock_path.parent.mkdir.assert_called_with(parents=True, exist_ok=True)

        # Verify file was opened and data was dumped
        mock_open.assert_called_with(mock_path, "w")
        mock_safe_dump.assert_called_with(config_data, mock_open.return_value.__enter__.return_value, default_flow_style=False, sort_keys=False)


class TestSignalHandling:
    """Tests for the signal handling in run_cli."""

    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.signal")
    @patch("code_agent.cli.utils.InMemorySessionService")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_signal_handler_interactive(self, mock_asyncio_run, mock_session_service, mock_signal, mock_console_class):
        """Test the signal handler registration in run_cli."""
        # Create mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        # Mock asyncio.run to return session ID and success
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Run the function to test signal handler registration
        run_cli(agent=MagicMock(), app_name="test_app", interactive=False, initial_instruction="Test")

        # Verify that signal.signal was called with SIGINT
        mock_signal.signal.assert_called_with(mock_signal.SIGINT, mock_signal.signal.call_args[0][1])
