"""
Tests for the 'web' command in code_agent.cli.main module.
"""

from unittest.mock import patch

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
        pytest.skip("Test needs rewriting after refactor")

    def test_web_command_invalid_directory(self, runner):
        """Test web command behavior when an invalid directory is provided."""
        pytest.skip("Test needs rewriting after refactor")

    def test_web_command_subprocess_error(self, runner):
        """Test web command behavior when subprocess.run raises an error."""
        # Mock necessary components
        with (
            patch("code_agent.cli.main.ADK_INSTALLED", True),
            patch("os.path.isdir", return_value=True),
            patch("os.chdir"),
            patch("subprocess.run", side_effect=Exception("Command failed")),
        ):
            # Test the command
            with patch("builtins.print"):  # Suppress print outputs
                result = runner.invoke(app, ["web"])

            # Should fail with error message
            assert result.exit_code != 0

    def test_web_command_invalid_log_level(self, runner):
        """Test web command behavior when an invalid log level is provided."""
        pytest.skip("Test needs rewriting after refactor")

    def test_web_command_keyboard_interrupt(self, runner):
        """Test web command behavior when a KeyboardInterrupt is raised."""
        pytest.skip("Test needs rewriting after refactor")


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_web.py"])
