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

    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.Console")
    def test_missing_adk(self, mock_console_class, mock_setup_logging, mock_init_config, mock_get_config):
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
                assert exc_info.value.code == 1

                # Verify error message is printed
                mock_console.print.assert_any_call("[bold red]Error:[/bold red] Google ADK is required for the 'run' command but is not installed.")
                mock_console.print.assert_any_call("Please install it using: [yellow]uv add google-adk[/yellow]")

    @patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value=None)
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    def test_agent_path_resolution_error(self, mock_setup_logging, mock_init_config, mock_get_config, mock_resolve_path):
        """Test error handling when agent path resolution fails."""
        # Arrange
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg

        # Act & Assert - Should raise typer.Exit
        with pytest.raises(typer.Exit) as exc_info:
            run_command("Test instruction", agent_path=None)

        # Verify exit code is 1
        assert exc_info.value.code == 1

        # Verify _resolve_agent_path_str was called
        mock_resolve_path.assert_called_once()

    @patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value="/fake/path/agent.py")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location", return_value=None)
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.Path.is_file", return_value=True)
    @patch("code_agent.cli.commands.run.Path.suffix", ".py")
    @patch("code_agent.cli.commands.run.thinking_indicator")
    def test_module_import_error(
        self, mock_thinking, mock_suffix, mock_is_file, mock_console_class, mock_setup_logging, mock_init_config, mock_get_config, mock_spec_from_file
    ):
        """Test error handling when module import fails."""
        # Arrange
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg
        mock_thinking.return_value.__enter__.return_value = None

        # Act & Assert - should raise ImportError
        with pytest.raises(ImportError) as exc_info:
            run_command("Test instruction", agent_path=Path("/fake/path/agent.py"))

        # Verify error message
        assert "Could not create module spec" in str(exc_info.value)

        # Verify spec_from_file_location was called
        mock_spec_from_file.assert_called_once()

    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.Path.is_file", return_value=False)
    @patch("code_agent.cli.commands.run.Path.is_dir", return_value=False)
    @patch("code_agent.cli.commands.run.thinking_indicator")
    def test_invalid_agent_path(
        self, mock_thinking, mock_is_dir, mock_is_file, mock_console_class, mock_setup_logging, mock_init_config, mock_get_config, mock_resolve_path
    ):
        """Test error handling when agent path is invalid."""
        # Arrange
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg
        mock_resolve_path.return_value = "/fake/path/not_file_or_dir"
        mock_thinking.return_value.__enter__.return_value = None

        # Act & Assert - should raise ImportError
        with pytest.raises(ImportError) as exc_info:
            run_command("Test instruction", agent_path=Path("/fake/path/not_file_or_dir"))

        # Verify error message
        assert "Agent path is neither a Python file nor a directory" in str(exc_info.value)

        # Verify is_file and is_dir were called
        mock_is_file.assert_called_once()
        mock_is_dir.assert_called_once()

    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.Path.is_file", return_value=False)
    @patch("code_agent.cli.commands.run.Path.is_dir", return_value=True)
    @patch("code_agent.cli.commands.run.thinking_indicator")
    @patch("code_agent.cli.commands.run.importlib.import_module", side_effect=ImportError("Cannot import module"))
    def test_package_import_error(
        self,
        mock_import_module,
        mock_thinking,
        mock_is_dir,
        mock_is_file,
        mock_console_class,
        mock_setup_logging,
        mock_init_config,
        mock_get_config,
        mock_resolve_path,
    ):
        """Test error handling when package import fails."""
        # Arrange
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_cfg = MagicMock()
        mock_get_config.return_value = mock_cfg
        mock_resolve_path.return_value = "/fake/path/agent_dir"
        mock_thinking.return_value.__enter__.return_value = None

        # Act & Assert - should raise ImportError
        with pytest.raises(ImportError) as exc_info:
            run_command("Test instruction", agent_path=Path("/fake/path/agent_dir"))

        # Verify error message
        assert "Could not import agent package" in str(exc_info.value)

        # Verify import_module was called
        mock_import_module.assert_called_once()
