"""
Tests for the FileSystemSessionService class.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.adk.sessions import Session
from pydantic import ValidationError

from code_agent.services.session_service import FileSystemSessionService


class TestFileSystemSessionService:
    """Test suite for FileSystemSessionService."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Create a temporary directory for session files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_dir = Path(self.temp_dir.name)
        self.service = FileSystemSessionService(sessions_dir=str(self.session_dir))

        # Create test session data
        self.app_name = "test-app"
        self.user_id = "test-user"
        self.session_id = "test-session-id"

    def teardown_method(self):
        """Clean up after each test method."""
        self.temp_dir.cleanup()

    def test_init_creates_directory(self):
        """Test that __init__ creates the sessions directory if it doesn't exist."""
        new_dir = self.session_dir / "nested" / "sessions"
        service = FileSystemSessionService(str(new_dir))
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_init_empty_dir_raises_error(self):
        """Test that __init__ raises ValueError if sessions_dir is empty."""
        with pytest.raises(ValueError, match="sessions_dir argument cannot be empty"):
            FileSystemSessionService("")

    @patch("pathlib.Path.mkdir")
    def test_init_handles_os_error(self, mock_mkdir):
        """Test that __init__ handles OSError when creating directory."""
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(RuntimeError, match="Failed to initialize FileSystemSessionService"):
            FileSystemSessionService("/some/nonexistent/path")

    def test_get_session_not_found(self):
        """Test get_session returns None when session doesn't exist."""
        # No session file exists yet
        result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)
        assert result is None

    @patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session")
    def test_get_session_from_memory(self, mock_get_session):
        """Test get_session retrieves from memory cache if available."""
        # Mock the parent class's get_session to return a session
        mock_session = MagicMock(spec=Session)
        mock_get_session.return_value = mock_session

        result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)
        assert result is mock_session
        mock_get_session.assert_called_once_with(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)

    def test_get_session_from_file(self):
        """Test get_session loads from file when not in memory."""
        # Create a mock session JSON file
        session_data = {"id": self.session_id, "app_name": self.app_name, "user_id": self.user_id, "messages": []}
        session_file = self.session_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f)

        # Mock the parent get_session to return None (not in memory)
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            # Mock Session.model_validate_json to return a valid session
            with patch("google.adk.sessions.Session.model_validate_json") as mock_validate:
                mock_session = MagicMock(spec=Session)
                mock_validate.return_value = mock_session

                result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)

                assert result is mock_session
                mock_validate.assert_called_once()

    def test_get_session_file_read_error(self):
        """Test get_session handles file read errors gracefully."""
        # Create the session file path but don't make it readable
        session_file = self.session_dir / f"{self.session_id}.session.json"
        session_file.touch()  # Create empty file

        # Make the file unreadable by mocking read_text to raise OSError
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
                result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)
                assert result is None

    def test_get_session_invalid_json(self):
        """Test get_session handles invalid JSON in session file gracefully."""
        # Create a session file with invalid JSON
        session_file = self.session_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            f.write("This is not valid JSON")

        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)
            assert result is None

    def test_get_session_validation_error(self):
        """Test get_session handles validation errors gracefully."""
        # Create a session file with JSON that won't validate
        session_file = self.session_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump({"invalid": "data"}, f)

        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            with patch("google.adk.sessions.Session.model_validate_json", side_effect=ValidationError.from_exception_data("error", [])):
                result = self.service.get_session(app_name=self.app_name, user_id=self.user_id, session_id=self.session_id)
                assert result is None
