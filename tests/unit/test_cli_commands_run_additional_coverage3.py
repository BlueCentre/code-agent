"""Additional unit tests for code_agent.cli.commands.run module to improve coverage."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from code_agent.cli.commands.run import _resolve_agent_path_str, run_command


class TestRunCommand(unittest.TestCase):
    """Test the run_command function and helper functions."""

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location")
    @patch("code_agent.cli.commands.run.importlib.util.module_from_spec")
    @patch("code_agent.cli.commands.run.FileSystemSessionService")
    @patch("code_agent.cli.commands.run.JsonFileMemoryService")
    @patch("code_agent.cli.commands.run.operation_complete")
    @patch("code_agent.cli.commands.run.run_cli")
    def test_run_command_with_valid_agent(
        self,
        mock_run_cli,
        mock_operation_complete,
        mock_memory_service,
        mock_session_service,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_resolve_agent_path,
        mock_get_config,
        mock_init_config,
        mock_console_class,
    ):
        """Test run_command with a valid agent path."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock config
        mock_config = MagicMock()
        mock_config.sessions_dir = "/tmp/sessions"
        mock_get_config.return_value = mock_config

        # Mock agent path resolution
        mock_agent_path = Path("/path/to/agent.py")
        mock_resolve_agent_path.return_value = str(mock_agent_path)

        # Mock importlib for agent loading
        mock_spec = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        # Setup mock agent
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_module.root_agent = mock_agent

        # Mock services
        mock_fs_service = MagicMock()
        mock_session_service.return_value = mock_fs_service
        mock_mem_service = MagicMock()
        mock_memory_service.return_value = mock_mem_service

        # Mock is_file and suffix to prevent ImportError
        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.is_file", return_value=True), patch.object(Path, "suffix", ".py", create=True):
            run_command(
                instruction="Test instruction",
                agent_path=Path("agent.py"),
                interactive=True,
                show_timestamps=True,
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify agent path was resolved
        mock_resolve_agent_path.assert_called_once()

        # Verify spec_from_file_location was called
        mock_spec_from_file_location.assert_called_once()

        # Verify run_cli was called with correct parameters
        mock_run_cli.assert_called_once()
        args, kwargs = mock_run_cli.call_args
        self.assertEqual(kwargs["agent"], mock_agent)
        self.assertEqual(kwargs["initial_instruction"], "Test instruction")
        self.assertEqual(kwargs["interactive"], True)
        self.assertEqual(kwargs["show_timestamps"], True)
        self.assertEqual(kwargs["session_service"], mock_fs_service)
        self.assertEqual(kwargs["memory_service"], mock_mem_service)

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.operation_error")
    def test_run_command_with_agent_path_resolution_failure(
        self,
        mock_operation_error,
        mock_resolve_agent_path,
        mock_get_config,
        mock_init_config,
        mock_console_class,
    ):
        """Test run_command when agent path resolution fails."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock config
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        # Mock agent path resolution to fail
        mock_resolve_agent_path.return_value = None

        # The error message is shown in _resolve_agent_path_str, not in run_command
        # We don't expect operation_error to be called in run_command itself

        # We expect the function to raise a typer.Exit
        with pytest.raises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("nonexistent.py"),
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify agent path resolution was attempted
        mock_resolve_agent_path.assert_called_once()

        # In the actual implementation, operation_error is not called when path resolution fails
        # It directly calls typer.Exit instead
        mock_operation_error.assert_not_called()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location")
    @patch("code_agent.cli.commands.run.operation_error")
    def test_run_command_with_agent_import_error(
        self,
        mock_operation_error,
        mock_spec_from_file_location,
        mock_resolve_agent_path,
        mock_get_config,
        mock_init_config,
        mock_console_class,
    ):
        """Test run_command when agent import fails."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock config
        mock_config = MagicMock()
        mock_config.sessions_dir = "/tmp/sessions"
        mock_get_config.return_value = mock_config

        # Mock agent path resolution
        mock_agent_path = Path("/path/to/agent.py")
        mock_resolve_agent_path.return_value = str(mock_agent_path)

        # Mock importlib to fail
        mock_spec_from_file_location.return_value = None

        # We expect the function to raise a typer.Exit
        with pytest.raises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("agent.py"),
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify agent path resolution was attempted
        mock_resolve_agent_path.assert_called_once()

        # Verify error was shown
        mock_operation_error.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location")
    @patch("code_agent.cli.commands.run.importlib.util.module_from_spec")
    @patch("code_agent.cli.commands.run.operation_error")
    def test_run_command_with_session_dir_creation_failure(
        self,
        mock_operation_error,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_resolve_agent_path,
        mock_get_config,
        mock_init_config,
        mock_console_class,
    ):
        """Test run_command when sessions directory creation fails."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Mock config
        mock_config = MagicMock()
        mock_config.sessions_dir = "/tmp/sessions"
        mock_get_config.return_value = mock_config

        # Mock agent path resolution
        mock_agent_path = Path("/path/to/agent.py")
        mock_resolve_agent_path.return_value = str(mock_agent_path)

        # Mock agent import
        mock_spec = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec
        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module
        mock_module.root_agent = MagicMock()

        # Mock directory check and creation to fail
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")

            # We expect the function to raise a typer.Exit
            with pytest.raises(typer.Exit):
                run_command(
                    instruction="Test instruction",
                    agent_path=Path("agent.py"),
                )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify agent path resolution was attempted
        mock_resolve_agent_path.assert_called_once()

        # Verify error was shown
        mock_operation_error.assert_called_once()


class TestResolveAgentPath(unittest.TestCase):
    """Test the _resolve_agent_path_str function."""

    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_with_valid_path(self, mock_console_class, mock_exists, mock_resolve):
        """Test _resolve_agent_path_str with a valid path."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Set up a valid path
        mock_exists.return_value = True
        path = Path("/path/to/agent.py")
        mock_resolve.return_value = path

        # Create a mock config
        mock_config = MagicMock()
        mock_config.default_agent_path = None

        # Call the function
        result = _resolve_agent_path_str(path, mock_config)

        # Verify the result
        self.assertEqual(result, str(path))

    @patch("code_agent.cli.utils.operation_error")
    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.utils.Console")
    def test_resolve_agent_path_str_with_nonexistent_path(self, mock_console_class, mock_exists, mock_resolve, mock_operation_error):
        """Test _resolve_agent_path_str with a nonexistent path."""
        # Setup
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Set up a nonexistent path
        mock_exists.return_value = False
        path = Path("nonexistent.py")
        mock_resolve.return_value = path

        # Create a mock config
        mock_config = MagicMock()
        mock_config.default_agent_path = None  # No default

        # Call the function
        result = _resolve_agent_path_str(path, mock_config)

        # Verify the result (should be None)
        self.assertIsNone(result)

        # In the actual implementation, operation_error is called multiple times
        mock_operation_error.assert_any_call(mock_console, f"Resolved agent path does not exist: {path}")
        mock_operation_error.assert_any_call(mock_console, "(Path was provided via command line argument)")

    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    @patch("logging.debug")
    def test_resolve_agent_path_str_with_default_from_config(self, mock_logging_debug, mock_exists, mock_resolve):
        """Test _resolve_agent_path_str with default path from config."""
        # Create paths for testing - use None directly for cli_path
        cli_path = None  # No CLI path provided
        default_path = Path("/default/agent.py")

        # Set up mock behavior
        mock_exists.return_value = True
        mock_resolve.return_value = default_path

        # Create a mock config with a default path
        mock_config = MagicMock()
        mock_config.default_agent_path = default_path

        # Call the function directly with None for cli_path (no CLI arg)
        with patch("code_agent.cli.utils.Console"):
            result = _resolve_agent_path_str(cli_path, mock_config)

        # Verify the result is the default path
        self.assertEqual(result, str(default_path))

        # Verify the debug log was called with the right message
        mock_logging_debug.assert_any_call(f"Using default agent path from config: {default_path}")


if __name__ == "__main__":
    unittest.main()
