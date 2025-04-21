"""
Tests for the native_tools module to improve coverage.

These tests focus on edge cases and error handling in the native_tools module.
"""

from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.native_tools import (
    DANGEROUS_COMMAND_PREFIXES,
    RISKY_COMMAND_PREFIXES,
    run_native_command,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    with patch("code_agent.tools.native_tools.get_config") as mock_get_config:
        config = MagicMock()
        config.auto_approve_native_commands = False
        config.native_command_allowlist = ["ls", "echo", "pwd"]
        mock_get_config.return_value = config
        yield config


class TestRunNativeCommand:
    """Tests for the run_native_command function."""

    def test_user_cancels_command(self, mock_config):
        """Test that command execution is cancelled when the user declines."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=False):
            result = run_native_command("ls -la")
            assert "Command execution cancelled by user" in result

    def test_user_confirms_command(self, mock_config):
        """Test that command is executed when the user confirms."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_process = MagicMock()
                mock_process.stdout = "command output"
                mock_process.stderr = ""
                mock_process.returncode = 0
                mock_run.return_value = mock_process

                result = run_native_command("ls -la")
                assert result == "command output"
                mock_run.assert_called_once()

    def test_command_with_error(self, mock_config):
        """Test handling of commands that return an error code."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_process = MagicMock()
                mock_process.stdout = "command output"
                mock_process.stderr = "error message"
                mock_process.returncode = 1
                mock_run.return_value = mock_process

                result = run_native_command("ls nonexistent")
                assert "command output" in result
                assert "Error (exit code: 1)" in result
                assert "error message" in result

    def test_command_exception(self, mock_config):
        """Test handling of exceptions during command execution."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("subprocess.run", side_effect=Exception("Command failed")):
                result = run_native_command("invalid command")
                assert "Error executing command: Command failed" in result

    def test_auto_approve_enabled(self, mock_config):
        """Test auto-approval of allowed commands."""
        mock_config.auto_approve_native_commands = True

        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.stdout = "command output"
            mock_process.stderr = ""
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = run_native_command("ls -la")
            assert result == "command output"
            mock_run.assert_called_once()

    def test_auto_approve_not_in_allowlist(self, mock_config):
        """Test that commands not in allowlist still require confirmation even with auto-approve enabled."""
        mock_config.auto_approve_native_commands = True

        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=False):
            result = run_native_command("rm -rf files")
            assert "Command execution cancelled by user" in result

    def test_dangerous_command_forces_confirmation(self, mock_config):
        """Test that dangerous commands always require confirmation."""
        mock_config.auto_approve_native_commands = True

        for dangerous_prefix in DANGEROUS_COMMAND_PREFIXES[:1]:  # Just test the first one
            with patch("code_agent.tools.native_tools.Confirm.ask", return_value=False):
                result = run_native_command(f"{dangerous_prefix} some_arg")
                assert "Command execution cancelled by user" in result

    def test_risky_command_warning(self, mock_config):
        """Test that risky commands show a warning."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("code_agent.tools.native_tools.print") as mock_print:
                with patch("subprocess.run") as mock_run:
                    mock_process = MagicMock()
                    mock_process.stdout = "command output"
                    mock_process.stderr = ""
                    mock_process.returncode = 0
                    mock_run.return_value = mock_process

                    # Test with the first risky command prefix
                    run_native_command(f"{RISKY_COMMAND_PREFIXES[0]} some_arg")

                    # Check that a caution message was printed
                    mock_print.assert_any_call(
                        "[bold yellow]⚠️  CAUTION: This command could have side effects.[/bold yellow]"
                    )

    def test_successful_command_message(self, mock_config):
        """Test that successful commands show a success message."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("code_agent.tools.native_tools.print") as mock_print:
                with patch("subprocess.run") as mock_run:
                    mock_process = MagicMock()
                    mock_process.stdout = "command output"
                    mock_process.stderr = ""
                    mock_process.returncode = 0
                    mock_run.return_value = mock_process

                    run_native_command("echo hello")

                    # Check that a success message was printed
                    mock_print.assert_any_call("[green]Command completed successfully[/green]")

    def test_failed_command_message(self, mock_config):
        """Test that failed commands show an error message."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("code_agent.tools.native_tools.print") as mock_print:
                with patch("subprocess.run") as mock_run:
                    mock_process = MagicMock()
                    mock_process.stdout = "command output"
                    mock_process.stderr = "error output"
                    mock_process.returncode = 1
                    mock_run.return_value = mock_process

                    run_native_command("false")

                    # Check that an error message was printed
                    mock_print.assert_any_call("[red]Command failed with exit code 1[/red]")

    def test_subprocess_run_parameters(self, mock_config):
        """Test that subprocess.run is called with the correct parameters."""
        with patch("code_agent.tools.native_tools.Confirm.ask", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_process = MagicMock()
                mock_process.stdout = "command output"
                mock_process.stderr = ""
                mock_process.returncode = 0
                mock_run.return_value = mock_process

                run_native_command("echo 'test command'")

                # Check subprocess.run parameters
                mock_run.assert_called_once_with(
                    "echo 'test command'",
                    shell=True,
                    text=True,
                    capture_output=True,
                    executable="/bin/bash",
                )
