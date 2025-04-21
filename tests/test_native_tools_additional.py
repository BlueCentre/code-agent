"""
Additional tests for the native_tools module to improve coverage.

These tests focus on edge cases and error handling in the native_tools module.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.native_tools import run_native_command


class TestRunNativeCommand:
    """Tests for the run_native_command function."""

    @patch("subprocess.run")
    @patch("code_agent.config.config.get_config")
    def test_command_execution_success(self, mock_get_config, mock_subprocess_run):
        """Test successful command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="ls", is_background=False)
        
        # Assertions
        assert "successfully" in result
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.config.config.get_config")
    def test_command_execution_failure(self, mock_get_config, mock_subprocess_run):
        """Test command execution failure."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.stdout = ""
        process_mock.stderr = "Command failed"
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="invalid_command", is_background=False)
        
        # Assertions
        assert "Error" in result
        assert "Command failed" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.config.config.get_config")
    def test_dangerous_command_rejected(self, mock_get_config):
        """Test dangerous command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = False
        mock_get_config.return_value = config

        # Run the function with a dangerous command
        result = run_native_command(command="rm -rf /", is_background=False)
        
        # Assertions
        assert "rejected" in result
        assert "dangerous" in result.lower()

    @patch("code_agent.config.config.get_config")
    def test_risky_command_rejected(self, mock_get_config):
        """Test risky command rejection."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = False
        mock_get_config.return_value = config

        # Run the function with a risky command
        result = run_native_command(command="apt-get install package", is_background=False)
        
        # Assertions
        assert "rejected" in result
        assert "risky" in result.lower()

    @patch("subprocess.run", side_effect=OSError("OS Error"))
    @patch("code_agent.config.config.get_config")
    def test_command_os_error(self, mock_get_config, mock_subprocess_run):
        """Test handling of OS errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test", is_background=False)
        
        # Assertions
        assert "Error" in result
        assert "OS Error" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("Generic Error"))
    @patch("code_agent.config.config.get_config")
    def test_command_generic_error(self, mock_get_config, mock_subprocess_run):
        """Test handling of generic errors during command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test", is_background=False)
        
        # Assertions
        assert "Error" in result
        assert "Generic Error" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.Popen")
    @patch("code_agent.config.config.get_config")
    def test_background_command_execution(self, mock_get_config, mock_subprocess_popen):
        """Test background command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.pid = 12345
        mock_subprocess_popen.return_value = process_mock

        # Run the function
        result = run_native_command(command="sleep 10", is_background=True)
        
        # Assertions
        assert "background" in result.lower()
        assert "12345" in result
        mock_subprocess_popen.assert_called_once()

    @patch("subprocess.Popen", side_effect=OSError("OS Error"))
    @patch("code_agent.config.config.get_config")
    def test_background_command_os_error(self, mock_get_config, mock_subprocess_popen):
        """Test handling of OS errors during background command execution."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="sleep 10", is_background=True)
        
        # Assertions
        assert "Error" in result
        assert "OS Error" in result
        mock_subprocess_popen.assert_called_once()

    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_command_user_rejection(self, mock_confirm, mock_get_config):
        """Test user rejection of command."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = False
        config.command_allowlist = []
        mock_get_config.return_value = config

        # Run the function
        result = run_native_command(command="echo test", is_background=False)
        
        # Assertions
        assert "rejected" in result
        assert "user" in result.lower()

    @patch("subprocess.run")
    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_command_user_approval(self, mock_confirm, mock_get_config, mock_subprocess_run):
        """Test user approval of command."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = False
        config.command_allowlist = []
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="echo test", is_background=False)
        
        # Assertions
        assert "successfully" in result
        assert "Command output" in result
        mock_subprocess_run.assert_called_once()

    @patch("subprocess.run")
    @patch("code_agent.config.config.get_config")
    def test_command_allowlist_match(self, mock_get_config, mock_subprocess_run):
        """Test command approval through allowlist matching."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = False
        config.command_allowlist = ["echo *"]
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Command output"
        process_mock.stderr = ""
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="echo test", is_background=False)
        
        # Assertions
        assert "successfully" in result
        assert "allowlist" in result.lower()
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.config.config.get_config")
    def test_empty_command(self, mock_get_config):
        """Test handling of empty command."""
        # Setup mocks
        config = MagicMock()
        mock_get_config.return_value = config

        # Run the function with empty command
        result = run_native_command(command="", is_background=False)
        
        # Assertions
        assert "Error" in result
        assert "empty" in result.lower()

    @patch("subprocess.run")
    @patch("code_agent.config.config.get_config")
    def test_command_with_stderr_output(self, mock_get_config, mock_subprocess_run):
        """Test command with stderr output but successful return code."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "Standard output"
        process_mock.stderr = "Some warnings"
        mock_subprocess_run.return_value = process_mock

        # Run the function
        result = run_native_command(command="command_with_warnings", is_background=False)
        
        # Assertions
        assert "successfully" in result
        assert "Standard output" in result
        assert "Some warnings" in result
        mock_subprocess_run.assert_called_once()

    @patch("code_agent.config.config.get_config")
    def test_command_with_env_variables(self, mock_get_config):
        """Test command with environment variables."""
        # Setup mocks
        config = MagicMock()
        config.auto_approve_commands = True
        mock_get_config.return_value = config

        # Patch subprocess.run to check the environment
        with patch("subprocess.run") as mock_subprocess_run:
            process_mock = MagicMock()
            process_mock.returncode = 0
            process_mock.stdout = "Command output"
            process_mock.stderr = ""
            mock_subprocess_run.return_value = process_mock

            # Run the function
            result = run_native_command(command="echo $HOME", is_background=False)
            
            # Get the call arguments
            call_args = mock_subprocess_run.call_args[1]
            
            # Assertions
            assert "env" in call_args
            assert call_args["env"] is not None
            assert "successfully" in result
            mock_subprocess_run.assert_called_once()
