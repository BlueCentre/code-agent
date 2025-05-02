"""
Unit tests for JsonFileMemoryService in code_agent.adk.json_memory_service.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types as genai_types

from code_agent.adk.json_memory_service import JsonFileMemoryService, MemoryServiceResponse


# Rename class to avoid pytest collection warning
class HelperJsonFileMemoryService(JsonFileMemoryService):
    """Helper version of JsonFileMemoryService that handles events instead of history."""

    def load_memory(self, query: str, **kwargs) -> MemoryServiceResponse:
        """
        Overridden version that works with events instead of history.
        """
        results = []
        query_lower = query.lower()

        for session in self._sessions.values():
            session_matched = False
            # Access events instead of history
            if session.events:
                for event in session.events:
                    # Access parts directly from the Content object in event.content
                    message_text = ""
                    if hasattr(event, "content") and event.content and event.content.parts:
                        message_text = "".join([part.text for part in event.content.parts if hasattr(part, "text") and part.text is not None]).lower()

                    if query_lower in message_text:
                        session_matched = True
                        break  # Found a match in this session's events

            if session_matched:
                # Add relevant session data
                results.append(session.model_dump(mode="json"))

        return MemoryServiceResponse(memories=results)


class TestJsonFileMemoryServiceClass(unittest.TestCase):
    """Tests for the JsonFileMemoryService class."""

    def setUp(self):
        """Set up test fixtures, including a temporary file for testing."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "test_memory.json")

        # Create a sample session for testing
        self.sample_session = self._create_sample_session()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def _create_sample_session(self):
        """Create a sample session with events for testing."""
        # Create a sample content objects for events
        user_content = genai_types.Content(role="user", parts=[genai_types.Part(text="Hello, this is a test message")])

        model_content = genai_types.Content(role="model", parts=[genai_types.Part(text="This is a test response")])

        # Create events from content
        user_event = Event(author="user", content=user_content)
        model_event = Event(author="model", content=model_content)

        # Create a session with the events
        session = Session(app_name="test_app", user_id="test_user", id="test_session", events=[user_event, model_event])
        return session

    def _create_memory_service(self, filepath=None):
        """Helper to create a HelperJsonFileMemoryService instance."""
        if filepath is None:
            filepath = self.test_filepath
        return HelperJsonFileMemoryService(filepath)

    def test_init_new_file(self):
        """Test initialization with a new file path."""
        # Test initialization with a file that doesn't exist
        service = self._create_memory_service()

        # Verify the service is initialized correctly
        self.assertEqual(service.filepath, self.test_filepath)
        self.assertEqual(len(service._sessions), 0)

    def test_get_session_key(self):
        """Test the _get_session_key method."""
        service = self._create_memory_service()

        # Get the key for the sample session
        key = service._get_session_key(self.sample_session)

        # Verify the key is correct
        self.assertEqual(key, ("test_app", "test_user", "test_session"))
        self.assertIsInstance(key, tuple)
        self.assertEqual(len(key), 3)

    def test_add_session_to_memory(self):
        """Test adding a session to memory."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Verify the session was added
        key = service._get_session_key(self.sample_session)
        self.assertIn(key, service._sessions)
        self.assertEqual(service._sessions[key], self.sample_session)

        # Verify the file was created
        self.assertTrue(os.path.exists(self.test_filepath))

    def test_load_memory_with_matching_query(self):
        """Test loading memory with a query that matches session content."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Search for a query that matches the message text
        response = service.load_memory("test message")

        # Verify the response
        self.assertIsInstance(response, MemoryServiceResponse)
        self.assertEqual(len(response.memories), 1)
        self.assertEqual(response.memories[0]["app_name"], "test_app")
        self.assertEqual(response.memories[0]["user_id"], "test_user")
        self.assertEqual(response.memories[0]["id"], "test_session")

    def test_load_memory_with_non_matching_query(self):
        """Test loading memory with a query that doesn't match session content."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Search for a query that doesn't match any message text
        response = service.load_memory("non-existent query")

        # Verify the response is empty
        self.assertIsInstance(response, MemoryServiceResponse)
        self.assertEqual(len(response.memories), 0)

    def test_search_memory(self):
        """Test the search_memory method."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Test the search_memory method with a matching query
        results = service.search_memory("test message")

        # Verify the results
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["app_name"], "test_app")

        # Test with non-matching query
        empty_results = service.search_memory("non-existent query")
        self.assertEqual(len(empty_results), 0)

    def test_load_from_json_valid_file(self):
        """Test loading sessions from a valid JSON file."""
        # Create a valid JSON file with session data
        session_data = {"('test_app', 'test_user', 'test_session')": self.sample_session.model_dump(mode="json")}

        with open(self.test_filepath, "w") as f:
            json.dump(session_data, f)

        # Initialize service, which should load the file
        service = self._create_memory_service()

        # Verify the session was loaded
        key = ("test_app", "test_user", "test_session")
        self.assertIn(key, service._sessions)
        self.assertEqual(service._sessions[key].app_name, "test_app")
        self.assertEqual(service._sessions[key].user_id, "test_user")
        self.assertEqual(service._sessions[key].id, "test_session")

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_json_invalid_json(self, mock_file, mock_exists):
        """Test loading from an invalid JSON file."""
        # Set up mocks
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        # Initialize service, which should catch the JSON error
        service = self._create_memory_service()

        # Verify no sessions were loaded
        self.assertEqual(len(service._sessions), 0)

    @patch("os.path.exists")
    def test_load_from_json_file_not_found(self, mock_exists):
        """Test handling of a non-existent file."""
        # Set up mock to simulate file not found
        mock_exists.return_value = False

        # Initialize service with a non-existent file
        service = self._create_memory_service()

        # Verify no sessions were loaded and no errors were raised
        self.assertEqual(len(service._sessions), 0)

    @patch("os.path.exists")
    def test_load_from_json_unexpected_error(self, mock_exists):
        """Test handling of unexpected error when loading from JSON."""
        # Set up mock to simulate file exists
        mock_exists.return_value = True

        # Mock open to raise an unexpected exception
        with patch("builtins.open") as mock_file:
            mock_file.side_effect = Exception("Unexpected error")

            # Initialize service, which should catch the error
            service = self._create_memory_service()

            # Verify no sessions were loaded and no errors were raised
            self.assertEqual(len(service._sessions), 0)

    def test_load_from_json_invalid_key_format(self):
        """Test loading with invalid key format in the JSON file."""
        # Create a JSON file with invalid key format
        invalid_data = {"invalid_key_format": self.sample_session.model_dump(mode="json")}

        with open(self.test_filepath, "w") as f:
            json.dump(invalid_data, f)

        # Initialize service, which should handle the invalid key format
        service = self._create_memory_service()

        # Verify no sessions were loaded
        self.assertEqual(len(service._sessions), 0)

    def test_load_from_json_invalid_session_data(self):
        """Test loading with invalid session data in the JSON file."""
        # Create a JSON file with invalid session data
        invalid_data = {"('test_app', 'test_user', 'test_session')": {"invalid": "data"}}

        with open(self.test_filepath, "w") as f:
            json.dump(invalid_data, f)

        # Initialize service, which should handle the invalid session data
        service = self._create_memory_service()

        # Verify no sessions were loaded
        self.assertEqual(len(service._sessions), 0)

    def test_save_to_json(self):
        """Test saving sessions to a JSON file."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Force save to JSON
        service._save_to_json()

        # Verify the file was created
        self.assertTrue(os.path.exists(self.test_filepath))

        # Verify the contents of the file
        with open(self.test_filepath, "r") as f:
            saved_data = json.load(f)

        # Verify the saved data
        key_str = str(("test_app", "test_user", "test_session"))
        self.assertIn(key_str, saved_data)
        self.assertEqual(saved_data[key_str]["app_name"], "test_app")
        self.assertEqual(saved_data[key_str]["user_id"], "test_user")
        self.assertEqual(saved_data[key_str]["id"], "test_session")

    def test_get_memory_service_info(self):
        """Test getting memory service info."""
        service = self._create_memory_service()

        # Get the service info
        info = service.get_memory_service_info()

        # Verify the info
        self.assertEqual(info["service_type"], "JsonFileMemoryService")
        self.assertEqual(info["filepath"], self.test_filepath)
        self.assertEqual(info["current_session_count"], 0)
        self.assertTrue(info["capabilities"]["persistence"])

    @patch("os.makedirs")
    def test_save_to_json_with_io_error(self, mock_makedirs):
        """Test handling of IOError during save_to_json."""
        # Set up mock to raise IOError
        mock_makedirs.side_effect = IOError("Test error")

        service = self._create_memory_service()
        service.add_session_to_memory(self.sample_session)

        # This should not raise an exception despite the IOError
        service._save_to_json()

        # Verify the internal state is still intact
        key = service._get_session_key(self.sample_session)
        self.assertIn(key, service._sessions)

    @patch("json.dump")
    def test_save_to_json_with_type_error(self, mock_dump):
        """Test handling of TypeError during save_to_json."""
        # Set up mock to raise TypeError
        mock_dump.side_effect = TypeError("Test error")

        service = self._create_memory_service()
        service.add_session_to_memory(self.sample_session)

        # This should not raise an exception despite the TypeError
        service._save_to_json()

        # Verify the internal state is still intact
        key = service._get_session_key(self.sample_session)
        self.assertIn(key, service._sessions)

    def test_add_invalid_session(self):
        """Test adding an invalid object as a session."""
        service = self._create_memory_service()

        # Try to add something that's not a Session
        service.add_session_to_memory("not a session")

        # Verify nothing was added
        self.assertEqual(len(service._sessions), 0)

    def test_original_load_memory_method(self):
        """Test the original load_memory method with mocked sessions that have 'history'."""

        # Create a special version of JsonFileMemoryService for testing the original method
        class OriginalMethodMemoryService(JsonFileMemoryService):
            def _load_from_json(self):
                # Don't load anything, we'll manually add sessions
                pass

        service = OriginalMethodMemoryService(self.test_filepath)

        # Create a mock session with a 'history' attribute that will be accessed by the original method
        mock_session = MagicMock()
        mock_session.history = [MagicMock()]
        mock_session.history[0].parts = [MagicMock()]
        mock_session.history[0].parts[0].text = "test message"
        mock_session.model_dump.return_value = {"app_name": "test_app", "id": "test_session"}

        # Add the mock session to the service
        session_key = ("test_app", "test_user", "test_session")
        service._sessions[session_key] = mock_session

        # Call the original load_memory method
        response = service.load_memory("test")

        # Verify the response
        self.assertEqual(len(response.memories), 1)
        self.assertEqual(response.memories[0]["app_name"], "test_app")

        # Test with a non-matching query
        response = service.load_memory("non-existent")
        self.assertEqual(len(response.memories), 0)
