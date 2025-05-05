"""
Tests for CLI run operations in code_agent.cli.utils module.
"""

import signal
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from rich.console import Console

from code_agent.cli.utils import run_cli, thinking_indicator


class TestThinkingIndicatorContext:
    """Tests for the thinking_indicator context manager."""

    def test_thinking_indicator_context_manager(self):
        """Test the thinking_indicator context manager."""
        # Setup mock console
        mock_console = MagicMock(spec=Console)

        # Use the context manager
        with thinking_indicator(mock_console, "Thinking..."):
            # Should have printed the message
            mock_console.print.assert_called_once()
            assert "Thinking..." in mock_console.print.call_args[0][0]
            assert mock_console.print.call_args[1]["end"] == "\r"
            mock_console.print.reset_mock()

        # Should have cleared the line after exiting
        mock_console.print.assert_called_once()
        assert mock_console.print.call_args[1]["end"] == "\r"


class TestRunCli:
    """Test for the run_cli function."""

    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_run_cli_with_instruction(self, mock_asyncio_run, mock_console_class, mock_signal, mock_prompt_ask, mock_runner_class):
        """Test run_cli with a provided instruction."""
        # Setup mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        mock_session = MagicMock()
        mock_session_service = MagicMock()

        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Set up mock async function
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Mock the process_message_async generator
        run_async_mock = AsyncMock()
        mock_runner.run_async.return_value = run_async_mock

        # Call run_cli with a provided instruction
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            user_id="test_user",
            session_id="test_session_id",
            interactive=False,
            session=mock_session,
            session_service=mock_session_service,
            initial_instruction="Test instruction",
        )

        # Verify Runner was initialized correctly
        mock_runner_class.assert_called_once_with(session_service=mock_session_service, app_name="test_app", agent=mock_agent, memory_service=None)

        # Verify signal handler was set up
        mock_signal.assert_called_with(signal.SIGINT, ANY)

        # Verify the console printed the instruction
        mock_console.print.assert_any_call("[bold cyan]User (Initial Instruction):[/bold cyan] Test instruction")

        # Verify prompt was not called since instruction was provided
        mock_prompt_ask.assert_not_called()

        # Verify asyncio.run was called to process the message
        mock_asyncio_run.assert_called_once()

    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_run_cli_prompt_for_instruction(self, mock_asyncio_run, mock_console_class, mock_signal, mock_prompt_ask, mock_runner_class):
        """Test run_cli when instruction is not provided."""
        # Setup mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        mock_session = MagicMock()
        mock_session_service = MagicMock()

        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Set up mock async function
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Mock the prompt to return an instruction
        mock_prompt_ask.return_value = "User prompted instruction"

        # Call run_cli without an instruction
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            user_id="test_user",
            session_id=None,
            interactive=False,
            session=mock_session,
            session_service=mock_session_service,
            initial_instruction=None,
        )

        # Verify the prompt was called to get the instruction
        mock_prompt_ask.assert_called_once()

        # Verify asyncio.run was called to process the message
        mock_asyncio_run.assert_called_once()

    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_run_cli_interactive_mode(self, mock_asyncio_run, mock_console_class, mock_signal, mock_prompt_ask, mock_runner_class):
        """Test run_cli in interactive mode."""
        # Setup mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        mock_session = MagicMock()
        mock_session_service = MagicMock()

        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Set up mock async function
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Call run_cli in interactive mode with instruction
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            user_id="test_user",
            session_id=None,
            interactive=True,
            session=mock_session,
            session_service=mock_session_service,
            initial_instruction="Initial instruction",
        )

        # Should run asyncio.run twice - once for initial instruction, once for interactive mode
        assert mock_asyncio_run.call_count == 2

    @patch("code_agent.cli.utils.Runner")
    @patch("code_agent.cli.utils.Prompt.ask")
    @patch("code_agent.cli.utils.signal.signal")
    @patch("code_agent.cli.utils.Console")
    @patch("code_agent.cli.utils.asyncio.run")
    def test_run_cli_interactive_mode_no_instruction(self, mock_asyncio_run, mock_console_class, mock_signal, mock_prompt_ask, mock_runner_class):
        """Test run_cli in interactive mode without initial instruction."""
        # Setup mocks
        mock_console = MagicMock(spec=Console)
        mock_console_class.return_value = mock_console

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        mock_session = MagicMock()
        mock_session_service = MagicMock()

        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Set up mock async function for interactive mode
        mock_asyncio_run.return_value = ("test_session_id", True)

        # Call run_cli in interactive mode without instruction
        run_cli(
            agent=mock_agent,
            app_name="test_app",
            user_id="test_user",
            session_id=None,
            interactive=True,
            session=mock_session,
            session_service=mock_session_service,
            initial_instruction=None,
        )

        # Should print interactive mode message
        mock_console.print.assert_any_call("[yellow]Starting in interactive mode without an initial instruction.[/yellow]")

        # Should run asyncio.run only once for interactive mode, skipping initial instruction
        mock_asyncio_run.assert_called_once()
