"""
Additional tests for the native_tools module to improve coverage.

These tests focus on edge cases and error handling in the native_tools module.
"""

from unittest.mock import MagicMock, patch

from code_agent.tools.native_tools import RunNativeCommandArgs, run_native_command, run_native_command_legacy


class TestRunNativeCommand:
    """Tests for the run_native_command function."""

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    def test_command_execution_success(self, mock_get_config, mock_subprocess_run):
        """Test successful command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["ls"]
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
    def test_command_execution_failure(self, mock_get_config, mock_subprocess_run):
        """Test command execution failure."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["invalid_command"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.stdout = ""
        process_mock.stderr = "Command failed"
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="invalid_command")

        # Assertions
        assert "Error" in result
        assert "Command failed" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_dangerous_command_rejected(self, mock_confirm, mock_get_config):
        """Test dangerous command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        config.native_command_allowlist = []
        mock_get_config.return_value = config

        # Run the function with a dangerous command
        result = run_native_command(command="rm -rf /")

        # Assertions
        assert "Command execution cancelled" in result

    @patch("code_agent.tools.native_tools.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_risky_command_rejected(self, mock_confirm, mock_get_config):
        """Test risky command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        config.native_command_allowlist = []
        mock_get_config.return_value = config

        # Run the function with a risky command
        result = run_native_command(command="apt-get install package")

        # Assertions
        assert "Command execution cancelled" in result

    @patch("subprocess.run", side_effect=OSError("OS Error"))
    @patch("code_agent.tools.native_tools.get_config")
    def test_command_os_error(self, mock_get_config, mock_subprocess_run):
        """Test handling of OS errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["echo"]
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "Error" in result
        assert "OS Error" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("Generic Error"))
    @patch("code_agent.tools.native_tools.get_config")
    def test_command_generic_error(self, mock_get_config, mock_subprocess_run):
        """Test handling of generic errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["echo"]
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "Error" in result
        assert "Generic Error" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_command_user_rejection(self, mock_confirm, mock_get_config):
        """Test user rejection of command."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        config.native_command_allowlist = []
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "cancelled" in result
        assert "user" in result.lower()

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_command_user_approval(self, mock_confirm, mock_get_config, mock_subprocess_run):
        """Test user approval of command."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = False
        config.native_command_allowlist = []
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    def test_command_allowlist_match(self, mock_get_config, mock_subprocess_run):
        """Test command approval through allowlist matching."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["echo"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="echo test")

        # Assertions
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.get_config")
    def test_command_with_stderr_output(self, mock_get_config):
        """Test command with stderr output but successful return code."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["ls"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Standard output"
        process_mock.stderr = "Some warning message"

        with patch("subprocess.run", return_value=process_mock):
            # Run the function
            result = run_native_command(command="ls -la")

            # Assertions
            assert "Standard output" in result
            # Stderr is not included if returncode is 0
            assert "Some warning message" not in result

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    def test_command_with_environmental_variables(self, mock_get_config, mock_subprocess_run):
        """Test command with environmental variables."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["echo"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "ENV_VAR value"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with env var
        result = run_native_command(command="echo $ENV_VAR")

        # Assertions
        assert "ENV_VAR value" in result
        mock_subprocess_run.assert_called_once_with(
            "echo $ENV_VAR",
            shell=True,
            text=True,
            capture_output=True,
            executable="/bin/bash",
        )

    @patch("code_agent.tools.native_tools.get_config")
    def test_non_allowlisted_command_needs_confirmation(self, mock_get_config):
        """Test that a non-allowlisted command requires confirmation even with auto-approve enabled."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["ls", "echo"]  # pwd not in allowlist
        mock_get_config.return_value = config

        with patch("rich.prompt.Confirm.ask", return_value=False) as mock_confirm:
            # Run the function
            result = run_native_command(command="pwd")

            # Assertions
            assert "Command execution cancelled" in result
            mock_confirm.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.tools.native_tools.get_config")
    def test_complex_command_with_pipe(self, mock_get_config, mock_subprocess_run):
        """Test command with pipe character."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_native_commands = True
        config.native_command_allowlist = ["ls"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Filtered output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function with piped command
        result = run_native_command(command="ls -la | grep file")

        # Assertions
        assert "Filtered output" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.tools.native_tools.run_native_command")
    def test_run_native_command_legacy(self, mock_run_native_command):
        """Test the legacy function that accepts RunNativeCommandArgs."""
        mock_run_native_command.return_value = "Command executed"

        args = RunNativeCommandArgs(command="test command")
        result = run_native_command_legacy(args)

        mock_run_native_command.assert_called_once_with("test command")
        assert result == "Command executed"
