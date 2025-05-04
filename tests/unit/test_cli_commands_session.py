"""Unit tests for CLI session commands."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer

from code_agent.cli.commands.session import history, sessions


class TestSessionCommands(unittest.TestCase):
    """Tests for CLI session commands."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test session files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self.temp_dir.name)

        # Create some session files for testing
        self.session_ids = ["test_session_1", "test_session_2", "test_session_3"]
        for session_id in self.session_ids:
            session_file = self.sessions_dir / f"{session_id}.session.json"
            with open(session_file, "w") as f:
                json.dump({
                    "app_name": "test_app",
                    "user_id": "test_user",
                    "id": session_id,
                    "events": []
                }, f)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    @patch("code_agent.cli.commands.session.Console")
    def test_history_command(self, mock_console_class):
        """Test the history command."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the history command
        history(session_id="test_session_id", count=None, show_timestamps=False)

        # Verify the console output - test that the console.print method was called
        mock_console.print.assert_called()

        # Check the first call contains the expected string
        first_call_args = mock_console.print.call_args_list[0].args
        self.assertTrue(any("Session History" in arg for arg in first_call_args if isinstance(arg, str)))

    @patch("code_agent.cli.commands.session.Console")
    def test_history_command_with_count(self, mock_console_class):
        """Test the history command with a count specified."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the history command with a count
        history(session_id="test_session_id", count=5, show_timestamps=False)

        # Verify the console output
        mock_console.print.assert_called()

    @patch("code_agent.cli.commands.session.Console")
    def test_history_command_with_timestamps(self, mock_console_class):
        """Test the history command with timestamps enabled."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the history command with timestamps
        history(session_id="test_session_id", count=None, show_timestamps=True)

        # Verify the console output
        mock_console.print.assert_called()

    @patch("code_agent.cli.commands.session.get_config")
    @patch("code_agent.cli.commands.session.Console")
    def test_sessions_command_missing_dir(self, mock_console_class, mock_get_config):
        """Test sessions command when sessions directory is not configured."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.sessions_dir = None
        mock_get_config.return_value = mock_config

        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the sessions command with a missing directory
        with self.assertRaises(typer.Exit):
            sessions()

        # Verify error message
        mock_console.print.assert_called()

    @patch("code_agent.cli.commands.session.get_config")
    @patch("code_agent.cli.commands.session.Console")
    def test_sessions_command_nonexistent_dir(self, mock_console_class, mock_get_config):
        """Test sessions command when sessions directory doesn't exist."""
        # Mock configuration with a nonexistent directory
        mock_config = MagicMock()
        mock_config.sessions_dir = MagicMock()
        mock_config.sessions_dir.is_dir.return_value = False
        mock_get_config.return_value = mock_config

        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the sessions command with a nonexistent directory
        with self.assertRaises(typer.Exit):
            sessions()

        # Verify error message
        self.assertTrue(any("directory not found" in str(arg) for args in mock_console.print.call_args_list for arg in args[0] if isinstance(arg, str)))

    @patch("code_agent.cli.commands.session.get_config")
    @patch("code_agent.cli.commands.session.Console")
    def test_sessions_command_glob_error(self, mock_console_class, mock_get_config):
        """Test sessions command when there's an error accessing the directory."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.sessions_dir = MagicMock()
        mock_config.sessions_dir.is_dir.return_value = True
        mock_config.sessions_dir.glob.side_effect = OSError("Permission denied")
        mock_get_config.return_value = mock_config

        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the sessions command with a directory access error
        with self.assertRaises(typer.Exit):
            sessions()

        # Verify error message
        mock_console.print.assert_called()

    @patch("code_agent.cli.commands.session.get_config")
    @patch("code_agent.cli.commands.session.Console")
    def test_sessions_command_success(self, mock_console_class, mock_get_config):
        """Test sessions command with valid sessions."""
        # Mock configuration with our real sessions directory
        mock_config = MagicMock()
        mock_config.sessions_dir = self.sessions_dir
        mock_get_config.return_value = mock_config

        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the sessions command
        sessions()

        # Verify output - it should print for each session file
        self.assertEqual(mock_console.print.call_count, len(self.session_ids) + 1)  # +1 for the header

        # Check that session IDs are in the output
        printed_lines = [str(call_args[0][0]) for call_args in mock_console.print.call_args_list if call_args[0]]
        for session_id in self.session_ids:
            self.assertTrue(any(session_id in line for line in printed_lines))

    @patch("code_agent.cli.commands.session.get_config")
    @patch("code_agent.cli.commands.session.Console")
    def test_sessions_command_no_sessions(self, mock_console_class, mock_get_config):
        """Test sessions command when no session files are found."""
        # Create an empty directory
        empty_dir = tempfile.TemporaryDirectory()

        # Mock configuration with the empty directory
        mock_config = MagicMock()
        mock_config.sessions_dir = Path(empty_dir.name)
        mock_get_config.return_value = mock_config

        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the sessions command
        sessions()

        # Verify output - it should indicate no sessions found
        mock_console.print.assert_called_with(f"No saved sessions found in: {Path(empty_dir.name)}")

        # Clean up
        empty_dir.cleanup()
