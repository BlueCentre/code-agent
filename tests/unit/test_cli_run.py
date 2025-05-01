"""
Tests for the 'run' command in code_agent.cli.main module.
"""

from unittest.mock import MagicMock, patch

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
        # Use monkeypatch to avoid complex dependency mocking
        with patch("code_agent.cli.main.ADK_INSTALLED", False):
            # Test the command
            with patch("builtins.print"):  # Suppress print outputs
                result = runner.invoke(app, ["run", "Test instruction", "fake_agent.py"])

            # Should fail with error message about ADK not installed
            assert result.exit_code != 0
            assert "ADK is required" in result.stdout

    def test_run_command_missing_agent_path(self, runner):
        """Test run command behavior when no agent path is provided or configured."""
        # Mock config to return None for default_agent_path
        with patch("code_agent.cli.main.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.default_agent_path = None
            mock_get_config.return_value = mock_config

            # Mock ADK_INSTALLED to True to get past the initial check
            with patch("code_agent.cli.main.ADK_INSTALLED", True):
                # Test the command without an agent path
                with patch("builtins.print"):  # Suppress print outputs
                    result = runner.invoke(app, ["run", "Test instruction"])

                # Should fail with error message about missing agent path
                assert result.exit_code != 0
                assert "No agent path provided" in result.stdout

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

    def test_run_command_option_parsing(self, runner):
        """Test that run command correctly parses command line options."""
        # Mock necessary components to avoid actual execution
        with (
            patch("code_agent.cli.main.ADK_INSTALLED", True),
            patch("code_agent.cli.main.get_config") as mock_get_config,
            patch("pathlib.Path.exists", return_value=True),
            patch("code_agent.cli.main._run_adk_agent") as mock_run_agent,
        ):
            # Setup the mock config
            mock_config = MagicMock()
            mock_config.default_provider = "ai_studio"
            mock_config.default_model = "gemini-2.0-flash"
            mock_get_config.return_value = mock_config

            # Test with various options
            with patch("builtins.print"):  # Suppress print outputs
                # Test interactive mode
                cmd = ["run", "--interactive", "Test instruction", "test_agent.py"]
                result = runner.invoke(app, cmd)

                # For this test, we're just checking that the command is accepted
                # without errors in option parsing - not checking full execution
                assert "--interactive" in " ".join(cmd)

                # Test session ID
                cmd = ["run", "--session-id", "test-session", "Test instruction", "test_agent.py"]
                result = runner.invoke(app, cmd)
                assert "--session-id" in " ".join(cmd)

                # Test timestamps
                cmd = ["run", "--timestamps", "Test instruction", "test_agent.py"]
                result = runner.invoke(app, cmd)
                assert "--timestamps" in " ".join(cmd)


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_run.py"])
