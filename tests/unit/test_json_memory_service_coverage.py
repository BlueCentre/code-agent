"""
Additional unit tests to increase coverage for JsonFileMemoryService.

These tests focus on edge cases and error handling in the json_memory_service module.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types as genai_types

from code_agent.adk.json_memory_service import JsonFileMemoryService


class TestJsonFileMemoryServiceCoverage(unittest.TestCase):
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

    def test_search_memory_with_different_content_types(self):
        """Test search_memory with different types of content."""
        service = self._create_memory_service()

        # Create a session with various content types
        user_content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part(text="Complex multipart message"),
                genai_types.Part(inline_data=genai_types.InlineData(mime_type="text/plain", data="Some data")),
            ],
        )
        model_content = genai_types.Content(
            role="model",
            parts=[
                genai_types.Part(text="Complex response"),
                genai_types.Part(function_response=genai_types.FunctionResponse(name="test_function", response={"result": "test"})),
            ],
        )

        # Create events from content
        user_event = Event(author="user", content=user_content)
        model_event = Event(author="model", content=model_content)

        # Create and add session
        complex_session = Session(app_name="test_app", user_id="test_user", id="complex_session", events=[user_event, model_event])
        service.add_session_to_memory(complex_session)

        # Search for content in text parts
        response = service.search_memory("multipart")
        self.assertEqual(len(response.memories), 1)
        self.assertEqual(response.memories[0]["id"], "complex_session")

        # Search for content in function response
        response = service.search_memory("test_function")
        self.assertEqual(len(response.memories), 1)
        self.assertEqual(response.memories[0]["id"], "complex_session")

        # Search for non-existent content
        response = service.search_memory("nonexistent")
        self.assertEqual(len(response.memories), 0)

    def test_add_observations_with_complex_content(self):
        """Test add_observations with complex content types."""
        service = self._create_memory_service()

        # Add observations with different data structures
        observations = [
            {"entity_name": "test1", "content": "Simple string content"},
            {"entity_name": "test2", "content": {"nested": "object", "with": ["array", "elements"]}},
            {"entity_name": "test3", "content": [1, 2, 3, "mixed", {"type": "array"}]},
        ]
        service.add_observations("test_session", observations)

        # Verify observations were added
        self.assertIn("test_session", service._memory_store.facts)
        self.assertEqual(len(service._memory_store.facts["test_session"]), 3)

        # Verify the observations can be searched
        results = service.search_nodes("test_session", "simple string")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entity_name"], "test1")

        # Search for content in nested objects
        results = service.search_nodes("test_session", "array")
        self.assertEqual(len(results), 2)  # Should find both test2 and test3

    def test_search_nodes_with_malformed_observation(self):
        """Test search_nodes with malformed observations that don't match expected structure."""
        service = self._create_memory_service()

        # Add malformed observations (missing required fields)
        malformed_observations = [
            {"content": "Missing entity_name"},  # Missing entity_name
            {"entity_name": "missing_content"},  # Missing content
            {"entity_name": "test", "content": "valid observation"},  # Valid observation
        ]

        # Manually add to facts to bypass validation in add_observations
        service._memory_store.facts["test_session"] = malformed_observations

        # Search should handle gracefully and only match valid observations
        results = service.search_nodes("test_session", "valid")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entity_name"], "test")

    @patch("os.path.exists")
    @patch("json.dump")
    def test_save_to_json_unexpected_error(self, mock_dump, mock_exists):
        """Test handling of an unexpected error during save_to_json."""
        mock_exists.return_value = True
        mock_dump.side_effect = Exception("Unexpected error during save")

        service = self._create_memory_service()

        # This should not raise an exception, as it's handled internally
        service.add_session_to_memory(self.sample_session)

        # Verify the session was still added to memory, even if saving failed
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)

    def test_search_memory_with_event_without_content(self):
        """Test search_memory with events that don't have content attribute."""
        service = self._create_memory_service()

        # Create an event with missing content attribute
        custom_event = Event(author="user", event_type="custom")  # No content

        # Create and add session
        session = Session(app_name="test_app", user_id="test_user", id="no_content_session", events=[custom_event])
        service.add_session_to_memory(session)

        # Search should handle gracefully and not raise exceptions
        response = service.search_memory("test")
        self.assertEqual(len(response.memories), 0)

    def test_search_memory_with_invalid_event_type(self):
        """Test search_memory with invalid event types."""
        service = self._create_memory_service()

        # Manually create a session with invalid event type
        invalid_session_data = {
            "app_name": "test_app",
            "user_id": "test_user",
            "id": "invalid_event_session",
            "events": [{"author": "user", "event_type": "unknown", "content": {"text": "This is invalid"}}],
        }

        # Manually add session to bypass validation
        session_key = "('test_app', 'test_user', 'invalid_event_session')"
        service._memory_store.sessions[session_key] = invalid_session_data

        # Search should handle gracefully and not raise exceptions
        response = service.search_memory("invalid")
        self.assertEqual(len(response.memories), 0)

    def test_get_memory_service_info_detailed(self):
        """Test get_memory_service_info with different states of the memory service."""
        service = self._create_memory_service()

        # Check initial info
        info = service.get_memory_service_info()
        self.assertEqual(info["type"], "JsonFileMemoryService")
        self.assertEqual(info["filepath"], self.test_filepath)
        self.assertEqual(info["session_count"], 0)
        self.assertEqual(info["fact_session_count"], 0)

        # Add a session
        service.add_session_to_memory(self.sample_session)

        # Add observations
        service.add_observations("test_session", [{"entity_name": "test", "content": "test"}])

        # Check updated info
        info = service.get_memory_service_info()
        self.assertEqual(info["session_count"], 1)
        self.assertEqual(info["fact_session_count"], 1)

    def test_search_memory_case_insensitive(self):
        """Test search_memory is case-insensitive."""
        service = self._create_memory_service()
        service.add_session_to_memory(self.sample_session)

        # Search with different case
        response = service.search_memory("TEST MESSAGE")
        self.assertEqual(len(response.memories), 1)

        response = service.search_memory("test RESPONSE")
        self.assertEqual(len(response.memories), 1)

    def test_search_nodes_case_insensitive(self):
        """Test search_nodes is case-insensitive."""
        service = self._create_memory_service()
        observations = [{"entity_name": "person", "content": "John Doe"}]
        service.add_observations("test_session", observations)

        # Search with different case
        results = service.search_nodes("test_session", "JOHN")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entity_name"], "person")

    def test_load_from_json_with_facts_and_observations(self):
        """Test loading from JSON with both sessions and facts/observations."""
        session_dump = self.sample_session.model_dump(mode="json")
        facts = {"test_session": [{"entity_name": "person", "content": "John Doe"}, {"entity_name": "location", "content": "New York"}]}

        test_data = {"sessions": {self.sample_session_key_str: session_dump}, "facts": facts}

        with open(self.test_filepath, "w") as f:
            json.dump(test_data, f)

        # Initialize service, which should load the file
        service = self._create_memory_service()

        # Verify sessions were loaded
        self.assertIn(self.sample_session_key_str, service._memory_store.sessions)

        # Verify facts were loaded
        self.assertIn("test_session", service._memory_store.facts)
        self.assertEqual(len(service._memory_store.facts["test_session"]), 2)
        self.assertEqual(service._memory_store.facts["test_session"][0]["entity_name"], "person")
        self.assertEqual(service._memory_store.facts["test_session"][1]["entity_name"], "location")
