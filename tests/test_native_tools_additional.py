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
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_execution_success(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test successful command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        # Set proper string values for native_commands properties
        native_commands = MagicMock()
        native_commands.default_working_directory = None
        native_commands.default_timeout = None
        config.native_commands = native_commands
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls")

        # Check that the command was executed with correct parameters
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert args[0] == ["ls"]
        assert kwargs["shell"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

        # Verify the result
        assert "Command output" in result

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_execution_auto_approve(self, mock_console, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with auto-approve enabled."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        # Set proper string values for native_commands properties
        native_commands = MagicMock()
        native_commands.default_working_directory = None
        native_commands.default_timeout = None
        config.native_commands = native_commands
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls")

        # Check that the command was executed
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert args[0] == ["ls"]

        # Verify the result
        assert "Command output" in result

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_execution_with_error(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution that returns an error code."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        # Set proper string values for native_commands properties
        native_commands = MagicMock()
        native_commands.default_working_directory = None
        native_commands.default_timeout = None
        config.native_commands = native_commands
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.stdout = ""
        process_mock.stderr = "Command failed with error"
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls nonexistent")

        # Verify the result contains error details
        assert "Error (exit code: 1)" in result
        assert "Command failed with error" in result

    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(False, "Command is dangerous", False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=False)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_dangerous_command_rejected(self, mock_console, mock_confirm, mock_is_safe, mock_get_config):
        """Test dangerous command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        mock_get_config.return_value = config

        # Run the function with a dangerous command
        result = run_native_command(command="rm -rf /")

        # Verify the command was rejected
        assert "not permitted" in result.lower()

    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, "Command has risks", True))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=False)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_risky_command_rejected(self, mock_console, mock_confirm, mock_is_safe, mock_get_config):
        """Test risky command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        # Set proper string values for native_commands properties
        native_commands = MagicMock()
        native_commands.default_working_directory = None
        native_commands.default_timeout = None
        config.native_commands = native_commands
        mock_get_config.return_value = config

        # Run the function with a risky command
        result = run_native_command(command="apt-get install package")

        # Verify the command was rejected
        assert "cancelled" in result.lower()

    @patch("subprocess.run", side_effect=OSError("OS Error"))
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_os_error(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test handling of OS errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        # Set proper string values for native_commands properties
        native_commands = MagicMock()
        native_commands.default_working_directory = None
        native_commands.default_timeout = None
        config.native_commands = native_commands
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test")

        # Verify error is reported in result
        assert "Error executing command" in result
        assert "OS Error" in result

    @patch("code_agent.tools.native_tools.run_native_command")
    def test_run_native_command_legacy(self, mock_run_native_command):
        """Test the legacy run_native_command_legacy function."""
        mock_run_native_command.return_value = "Command executed"

        args = MagicMock()
        args.command = "test command"
        args.working_directory = None
        args.timeout = None

        # Call the legacy function
        result = run_native_command_legacy(args)

        # Check that the modern function was called with correct parameters
        mock_run_native_command.assert_called_once_with("test command", working_directory=None, timeout=None)

        # Verify the result
        assert result == "Command executed"

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
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_with_working_directory(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with working directory specified."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False

        # Explicitly set native_commands with None values to avoid defaults
        native_commands_mock = MagicMock()
        native_commands_mock.default_timeout = None
        native_commands_mock.default_working_directory = None
        config.native_commands = native_commands_mock

        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with working directory
        result = run_native_command(command="ls", working_directory="/tmp")

        # Check that the command was executed with correct working directory
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert kwargs["cwd"] == "/tmp"

        # Verify the result
        assert "Command output" in result

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_with_timeout(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test command execution with timeout specified."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False

        # Explicitly set native_commands with None values to avoid defaults
        native_commands_mock = MagicMock()
        native_commands_mock.default_timeout = None
        native_commands_mock.default_working_directory = None
        config.native_commands = native_commands_mock

        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with timeout
        result = run_native_command(command="ls", timeout=30)

        # Check that the command was executed with correct timeout
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert kwargs["timeout"] == 30

        # Verify the result
        assert "Command output" in result

    @patch("subprocess.run", side_effect=TimeoutExpired(cmd="ls", timeout=5))
    @patch("code_agent.tools.native_tools.get_config")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_timeout_error(self, mock_console, mock_confirm, mock_is_safe, mock_get_config, mock_subprocess_run):
        """Test handling of timeout errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False

        # Explicitly set native_commands with None values to avoid defaults
        native_commands_mock = MagicMock()
        native_commands_mock.default_timeout = None
        native_commands_mock.default_working_directory = None
        config.native_commands = native_commands_mock

        mock_get_config.return_value = config

        # Run the function with timeout
        result = run_native_command(command="ls", timeout=5)

        # Verify error is reported in result
        assert "Command timed out after 5 seconds" in result

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

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False))
    @patch("code_agent.tools.native_tools.Confirm.ask", return_value=True)
    @patch("code_agent.tools.native_tools.console")  # Mock the console to avoid rendering issues
    def test_command_with_config_defaults(self, mock_console, mock_confirm, mock_is_safe, mock_subprocess_run):
        """Test command execution using configuration defaults."""
        # Create a mock config with native command settings
        config_mock = MagicMock()
        config_mock.auto_approve_native_commands = False

        # Create native_commands with default values
        native_commands_mock = MagicMock()
        native_commands_mock.default_timeout = 60
        native_commands_mock.default_working_directory = "/custom/workdir"

        # Attach native_commands to config
        config_mock.native_commands = native_commands_mock

        # Setup subprocess mock
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output with defaults"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Patch get_config to return our mock config
        with patch("code_agent.tools.native_tools.get_config", return_value=config_mock):
            # Run the command without specifying working_directory or timeout
            # Should use the values from config
            result = run_native_command(command="echo test")

            # Check that defaults were used
            mock_subprocess_run.assert_called_once()
            args, kwargs = mock_subprocess_run.call_args
            assert kwargs["cwd"] == "/custom/workdir"
            assert kwargs["timeout"] == 60

            # Verify the result
            assert "Command output with defaults" in result
