"""
Tests for the 'fastapi' command in code_agent.cli.main module.
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestFastAPICommand:
    """Test class for the 'fastapi' command."""

    def test_fastapi_command_adk_not_installed(self, runner):
        """Test fastapi command behavior when ADK is not installed."""
        # Use monkeypatch to avoid complex dependency mocking
        with patch("code_agent.cli.main.ADK_INSTALLED", False):
            # Test the command
            with patch("builtins.print"):  # Suppress print outputs
                result = runner.invoke(app, ["fastapi"])

            # Should fail with error message about ADK not installed
            assert result.exit_code != 0
            assert "ADK is required" in result.stdout

    def test_fastapi_command_invalid_directory(self, runner):
        """Test fastapi command behavior when an invalid directory is provided."""
        # Mock ADK_INSTALLED to True
        with patch("code_agent.cli.main.ADK_INSTALLED", True):
            # Mock os.path.isdir to return False for any path
            with patch("os.path.isdir", return_value=False):
                # Test the command with a non-existent path
                with patch("builtins.print"):  # Suppress print outputs
                    result = runner.invoke(app, ["fastapi", "non_existent_dir"])

                # Should fail with error message about invalid directory
                assert result.exit_code != 0
                assert "not a valid directory" in result.stdout

    def test_fastapi_command_subprocess_error(self, runner):
        """Test fastapi command behavior when subprocess.run raises an error."""
        # Mock necessary components
        with (
            patch("code_agent.cli.main.ADK_INSTALLED", True),
            patch("os.path.isdir", return_value=True),
            patch("os.chdir"),
            patch("subprocess.run", side_effect=Exception("Command failed")),
        ):
            # Test the command
            with patch("builtins.print"):  # Suppress print outputs
                result = runner.invoke(app, ["fastapi"])

            # Should fail with error message
            assert result.exit_code != 0


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_fastapi.py"])
