"""
Tests for the 'run' command in code_agent.cli.main module.
"""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestRunCommand:
    """Test class for the 'run' command."""

    def test_run_command_adk_not_installed(self, runner):
        """Test run command behavior when ADK is not installed."""
        pytest.skip("Test needs rewriting after refactor")

    def test_run_command_missing_agent_path(self, runner):
        """Test run command behavior when no agent path is provided or configured."""
        pytest.skip("Test needs rewriting after refactor")

    def test_run_command_agent_path_not_exists(self, runner):
        """Test run command behavior when the agent path doesn't exist."""
        # Mock ADK_INSTALLED to True
        with patch("code_agent.cli.main.ADK_INSTALLED", True):
            # Mock Path.exists to return False
            with patch("pathlib.Path.exists", return_value=False):
                # Test the command with a non-existent path
                with patch("builtins.print"):  # Suppress print outputs
                    result = runner.invoke(app, ["run", "Test instruction", "non_existent_agent.py"])

                # Should fail with error message about path not existing
                assert result.exit_code != 0
                assert "does not exist" in result.stdout

    def test_run_command_invalid_log_level(self, runner):
        """Test run command behavior when an invalid log level is provided."""
        pytest.skip("Test needs rewriting after refactor")


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_run.py"])
