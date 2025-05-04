"""Additional unit tests for JsonFileMemoryService to increase coverage."""

import json
import os
import tempfile
import unittest

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types as genai_types

from code_agent.adk.json_memory_service import JsonFileMemoryService


class TestJsonFileMemoryServiceAdditional(unittest.TestCase):
    """Additional tests for the JsonFileMemoryService class to increase coverage."""

    def setUp(self):
        """Set up test fixtures, including a temporary file for testing."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "test_memory.json")

        # Create a sample session for testing
        self.sample_session = self._create_sample_session()
        self.sample_session_key_str = f"('{self.sample_session.app_name}', '{self.sample_session.user_id}', '{self.sample_session.id}')"

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
            app_name="test_app",
            user_id="test_user",
            id="test_session",
            events=[user_event, model_event]
        )
        return session

    def _create_memory_service(self, filepath=None):
        """Helper to create a JsonFileMemoryService instance."""
        if filepath is None:
            filepath = self.test_filepath
        return JsonFileMemoryService(filepath)

    def test_search_nodes_empty_session_id(self):
        """Test search_nodes with an empty session ID."""
        service = self._create_memory_service()
        result = service.search_nodes("", "test query")
        self.assertEqual(result, [])

    def test_search_nodes_none_session_id(self):
        """Test search_nodes with None as session ID."""
        service = self._create_memory_service()
        result = service.search_nodes(None, "test query")
        self.assertEqual(result, [])

    def test_search_nodes_invalid_session_id_type(self):
        """Test search_nodes with an invalid session ID type."""
        service = self._create_memory_service()
        result = service.search_nodes(123, "test query")  # Integer instead of string
        self.assertEqual(result, [])

    def test_search_nodes_session_id_not_found(self):
        """Test search_nodes with a session ID that doesn't exist."""
        service = self._create_memory_service()
        result = service.search_nodes("nonexistent_session", "test query")
        self.assertEqual(result, [])

    def test_search_nodes_empty_query(self):
        """Test search_nodes with an empty query."""
        service = self._create_memory_service()

        # Add observations to the session
        service.add_observations("test_session", [
            {"entity_name": "person", "content": "John Doe"},
            {"entity_name": "location", "content": "New York"}
        ])

        # Search with empty query
        result = service.search_nodes("test_session", "")

        # Empty query should return all observations
        self.assertEqual(len(result), 2)

    def test_search_nodes_matching_query(self):
        """Test search_nodes with a query that matches observations."""
        service = self._create_memory_service()

        # Add observations to the session
        service.add_observations("test_session", [
            {"entity_name": "person", "content": "John Doe"},
            {"entity_name": "location", "content": "New York"}
        ])

        # Search with matching query
        result = service.search_nodes("test_session", "John")

        # Should return the matching observation
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_name"], "person")

    def test_search_nodes_non_matching_query(self):
        """Test search_nodes with a query that doesn't match any observations."""
        service = self._create_memory_service()

        # Add observations to the session
        service.add_observations("test_session", [
            {"entity_name": "person", "content": "John Doe"},
            {"entity_name": "location", "content": "New York"}
        ])

        # Search with non-matching query
        result = service.search_nodes("test_session", "Paris")

        # Should return an empty list
        self.assertEqual(result, [])

    def test_add_observations_empty_session_id(self):
        """Test add_observations with an empty session ID."""
        service = self._create_memory_service()
        service.add_observations("", [{"entity_name": "test", "content": "test"}])

        # Should not add observations with empty session ID
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_add_observations_none_session_id(self):
        """Test add_observations with None as session ID."""
        service = self._create_memory_service()
        service.add_observations(None, [{"entity_name": "test", "content": "test"}])

        # Should not add observations with None session ID
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_add_observations_invalid_session_id_type(self):
        """Test add_observations with an invalid session ID type."""
        service = self._create_memory_service()
        service.add_observations(123, [{"entity_name": "test", "content": "test"}])  # Integer instead of string

        # Should not add observations with invalid session ID type
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_add_observations_invalid_observations_type(self):
        """Test add_observations with observations that aren't a list."""
        service = self._create_memory_service()
        service.add_observations("test_session", {"entity_name": "test", "content": "test"})  # Dict instead of list

        # Should not add observations with invalid observations type
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_add_observations_valid(self):
        """Test add_observations with valid parameters."""
        service = self._create_memory_service()
        observations = [
            {"entity_name": "person", "content": "John Doe"},
            {"entity_name": "location", "content": "New York"}
        ]
        service.add_observations("test_session", observations)

        # Should add observations
        self.assertEqual(len(service._memory_store.facts), 1)
        self.assertEqual(len(service._memory_store.facts["test_session"]), 2)
        self.assertEqual(service._memory_store.facts["test_session"][0]["entity_name"], "person")
        self.assertEqual(service._memory_store.facts["test_session"][1]["entity_name"], "location")

    def test_add_observations_append_to_existing(self):
        """Test add_observations appending to existing observations."""
        service = self._create_memory_service()

        # Add initial observations
        service.add_observations("test_session", [{"entity_name": "person", "content": "John Doe"}])

        # Add more observations
        service.add_observations("test_session", [{"entity_name": "location", "content": "New York"}])

        # Should append to existing observations
        self.assertEqual(len(service._memory_store.facts["test_session"]), 2)
        self.assertEqual(service._memory_store.facts["test_session"][0]["entity_name"], "person")
        self.assertEqual(service._memory_store.facts["test_session"][1]["entity_name"], "location")

    def test_load_from_json_old_format(self):
        """Test loading from old format JSON file."""
        # Create a JSON file with the old structure (just sessions, no facts)
        session_dump = self.sample_session.model_dump(mode="json")
        old_data = {self.sample_session_key_str: session_dump}

        with open(self.test_filepath, "w") as f:
            json.dump(old_data, f)

        # Initialize service, which should migrate the data
        service = self._create_memory_service()

        # Verify the session was loaded and migrated
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)
        self.assertEqual(service._memory_store.sessions[self.sample_session_key_str]["id"], "test_session")
        self.assertEqual(len(service._memory_store.facts), 0)  # Facts should be initialized empty

    def test_load_from_json_invalid_format(self):
        """Test loading from JSON with an invalid format."""
        # Create a JSON file with an invalid structure (not a dict)
        with open(self.test_filepath, "w") as f:
            json.dump(["not", "a", "dict"], f)

        # Initialize service, which should handle the invalid format
        service = self._create_memory_service()

        # Verify no sessions were loaded
        self.assertEqual(len(service._memory_store.sessions), 0)
        self.assertEqual(len(service._memory_store.facts), 0)

    def test_parse_str_key_valid(self):
        """Test parsing a valid string key."""
        service = self._create_memory_service()
        key_str = "('app', 'user', 'session')"
        parsed_key = service._parse_str_key(key_str)
        self.assertEqual(parsed_key, ('app', 'user', 'session'))

    def test_parse_str_key_invalid_format(self):
        """Test parsing an invalid string key format."""
        service = self._create_memory_service()
        key_str = "not a tuple"
        parsed_key = service._parse_str_key(key_str)
        self.assertIsNone(parsed_key)

    def test_parse_str_key_wrong_length(self):
        """Test parsing a string key with wrong tuple length."""
        service = self._create_memory_service()
        key_str = "('app', 'user')"  # Only 2 elements
        parsed_key = service._parse_str_key(key_str)
        self.assertIsNone(parsed_key)

    def test_parse_str_key_syntax_error(self):
        """Test parsing a string key with syntax error."""
        service = self._create_memory_service()
        key_str = "('app', 'user', 'session'"  # Missing closing parenthesis
        parsed_key = service._parse_str_key(key_str)
        self.assertIsNone(parsed_key)

    def test_get_memory_service_info(self):
        """Test getting memory service info."""
        service = self._create_memory_service()
        info = service.get_memory_service_info()

        self.assertIsInstance(info, dict)
        self.assertIn("service_type", info)
        self.assertEqual(info["service_type"], "JsonFileMemoryService")
        self.assertIn("description", info)
        self.assertIn("filepath", info)
        self.assertIn("capabilities", info)
