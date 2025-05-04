"""
Tests for path resolution functions in code_agent.cli.utils module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from code_agent.cli.utils import _resolve_agent_path_str


class TestPathResolution:
    """Tests for path resolution functions."""

    def test_resolve_agent_path_from_cli_arg(self):
        """Test resolving agent path from CLI argument."""
        # Create a mock for the config
        mock_cfg = MagicMock()
        mock_cfg.default_agent_path = None

        # Create a temporary path that exists
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.resolve", return_value=Path("/mock/path/agent.py")):
                # Call the function with a CLI path
                result = _resolve_agent_path_str(Path("agent.py"), mock_cfg)

                # Verify the result matches the expected path
                assert result == "/mock/path/agent.py"

    def test_resolve_agent_path_from_config(self):
        """Test resolving agent path from config when CLI arg is not provided."""
        # Create a mock for the config with a default path
        mock_cfg = MagicMock()
        mock_cfg.default_agent_path = Path("/config/path/agent.py")

        # Mock the path.exists check to return True
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.resolve", return_value=Path("/config/path/agent.py")):
                # Call the function without a CLI path
                result = _resolve_agent_path_str(None, mock_cfg)

                # Verify the result matches the config path
                assert result == "/config/path/agent.py"

    def test_resolve_agent_path_fallback_to_current_dir(self):
        """Test resolving agent path defaults to current directory when no paths are provided."""
        # Create a mock for the config with no default path
        mock_cfg = MagicMock()
        mock_cfg.default_agent_path = None

        # Mock path.exists and Console
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.resolve", return_value=Path("/current/dir")):
                with patch("code_agent.cli.utils.Console") as mock_console_class:
                    mock_console = MagicMock()
                    mock_console_class.return_value = mock_console

                    # Call the function without any paths
                    result = _resolve_agent_path_str(None, mock_cfg)

                    # Verify the result is the current directory
                    assert result == "/current/dir"

                    # Verify warning was printed
                    mock_console.print.assert_called_once()
                    assert "Warning" in mock_console.print.call_args[0][0]

    def test_resolve_agent_path_nonexistent_path(self):
        """Test resolving agent path when the path doesn't exist."""
        # Create a mock for the config
        mock_cfg = MagicMock()
        mock_cfg.default_agent_path = None

        # Mock path.exists to return False (path doesn't exist)
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.resolve", return_value=Path("/nonexistent/path")):
                with patch("code_agent.cli.utils.Console") as mock_console_class:
                    mock_console = MagicMock()
                    mock_console_class.return_value = mock_console

                    # Call the function with a nonexistent path
                    result = _resolve_agent_path_str(Path("/nonexistent/path"), mock_cfg)

                    # Verify the result is None
                    assert result is None

                    # Verify error was printed
                    mock_console.print.assert_called()
                    # Check for error indicators in the error message
                    error_call_args = [args[0] for args in mock_console.print.call_args_list]
                    assert any("does not exist" in str(arg) for arg in error_call_args)
