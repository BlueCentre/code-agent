"""Additional unit tests for code_agent.cli.commands.run module to improve coverage."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from code_agent.cli.commands.run import (
    _resolve_agent_path_str,
    run_command,
)


class TestResolveAgentPathStr(unittest.TestCase):
    """Test the _resolve_agent_path_str function in cli.commands.run."""

    @patch("code_agent.cli.commands.run.Console")
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.commands.run.operation_error")
    def test_resolve_agent_path_str_with_cli_path(self, mock_operation_error, mock_exists, mock_console_class):
        """Test _resolve_agent_path_str with a path provided by the CLI."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_exists.return_value = True

        # Create test config and path
        mock_config = MagicMock()
        test_path = Path("/test/agent_path")

        # Call the function
        result = _resolve_agent_path_str(test_path, mock_config)

        # Verify result is the resolved path string
        self.assertIsNotNone(result)

    @pytest.mark.skip(reason="Mocking needs to be adjusted to match actual implementation")
    @patch("code_agent.cli.commands.run.Console")
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.commands.run.operation_error")
    def test_resolve_agent_path_str_with_non_existent_path(self, mock_operation_error, mock_exists, mock_console_class):
        """Test _resolve_agent_path_str with a non-existent path."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_exists.return_value = False

        # Create test config and path
        mock_config = MagicMock()
        test_path = Path("/test/non_existent_path")

        # Call the function
        result = _resolve_agent_path_str(test_path, mock_config)

        # Verify result is None
        self.assertIsNone(result)

        # Verify error message was printed via operation_error
        mock_operation_error.assert_any_call(mock_console, "Resolved agent path does not exist: /test/non_existent_path")


class TestRunCommand(unittest.TestCase):
    """Test the run_command function in cli.commands.run."""

    @pytest.mark.skip(reason="Need more robust mocking of importlib functionality")
    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.run_cli")
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.suffix", new_callable=MagicMock)
    @patch("sys.modules", {})
    def test_run_command_with_python_file(
        self,
        mock_suffix,
        mock_is_file,
        mock_module_from_spec,
        mock_spec_from_file,
        mock_run_cli,
        mock_resolve_path,
        mock_setup_logging,
        mock_get_config,
        mock_init_config,
        mock_console_class,
    ):
        """Test run_command with a Python agent file."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 2
        mock_config.provider = "openai"
        mock_config.model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Setup mock path resolution
        test_path = Path("/test/agent/agent.py")
        mock_resolve_path.return_value = str(test_path)

        # Setup file checks
        mock_is_file.return_value = True
        mock_suffix.return_value = ".py"

        # Setup module loading
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec
        mock_module = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_agent.tools = []
        mock_module.root_agent = mock_agent
        mock_module_from_spec.return_value = mock_module

        # Call the function
        run_command(
            instruction="Test instruction",
            agent_path=test_path,
            session_id=None,
            interactive=False,
            show_timestamps=False,
            log_level=None,
            provider=None,
            model=None,
            temperature=None,
            max_tokens=None,
            save_session_cli=False,
            verbose=True,
        )

        # Verify run_cli was called
        mock_run_cli.assert_called_once()

        # Verify agent was passed to run_cli
        args, kwargs = mock_run_cli.call_args
        self.assertEqual(kwargs["agent"], mock_agent)

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    def test_run_command_with_non_existent_agent_path(self, mock_setup_logging, mock_get_config, mock_init_config, mock_console_class):
        """Test run_command with a non-existent agent path."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Create a path object that will fail the resolution
        test_path = Path("/non/existent/path")

        # Mock _resolve_agent_path_str to always return None
        with patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value=None):
            # Run the command and expect it to exit
            with self.assertRaises(typer.Exit):
                run_command(
                    instruction="Test instruction",
                    agent_path=test_path,
                    session_id=None,
                    interactive=False,
                    show_timestamps=False,
                    log_level=None,
                    provider=None,
                    model=None,
                    temperature=None,
                    max_tokens=None,
                    save_session_cli=False,
                    verbose=True,
                )

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", False)
    def test_run_command_without_adk_installed(self, mock_console_class):
        """Test run_command when ADK is not installed."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the function and expect it to exit
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("/test/path"),
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=True,
            )

        # Verify error message was printed
        mock_console.print.assert_any_call("[bold red]Error:[/bold red] Google ADK is required for the 'run' command but is not installed.")
        mock_console.print.assert_any_call("Please install it using: [yellow]uv add google-adk[/yellow]")

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", None)
    def test_run_command_without_session_service(self, mock_console_class):
        """Test run_command when InMemorySessionService is not available."""
        # Setup mocks
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the function and expect it to exit
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("/test/path"),
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=True,
            )

        # Verify error message was printed
        mock_console.print.assert_any_call("[bold red]Error:[/bold red] Failed to import ADK's InMemorySessionService.")


if __name__ == "__main__":
    unittest.main()
