# ruff: noqa: F841
"""
Tests for error handling in code_agent.cli.commands.run module.
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from code_agent.cli.commands.run import run_command


class TestRunCommandErrorHandling:
    """Test error handling in the run_command function."""

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    def test_missing_adk(self, mock_get_config, mock_init_config, mock_setup_logging, mock_console_class):
        """Test error handling when ADK is not installed."""
        # Arrange
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg

        # Mock that ADK is not installed
        with patch.dict("sys.modules", {"code_agent.cli.commands.run": importlib.import_module("code_agent.cli.commands.run")}):
            with patch("code_agent.cli.commands.run.ADK_INSTALLED", False):
                # Act & Assert - Should raise typer.Exit
                with pytest.raises(typer.Exit) as exc_info:
                    run_command("Test instruction", agent_path=None)

                # Verify exit code is 1
                assert exc_info.value.exit_code == 1

                # Verify error message is printed
                mock_console.print.assert_any_call("[bold red]Error:[/bold red] Google ADK is required for the 'run' command but is not installed.")
                mock_console.print.assert_any_call("Please install it using: [yellow]uv add google-adk[/yellow]")

    def test_agent_path_resolution_error(self):
        """Test error handling when agent path resolution fails."""
        # Use context managers instead of decorators to avoid parameter ordering issues
        with (
            patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock()),
            patch("code_agent.cli.commands.run.ADK_INSTALLED", True),
            patch("code_agent.cli.commands.run.setup_logging") as mock_setup_logging,
            patch("code_agent.cli.commands.run.initialize_config") as mock_init_config,
            patch("code_agent.cli.commands.run.get_config") as mock_get_config,
            patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value=None) as mock_resolve_path,
        ):
            # Arrange
            mock_cfg = MagicMock()
            mock_get_config.return_value = mock_cfg

            # Act & Assert - Should raise typer.Exit
            with pytest.raises(typer.Exit) as exc_info:
                run_command("Test instruction", agent_path=None)

            # Verify exit code is 1
            assert exc_info.value.exit_code == 1

            # Verify _resolve_agent_path_str was called
            mock_resolve_path.assert_called_once()

    def test_module_import_error(self):
        """Test error handling when module import fails."""
        # Use context managers instead of decorators
        with (
            patch("code_agent.cli.commands.run.thinking_indicator") as mock_thinking,
            patch.object(Path, "suffix", ".py"),
            patch.object(Path, "is_file", return_value=True),
            patch("code_agent.cli.commands.run.Console") as mock_console_class,
            patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock()),
            patch("code_agent.cli.commands.run.ADK_INSTALLED", True),
            patch("code_agent.cli.commands.run.setup_logging") as mock_setup_logging,
            patch("code_agent.cli.commands.run.initialize_config") as mock_init_config,
            patch("code_agent.cli.commands.run.get_config") as mock_get_config,
            patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location", return_value=None) as mock_spec_from_file,
            patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value="/fake/path/agent.py") as mock_resolve_path,
        ):
            # Arrange
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            mock_cfg = MagicMock()
            mock_get_config.return_value = mock_cfg
            mock_thinking.return_value.__enter__.return_value = None

            # Mock operation_error function within the test
            with patch("code_agent.cli.commands.run.operation_error") as mock_operation_error:
                # Act & Assert - ImportError gets caught and converted to typer.Exit
                with pytest.raises(typer.Exit) as exc_info:
                    run_command("Test instruction", agent_path=Path("/fake/path/agent.py"))

                # Verify exit code is 1
                assert exc_info.value.exit_code == 1

                # Verify error message was printed using operation_error
                mock_operation_error.assert_any_call(mock_console, "Failed to load agent: Could not create module spec for /fake/path/agent.py")

            # Verify spec_from_file_location was called
            mock_spec_from_file.assert_called_once()

    def test_invalid_agent_path(self):
        """Test error handling when agent path is invalid."""
        # Use context managers instead of decorators
        with (
            patch("code_agent.cli.commands.run.thinking_indicator") as mock_thinking,
            patch.object(Path, "is_dir", return_value=False),
            patch.object(Path, "is_file", return_value=False),
            patch("code_agent.cli.commands.run.Console") as mock_console_class,
            patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock()),
            patch("code_agent.cli.commands.run.ADK_INSTALLED", True),
            patch("code_agent.cli.commands.run.setup_logging") as mock_setup_logging,
            patch("code_agent.cli.commands.run.initialize_config") as mock_init_config,
            patch("code_agent.cli.commands.run.get_config") as mock_get_config,
            patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value="/fake/path/not_file_or_dir") as mock_resolve_path,
        ):
            # Arrange
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            mock_cfg = MagicMock()
            mock_get_config.return_value = mock_cfg
            mock_thinking.return_value.__enter__.return_value = None

            # Mock operation_error function within the test
            with patch("code_agent.cli.commands.run.operation_error") as mock_operation_error:
                # Act & Assert - ImportError gets caught and converted to typer.Exit
                with pytest.raises(typer.Exit) as exc_info:
                    run_command("Test instruction", agent_path=Path("/fake/path/not_file_or_dir"))

                # Verify exit code is 1
                assert exc_info.value.exit_code == 1

                # Verify error message was printed
                mock_operation_error.assert_any_call(
                    mock_console, "Failed to load agent: Agent path is neither a Python file nor a directory: /fake/path/not_file_or_dir"
                )

    def test_package_import_error(self):
        """Test error handling when package import fails."""
        # Use context managers instead of decorators
        with (
            patch("code_agent.cli.commands.run.thinking_indicator") as mock_thinking,
            patch.object(Path, "is_dir", return_value=True),
            patch.object(Path, "is_file", return_value=False),
            patch("code_agent.cli.commands.run.Console") as mock_console_class,
            patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock()),
            patch("code_agent.cli.commands.run.ADK_INSTALLED", True),
            patch("code_agent.cli.commands.run.setup_logging") as mock_setup_logging,
            patch("code_agent.cli.commands.run.initialize_config") as mock_init_config,
            patch("code_agent.cli.commands.run.get_config") as mock_get_config,
            patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value="/fake/path/agent_dir") as mock_resolve_path,
            patch("code_agent.cli.commands.run.operation_error") as mock_operation_error,
        ):
            # Arrange
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            mock_cfg = MagicMock()
            mock_get_config.return_value = mock_cfg
            mock_thinking.return_value.__enter__.return_value = None

            # Create a custom mock object that raises an ImportError only for the specific import we need
            def mock_import_module(name, *args, **kwargs):
                if name == "agent_dir":
                    raise ImportError("Cannot import module")
                else:
                    # Use the real import for other modules
                    return importlib.import_module(name, *args, **kwargs)

            # Mock importlib.import_module with our custom mock
            with patch("code_agent.cli.commands.run.importlib.import_module", side_effect=mock_import_module):
                # Act & Assert - ImportError gets caught and converted to typer.Exit
                with pytest.raises(typer.Exit) as exc_info:
                    run_command("Test instruction", agent_path=Path("/fake/path/agent_dir"))

                # Verify exit code is 1
                assert exc_info.value.exit_code == 1

                # Verify error message was printed
                mock_operation_error.assert_any_call(
                    mock_console, "Failed to load agent: Could not import agent package 'agent_dir' from /fake/path/agent_dir: Cannot import module"
                )
