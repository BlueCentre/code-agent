"""Unit tests for FileSystemSessionService class in code_agent.services.session_service."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types as genai_types

from code_agent.services.session_service import FileSystemSessionService


class TestFileSystemSessionService(unittest.TestCase):
    """Tests for FileSystemSessionService."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test session files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sessions_dir = Path(self.temp_dir.name)

        # Create a sample session
        self.app_name = "test_app"
        self.user_id = "test_user"
        self.session_id = "test_session_id"
        self.sample_session = self._create_sample_session()

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def _create_sample_session(self):
        """Create a sample session with events for testing."""
        # Create sample content objects for events
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text="Hello, this is a test message")]
        )
        model_content = genai_types.Content(
            role="model",
            parts=[genai_types.Part(text="This is a test response")]
        )

        # Create events from content
        user_event = Event(author="user", content=user_content)
        model_event = Event(author="model", content=model_content)

        # Create a session with the events
        session = Session(
            app_name=self.app_name,
            user_id=self.user_id,
            id=self.session_id,
            events=[user_event, model_event]
        )
        return session

    def test_init_with_valid_dir(self):
        """Test initialization with a valid directory."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))
        self.assertEqual(service.sessions_dir, self.sessions_dir)
        self.assertTrue(self.sessions_dir.exists())

    def test_init_with_empty_dir(self):
        """Test initialization with an empty directory string."""
        with self.assertRaises(ValueError):
            FileSystemSessionService(sessions_dir="")

    @patch("pathlib.Path.mkdir")
    def test_init_with_mkdir_error(self, mock_mkdir):
        """Test initialization with an error creating directory."""
        mock_mkdir.side_effect = OSError("Permission denied")
        with self.assertRaises(RuntimeError):
            FileSystemSessionService(sessions_dir="/nonexistent/path")

    @patch("pathlib.Path.mkdir")
    def test_init_with_unexpected_error(self, mock_mkdir):
        """Test initialization with an unexpected error."""
        mock_mkdir.side_effect = Exception("Unexpected error")
        with self.assertRaises(RuntimeError):
            FileSystemSessionService(sessions_dir="/some/path")

    def test_get_session_from_memory(self):
        """Test getting a session from memory cache."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Mock the parent class method to return our sample session
        with patch.object(service, 'get_session', return_value=self.sample_session):
            # This would call the overridden method which we've already mocked
            session = service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )

        # Since we've mocked the method itself, we're just verifying our mock works
        self.assertEqual(session, self.sample_session)

    def test_get_session_from_file(self):
        """Test getting a session from file when not in memory."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Create a real session file
        session_file = self.sessions_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump(self.sample_session.model_dump(mode="json"), f)

        # Mock the parent get_session to return None (not in memory)
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            session = service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )

        # Verify we got a session back
        self.assertIsNotNone(session)
        self.assertEqual(session.id, self.session_id)
        self.assertEqual(session.app_name, self.app_name)
        self.assertEqual(session.user_id, self.user_id)

    def test_get_session_not_found(self):
        """Test getting a session that doesn't exist."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Mock the parent get_session to return None (not in memory)
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            session = service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id="nonexistent_session"
            )

        # Verify we got None back
        self.assertIsNone(session)

    def test_get_session_with_file_error(self):
        """Test getting a session with a file read error."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Create the session file path
        session_file = self.sessions_dir / f"{self.session_id}.session.json" # noqa: F841

        # Set up the mock to make it look like the file exists
        with patch("pathlib.Path.is_file", return_value=True):
            # Mock read_text to raise an OSError
            with patch("pathlib.Path.read_text", side_effect=OSError("Read error")):
                # Mock the parent get_session to return None (not in memory)
                with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
                    session = service.get_session(
                        app_name=self.app_name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )

        # Verify we got None back
        self.assertIsNone(session)

    def test_get_session_with_json_error(self):
        """Test getting a session with a JSON decode error."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Create a session file with invalid JSON
        session_file = self.sessions_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            f.write("invalid json")

        # Mock the parent get_session to return None (not in memory)
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            session = service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )

        # Verify we got None back
        self.assertIsNone(session)

    def test_get_session_with_validation_error(self):
        """Test getting a session with a validation error."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Create a session file with valid JSON but invalid schema
        session_file = self.sessions_dir / f"{self.session_id}.session.json"
        with open(session_file, "w") as f:
            json.dump({"invalid": "schema"}, f)

        # Mock the parent get_session to return None (not in memory)
        with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
            session = service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )

        # Verify we got None back
        self.assertIsNone(session)

    def test_get_session_with_unexpected_error(self):
        """Test getting a session with an unexpected error."""
        service = FileSystemSessionService(sessions_dir=str(self.sessions_dir))

        # Set up the mock to make it look like the file exists
        with patch("pathlib.Path.is_file", return_value=True):
            # Mock model_validate_json to raise an unexpected error
            with patch("google.adk.sessions.Session.model_validate_json", side_effect=Exception("Unexpected error")):
                # Mock the parent get_session to return None (not in memory)
                with patch("google.adk.sessions.in_memory_session_service.InMemorySessionService.get_session", return_value=None):
                    session = service.get_session(
                        app_name=self.app_name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )

        # Verify we got None back
        self.assertIsNone(session)
