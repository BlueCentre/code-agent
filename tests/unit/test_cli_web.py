"""
Tests for the 'web' command in code_agent.cli.main module.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestWebCommand:
    """Test class for the 'web' command."""

    def test_web_command_adk_not_installed(self, runner):
        """Test web command behavior when ADK is not installed."""
        with patch("code_agent.adapters.adk_adapter.ADK_AVAILABLE", False):
            result = runner.invoke(app, ["web", "."])
            assert result.exit_code != 0
            assert "ADK is not available" in result.stdout or "Failed to create web app" in result.stdout

    def test_web_command_invalid_directory(self, runner):
        """Test web command behavior when an invalid directory is provided."""
        result = runner.invoke(app, ["web", "/path/does/not/exist"])
        assert result.exit_code != 0
        assert "Directory" in result.stdout or "Path" in result.stdout

    @patch("code_agent.adapters.web_adapter.create_web_app")
    @patch("asyncio.run")
    def test_web_command_success(self, mock_asyncio_run, mock_create_web_app, runner):
        """Test web command success path."""
        # Mock the necessary components
        mock_create_web_app.return_value = MagicMock()

        with patch("os.path.exists", return_value=True):
            result = runner.invoke(app, ["web", "."])

        # Should succeed
        assert result.exit_code == 0
        assert mock_create_web_app.called
        assert mock_asyncio_run.called

    @patch("code_agent.adapters.web_adapter.create_web_app")
    def test_web_command_server_error(self, mock_create_web_app, runner):
        """Test web command behavior when the server raises an error."""
        # Mock create_web_app to work but asyncio.run to fail
        mock_create_web_app.return_value = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("asyncio.run", side_effect=Exception("Server error")),
        ):
            result = runner.invoke(app, ["web", "."])

        # Should fail with error message
        assert result.exit_code != 0
        assert "Server error" in result.stdout or "Error" in result.stdout

    def test_web_command_invalid_log_level(self, runner):
        """Test web command behavior when an invalid log level is provided."""
        result = runner.invoke(app, ["web", ".", "--log-level", "INVALID_LEVEL"])
        assert result.exit_code != 0
        assert "log level" in result.stdout.lower() or "invalid" in result.stdout.lower()

    @patch("code_agent.adapters.web_adapter.create_web_app")
    @patch("asyncio.run", side_effect=KeyboardInterrupt)
    def test_web_command_keyboard_interrupt(self, mock_asyncio_run, mock_create_web_app, runner):
        """Test web command behavior when a KeyboardInterrupt is raised."""
        # Mock the necessary components
        mock_create_web_app.return_value = MagicMock()

        with patch("os.path.exists", return_value=True):
            result = runner.invoke(app, ["web", "."])

        # KeyboardInterrupt should be caught and handled gracefully
        assert "interrupt" in result.stdout.lower() or "stopped" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_web.py"])
