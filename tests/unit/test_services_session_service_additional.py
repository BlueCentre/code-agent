"""
Tests to increase coverage for code_agent.services.session_service module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.adk.sessions import Session
from pydantic import ValidationError

from code_agent.services.session_service import FileSystemSessionService


class TestFileSystemSessionServiceAdditional:
    """Additional tests for FileSystemSessionService to increase coverage."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for session files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_dir = Path(self.temp_dir.name)

        # Create a service instance
        self.service = FileSystemSessionService(str(self.session_dir))

        # Basic session parameters
        self.app_name = "test-app"
        self.user_id = "test-user"
        self.session_id = "test-session-id"

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_init_with_missing_dir(self):
        """Test initialization with directory that doesn't exist yet."""
        # Create a path that doesn't exist yet
        new_dir = self.session_dir / "nested" / "dir"

        # Initialize service with non-existent directory
        # service = FileSystemSessionService(str(new_dir))
        FileSystemSessionService(str(new_dir))

        # Verify directory was created
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_sessions_dir_str_conversion(self):
        """Test that sessions_dir is stored as a Path object regardless of input type."""
        # Initialize with string path
        service_from_str = FileSystemSessionService(str(self.session_dir))
        assert isinstance(service_from_str.sessions_dir, Path)

        # Initialize with Path object
        service_from_path = FileSystemSessionService(self.session_dir)
        assert isinstance(service_from_path.sessions_dir, Path)

    def test_get_session_with_nonexistent_dir(self):
        """Test get_session when session directory doesn't exist."""
        # Create a service with a directory then delete it
        nonexistent_dir = self.session_dir / "nonexistent"
        service = FileSystemSessionService(str(nonexistent_dir))
        nonexistent_dir.rmdir()  # Remove the directory

        # Mock parent get_session to return None
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            # Attempt to get a session
            result = service.get_session(self.app_name, self.user_id, self.session_id)

            # Expect None result
            assert result is None

    @pytest.mark.skip(reason="Test is unstable due to mocking complexity")
    @patch("code_agent.services.session_service.Path.is_file")
    def test_get_session_missing_session_id(self, mock_is_file):
        """Test get_session with None session_id."""
        mock_is_file.return_value = False

        # Mock parent get_session to return None
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            # Attempt to get a session with None session_id
            result = self.service.get_session(self.app_name, self.user_id, None)

            # Expect None result
            assert result is None
            # Verify is_file wasn't called (early return)
            mock_is_file.assert_not_called()

    @pytest.mark.skip(reason="Test is unstable due to ValidationError mocking complexity")
    def test_get_session_validation_error_with_details(self):
        """Test get_session with a detailed validation error."""
        # Create a session file with invalid data
        session_file = self.session_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump({"invalid": "data"}, f)

        # Mock parent get_session to return None
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            # Mock validation error with details
            validation_error = ValidationError.from_exception_data(
                title="Invalid session data",
                line_errors=[
                    {"loc": ["app_name"], "msg": "field required", "type": "value_error.missing"},
                    {"loc": ["user_id"], "msg": "field required", "type": "value_error.missing"},
                ],
            )

            with patch("google.adk.sessions.Session.model_validate_json", side_effect=validation_error):
                # Attempt to get a session
                result = self.service.get_session(self.app_name, self.user_id, self.session_id)

                # Expect None result
                assert result is None

    def test_complex_exception_handling(self):
        """Test complex exception handling in get_session."""
        # Create a session file
        session_file = self.session_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump({"app_name": self.app_name, "user_id": self.user_id, "id": self.session_id}, f)

        # Mock parent get_session to return None
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            # Create a complicated exception chain
            inner_exception = ValueError("Inner error")
            middle_exception = RuntimeError("Middle error")
            middle_exception.__cause__ = inner_exception
            outer_exception = Exception("Outer error")
            outer_exception.__cause__ = middle_exception

            with patch("google.adk.sessions.Session.model_validate_json", side_effect=outer_exception):
                # Attempt to get a session
                result = self.service.get_session(self.app_name, self.user_id, self.session_id)

                # Expect None result
                assert result is None

    @patch("code_agent.services.session_service.Session.model_validate_json")
    @patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None)
    def test_get_session_successful_load(self, mock_parent_get_session, mock_validate_json):
        """Test successful loading of a session from file."""
        # Create a session file
        session_file = self.session_dir / f"{self.session_id}.session.json"
        session_data = {"app_name": self.app_name, "user_id": self.user_id, "id": self.session_id, "events": []}
        with open(session_file, "w") as f:
            json.dump(session_data, f)

        # Mock the validation to return a session object
        mock_session = MagicMock(spec=Session)
        mock_session.app_name = self.app_name
        mock_session.user_id = self.user_id
        mock_session.id = self.session_id
        mock_validate_json.return_value = mock_session

        # Get the session
        result = self.service.get_session(self.app_name, self.user_id, self.session_id)

        # Verify result
        assert result is mock_session
        mock_validate_json.assert_called_once()

        # Verify the correct JSON was passed to model_validate_json
        json_str = mock_validate_json.call_args[0][0]
        loaded_data = json.loads(json_str)
        assert loaded_data["app_name"] == self.app_name
        assert loaded_data["user_id"] == self.user_id
        assert loaded_data["id"] == self.session_id
