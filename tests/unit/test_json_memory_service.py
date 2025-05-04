"""
Unit tests for JsonFileMemoryService in code_agent.adk.json_memory_service.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import mock_open, patch

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types as genai_types

from code_agent.adk.json_memory_service import JsonFileMemoryService, JsonMemoryStore, MemoryServiceResponse


class TestJsonFileMemoryServiceClass(unittest.TestCase):
    """Tests for the JsonFileMemoryService class."""

    def setUp(self):
        """Set up test fixtures, including a temporary file for testing."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "test_memory.json")

        # Create a sample session for testing
        self.sample_session = self._create_sample_session()
        # Define the expected string key for the sample session
        self.sample_session_key_str = f"('{self.sample_session.app_name}', '{self.sample_session.user_id}', '{self.sample_session.id}')"

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
        """Helper to create a JsonFileMemoryService instance."""
        if filepath is None:
            filepath = self.test_filepath
        return JsonFileMemoryService(filepath)

    def test_init_new_file(self):
        """Test initialization with a new file path."""
        # Test initialization with a file that doesn't exist
        service = self._create_memory_service()

        # Verify the service is initialized correctly
        self.assertEqual(service.filepath, self.test_filepath)
        self.assertIsInstance(service._memory_store, JsonMemoryStore)
        self.assertEqual(len(service._memory_store.sessions), 0)
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_add_session_to_memory(self):
        """Test adding a session to memory."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Verify the session was added using the string key
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)
        self.assertEqual(service._memory_store.sessions[self.sample_session_key_str]["id"], self.sample_session.id)

        # Verify the file was created/updated (implicitly tested by add_session_to_memory calling _save_to_json)
        self.assertTrue(os.path.exists(self.test_filepath))

    def test_load_memory_with_matching_query(self):
        """Test loading memory with a query that matches session content."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Search for a query that matches the message text
        response = service.search_memory("test message")

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
        response = service.search_memory("non-existent query")

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
        self.assertIsInstance(results, MemoryServiceResponse)
        self.assertEqual(len(results.memories), 1)
        self.assertEqual(results.memories[0]["app_name"], "test_app")

        # Test with non-matching query
        empty_results = service.search_memory("non-existent query")
        self.assertIsInstance(empty_results, MemoryServiceResponse)
        self.assertEqual(len(empty_results.memories), 0)

    def test_load_from_json_valid_file(self):
        """Test loading sessions from a valid JSON file."""
        # Create a valid JSON file with the new structure
        session_dump = self.sample_session.model_dump(mode="json")
        valid_data = {"sessions": {self.sample_session_key_str: session_dump}, "facts": {}}

        with open(self.test_filepath, "w") as f:
            json.dump(valid_data, f)

        # Initialize service, which should load the file
        service = self._create_memory_service()

        # Verify the session was loaded into the memory store
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)
        loaded_session_data = service._memory_store.sessions[self.sample_session_key_str]
        self.assertEqual(loaded_session_data["app_name"], "test_app")
        self.assertEqual(loaded_session_data["user_id"], "test_user")
        self.assertEqual(loaded_session_data["id"], "test_session")

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
        self.assertEqual(len(service._memory_store.sessions), 0)

    @patch("os.path.exists")
    def test_load_from_json_file_not_found(self, mock_exists):
        """Test handling of a non-existent file."""
        # Set up mock to simulate file not found
        mock_exists.return_value = False

        # Initialize service with a non-existent file
        service = self._create_memory_service()

        # Verify no sessions were loaded and no errors were raised
        self.assertEqual(len(service._memory_store.sessions), 0)

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
            self.assertEqual(len(service._memory_store.sessions), 0)

    def test_load_from_json_invalid_key_format(self):
        """Test loading with invalid key format in the JSON file."""
        # Create a JSON file with valid structure but potentially bad session key
        # (Note: Pydantic might catch malformed session dumps earlier now)
        invalid_session_dump = self.sample_session.model_dump(mode="json")
        valid_data_bad_key = {"sessions": {"bad key": invalid_session_dump}, "facts": {}}

        with open(self.test_filepath, "w") as f:
            json.dump(valid_data_bad_key, f)

        # Initialize service
        service = self._create_memory_service()

        # Verify the session with the bad key might be loaded but potentially unusable,
        # or simply check if the store remains empty if validation fails harshly.
        # Let's assume it loads the key as is for now.
        self.assertNotIn("bad key", service._memory_store.sessions)
        self.assertEqual(len(service._memory_store.sessions), 0)

    def test_load_from_json_invalid_session_data(self):
        """Test loading with invalid session data in the JSON file."""
        # Create a JSON file with the correct outer structure but invalid inner session data
        invalid_session_data = {"invalid": "data"}
        valid_structure_invalid_session = {"sessions": {self.sample_session_key_str: invalid_session_data}, "facts": {}}

        with open(self.test_filepath, "w") as f:
            json.dump(valid_structure_invalid_session, f)

        # Initialize service, which should handle the invalid session data gracefully
        service = self._create_memory_service()

        # Verify no valid sessions were loaded (or the invalid one was skipped)
        self.assertEqual(len(service._memory_store.sessions), 0)

    def test_save_to_json(self):
        """Test saving sessions to a JSON file."""
        service = self._create_memory_service()

        # Add the sample session to memory
        service.add_session_to_memory(self.sample_session)

        # Force save to JSON (add_session calls it, but call again for explicitness if needed)
        service._save_to_json()

        # Verify the file was created
        self.assertTrue(os.path.exists(self.test_filepath))

        # Verify the contents of the file
        with open(self.test_filepath, "r") as f:
            saved_data = json.load(f)

        # Verify the saved data structure and content
        self.assertIn("sessions", saved_data)
        self.assertIn("facts", saved_data)
        self.assertIsInstance(saved_data["sessions"], dict)
        self.assertIn(self.sample_session_key_str, saved_data["sessions"])
        # Compare saved session dump with original dump
        saved_session_dump = saved_data["sessions"][self.sample_session_key_str]
        original_session_dump = self.sample_session.model_dump(mode="json")
        self.assertDictEqual(saved_session_dump, original_session_dump)

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
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)

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
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)

    def test_add_invalid_session(self):
        """Test adding an invalid object as a session."""
        service = self._create_memory_service()

        # Try to add something that's not a Session
        service.add_session_to_memory("not a session")

        # Verify nothing was added
        self.assertEqual(len(service._memory_store.sessions), 0)
