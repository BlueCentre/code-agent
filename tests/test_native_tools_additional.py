"""
Additional tests for the native_tools module to improve coverage.

These tests focus on edge cases and error handling in the native_tools module.
"""

from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

from code_agent.tools.native_tools import (
    DANGEROUS_COMMAND_PREFIXES,
    RISKY_COMMAND_PREFIXES,
    RunNativeCommandArgs,
    run_native_command,
    run_native_command_legacy,
)


class TestRunNativeCommand:
    """Test class for the run_native_command function."""

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_execution_success(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test successful command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls")

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()
        mock_confirm.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    def test_command_execution_auto_approve(self, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with auto-approve enabled."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls")

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_execution_with_error(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution that returns an error code."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.stdout = ""
        process_mock.stderr = "Command failed with error"
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls nonexistent")

        # Assertions
        assert "Error (exit code: 1)" in result
        assert "Command failed with error" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(False, "Command is dangerous", False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=False)
    def test_dangerous_command_rejected(self, mock_confirm, mock_is_safe, mock_get_config):
        """Test dangerous command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        # Run the function with a dangerous command
        result = run_native_command(command="rm -rf /")

        # Assertions
        assert "Command execution not permitted" in result
        assert "Command is dangerous" in result
        # Confirm should not be called since the command is rejected before confirmation
        mock_confirm.assert_not_called()

    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, "Command has risks", True))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=False)
    def test_risky_command_rejected(self, mock_confirm, mock_is_safe, mock_get_config):
        """Test risky command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        # Run the function with a risky command
        result = run_native_command(command="apt-get install package")

        # Assertions
        assert "Command execution cancelled" in result
        mock_confirm.assert_called_once()

    @patch("subprocess.run", side_effect=OSError("OS Error"))
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_os_error(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test handling of OS errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "Error executing command" in result
        assert "OS Error" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.run_native_command")
    def test_run_native_command_legacy(self, mock_run_native_command):
        """Test the legacy function that accepts RunNativeCommandArgs."""
        # Setup mock
        mock_run_native_command.return_value = "Command output"

        # Create args object
        args = RunNativeCommandArgs(command="ls")

        # Call the legacy function
        result = run_native_command_legacy(args)

        # Assertions
        assert result == "Command output"
        mock_run_native_command.assert_called_once_with("ls", working_directory=None, timeout=None)

    def test_dangerous_command_prefixes_exist(self):
        """Test that DANGEROUS_COMMAND_PREFIXES is defined and not empty."""
        assert DANGEROUS_COMMAND_PREFIXES
        assert isinstance(DANGEROUS_COMMAND_PREFIXES, list)
        assert len(DANGEROUS_COMMAND_PREFIXES) > 0

    def test_risky_command_prefixes_exist(self):
        """Test that RISKY_COMMAND_PREFIXES is defined and not empty."""
        assert RISKY_COMMAND_PREFIXES
        assert isinstance(RISKY_COMMAND_PREFIXES, list)
        assert len(RISKY_COMMAND_PREFIXES) > 0

    # Additional tests for working directory and timeout options
    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_with_working_directory(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with working directory specified."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with working directory
        result = run_native_command(command="ls", working_directory="/tmp")

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once_with(["ls"], capture_output=True, text=True, shell=False, cwd="/tmp", timeout=None)

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_with_timeout(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with timeout specified."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with timeout
        result = run_native_command(command="ls", timeout=30)

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once_with(["ls"], capture_output=True, text=True, shell=False, cwd=None, timeout=30)

    @patch("subprocess.run", side_effect=TimeoutExpired(cmd="ls", timeout=5))
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    def test_command_timeout_error(self, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test handling of timeout errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        # Run the function with timeout
        result = run_native_command(command="ls", timeout=5)

        # Assertions
        assert "Command timed out after 5 seconds" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.run_native_command")
    def test_run_native_command_legacy_with_options(self, mock_run_native_command):
        """Test the legacy function with working directory and timeout."""
        # Setup mock
        mock_run_native_command.return_value = "Command output"

        # Create args object with working directory and timeout
        args = RunNativeCommandArgs(command="ls", working_directory="/tmp", timeout=30)

        # Call the legacy function
        result = run_native_command_legacy(args)

        # Assertions
        assert result == "Command output"
        mock_run_native_command.assert_called_once_with("ls", working_directory="/tmp", timeout=30)
