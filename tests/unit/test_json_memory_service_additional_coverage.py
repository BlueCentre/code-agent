"""
Tests to increase coverage for code_agent.adk.json_memory_service.py.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from google.adk.sessions import Session

from code_agent.adk.json_memory_service import (
    JsonFileMemoryService,
    JsonMemoryStore,
    MemoryFact,
    MemoryServiceResponse,
)


class TestJsonMemoryServiceAdditionalCoverage:
    """Additional tests for JsonFileMemoryService to increase coverage."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for memory files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "test_memory.json")

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def _create_memory_service(self, filepath=None):
        """Helper to create a JsonFileMemoryService instance."""
        if filepath is None:
            filepath = self.test_filepath
        return JsonFileMemoryService(filepath)

    def _create_sample_session(self, app_name="test_app", user_id="test_user", session_id="test_session"):
        """Create a sample session with events for testing."""
        session = MagicMock(spec=Session)
        session.app_name = app_name
        session.user_id = user_id
        session.id = session_id

        # Simulate model_dump method
        session.model_dump.return_value = {"app_name": app_name, "user_id": user_id, "id": session_id, "events": []}

        return session

    def test_get_str_key(self):
        """Test the _get_str_key method."""
        service = self._create_memory_service()

        # Test with valid inputs
        key = service._get_str_key("app1", "user1", "session1")

        # The key should be a string representation of the tuple
        assert key == "('app1', 'user1', 'session1')"

    def test_add_session_to_memory_non_session(self):
        """Test adding a non-Session object to memory."""
        service = self._create_memory_service()

        # Add a non-Session object
        service.add_session_to_memory("not a session")

        # Verify nothing was added
        assert len(service._memory_store.sessions) == 0

    def test_add_observations_empty_list(self):
        """Test adding empty list of observations."""
        service = self._create_memory_service()

        # Add empty list of observations
        service.add_observations("test_session", [])

        # Verify session_id key was created but no observations added
        assert "test_session" in service._memory_store.facts
        assert len(service._memory_store.facts["test_session"]) == 0

    def test_add_observations_invalid_inputs(self):
        """Test adding observations with invalid inputs."""
        service = self._create_memory_service()

        # Test with None session_id
        service.add_observations(None, [{"entity_name": "test", "content": "test content"}])
        assert len(service._memory_store.facts) == 0

        # Test with non-string session_id
        service.add_observations(123, [{"entity_name": "test", "content": "test content"}])
        assert len(service._memory_store.facts) == 0

        # Test with non-list observations
        service.add_observations("test_session", "not a list")
        assert len(service._memory_store.facts) == 0

    def test_add_observations_valid(self):
        """Test adding valid observations."""
        service = self._create_memory_service()

        # Add valid observations
        observations = [{"entity_name": "entity1", "content": "content1"}, {"entity_name": "entity2", "content": "content2"}]
        service.add_observations("test_session", observations)

        # Verify observations were added
        assert "test_session" in service._memory_store.facts
        assert len(service._memory_store.facts["test_session"]) == 2
        assert service._memory_store.facts["test_session"][0]["entity_name"] == "entity1"
        assert service._memory_store.facts["test_session"][1]["entity_name"] == "entity2"

    def test_search_nodes_invalid_session_id(self):
        """Test searching nodes with invalid session_id."""
        service = self._create_memory_service()

        # Test with None session_id
        result = service.search_nodes(None, "query")
        assert result == []

        # Test with non-string session_id
        result = service.search_nodes(123, "query")
        assert result == []

    def test_search_nodes_no_matching_nodes(self):
        """Test searching nodes with no matching results."""
        service = self._create_memory_service()

        # Add some observations
        observations = [{"entity_name": "entity1", "content": "content1"}, {"entity_name": "entity2", "content": "content2"}]
        service.add_observations("test_session", observations)

        # Search with non-matching query
        result = service.search_nodes("test_session", "nonexistent")

        # Verify no results were found
        assert len(result) == 0

    def test_search_nodes_with_matching_nodes(self):
        """Test searching nodes with matching results."""
        service = self._create_memory_service()

        # Add some observations
        observations = [{"entity_name": "entity1", "content": "matching content"}, {"entity_name": "entity2", "content": "other content"}]
        service.add_observations("test_session", observations)

        # Search with matching query
        result = service.search_nodes("test_session", "matching")

        # Verify matching results were found
        assert len(result) == 1
        assert result[0]["entity_name"] == "entity1"
        assert result[0]["content"] == "matching content"

    def test_search_nodes_session_not_in_facts(self):
        """Test searching nodes for a session not in facts."""
        service = self._create_memory_service()

        # Search for nonexistent session
        result = service.search_nodes("nonexistent_session", "query")

        # Verify empty result
        assert len(result) == 0

    def test_save_to_json_with_unexpected_error(self):
        """Test _save_to_json with an unexpected error."""
        service = self._create_memory_service()

        # Add a session
        session = self._create_sample_session()
        service.add_session_to_memory(session)

        # Mock json.dump to raise an unexpected error
        with patch("json.dump") as mock_dump:
            mock_dump.side_effect = Exception("Unexpected error")

            # Call _save_to_json, which should handle the error gracefully
            service._save_to_json()

            # Verify state is still intact
            key = service._get_str_key(session.app_name, session.user_id, session.id)
            assert key in service._memory_store.sessions

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_load_from_json_with_unexpected_error(self, mock_open, mock_exists):
        """Test _load_from_json with an unexpected error."""
        # Set up mocks
        mock_exists.return_value = True
        mock_open.side_effect = Exception("Unexpected error")

        # Create service, which will call _load_from_json
        service = self._create_memory_service()

        # Verify empty store was created despite the error
        assert isinstance(service._memory_store, JsonMemoryStore)
        assert len(service._memory_store.sessions) == 0
        assert len(service._memory_store.facts) == 0

    def test_load_from_json_old_format(self):
        """Test loading from old format JSON file."""
        # Create a file with old format (just sessions dict, no facts)
        old_data = {"('app1', 'user1', 'session1')": {"app_name": "app1", "user_id": "user1", "id": "session1", "events": []}}
        with open(self.test_filepath, "w") as f:
            json.dump(old_data, f)

        # Create service, which will load the file
        service = self._create_memory_service()

        # Verify sessions were loaded and facts dict was created
        assert len(service._memory_store.sessions) == 1
        assert len(service._memory_store.facts) == 0
        assert "('app1', 'user1', 'session1')" in service._memory_store.sessions

    def test_load_from_json_with_invalid_session_keys(self):
        """Test loading from JSON with invalid session keys."""
        # Create a file with some valid and some invalid keys
        data = {
            "sessions": {
                "('app1', 'user1', 'session1')": {  # Valid key format
                    "app_name": "app1",
                    "user_id": "user1",
                    "id": "session1",
                    "events": [],
                },
                "invalid-key": {  # Invalid key format
                    "app_name": "app2",
                    "user_id": "user2",
                    "id": "session2",
                    "events": [],
                },
                "('app3', 'user3')": {  # Invalid tuple length
                    "app_name": "app3",
                    "user_id": "user3",
                    "id": "session3",
                    "events": [],
                },
            },
            "facts": {},
        }
        with open(self.test_filepath, "w") as f:
            json.dump(data, f)

        # Create service, which will load the file
        service = self._create_memory_service()

        # Verify only valid sessions were loaded
        assert len(service._memory_store.sessions) == 1
        assert "('app1', 'user1', 'session1')" in service._memory_store.sessions
        assert "invalid-key" not in service._memory_store.sessions
        assert "('app3', 'user3')" not in service._memory_store.sessions

    def test_memory_fact_dataclass(self):
        """Test the MemoryFact dataclass."""
        # Create a MemoryFact
        fact = MemoryFact(entity_name="test-entity", content={"type": "observation", "text": "This is a test"})

        # Verify attributes
        assert fact.entity_name == "test-entity"
        assert fact.content["type"] == "observation"
        assert fact.content["text"] == "This is a test"

    def test_memory_service_response_dataclass(self):
        """Test the MemoryServiceResponse dataclass."""
        # Create a MemoryServiceResponse
        memories = [{"id": "memory1"}, {"id": "memory2"}]
        response = MemoryServiceResponse(memories=memories)

        # Verify attributes
        assert len(response.memories) == 2
        assert response.memories[0]["id"] == "memory1"
        assert response.memories[1]["id"] == "memory2"
