"""
Additional unit tests for code_agent.adk.memory module to increase coverage.

These tests focus on edge cases and error conditions to improve test coverage.
"""

import json
import unittest
from datetime import datetime

from code_agent.adk.memory import (
    InMemoryMemoryService,
    Memory,
    MemoryManager,
    MemoryType,
    SearchMemoryResponse,
    get_memory_manager,
    get_memory_service,
)


class TestMemoryAdditional(unittest.TestCase):
    """Additional tests for the Memory class."""

    def test_memory_with_empty_metadata(self):
        """Test creating Memory with empty metadata."""
        memory = Memory(content="Test content", memory_type=MemoryType.SHORT_TERM, metadata={})
        self.assertEqual(memory.metadata, {})

        # Test to_dict with empty metadata
        memory_dict = memory.to_dict()
        self.assertEqual(memory_dict["metadata"], {})

    def test_memory_from_dict_validation(self):
        """Test Memory.from_dict with various input validations."""
        # Test with invalid datetime strings
        mem_dict = {
            "content": "Test content",
            "memory_type": "short_term",
            "importance": 0.5,
            "metadata": {},
            "created_at": "invalid-date",  # Invalid date format
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
        }

        # Should raise ValueError due to invalid date format
        with self.assertRaises(ValueError):
            Memory.from_dict(mem_dict)

        # Test with invalid memory_type
        mem_dict = {
            "content": "Test content",
            "memory_type": "invalid_type",  # Invalid memory type
            "importance": 0.5,
            "metadata": {},
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
        }

        # Should raise ValueError due to invalid memory type
        with self.assertRaises(ValueError):
            Memory.from_dict(mem_dict)


class TestMemoryManagerAdditional(unittest.TestCase):
    """Additional tests for the MemoryManager class."""

    def setUp(self):
        """Set up the test case."""
        self.manager = MemoryManager("test_session")

    def test_search_memories_empty_query(self):
        """Test search_memories with an empty query string."""
        # Add some memories
        self.manager.add_memory(content="Test memory", memory_type=MemoryType.SHORT_TERM)

        # Search with empty query
        response = self.manager.search_memories("")

        # Should return all memories with a score of 0
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].content, "Test memory")
        self.assertEqual(response.results[0].score, 0.0)

    def test_search_memories_no_memories(self):
        """Test search_memories with no memories added."""
        # Search with a query but no memories
        response = self.manager.search_memories("test")

        # Should return empty results
        self.assertEqual(len(response.results), 0)

    def test_search_memories_with_min_score(self):
        """Test search_memories with min_score filter."""
        # Add memories
        self.manager.add_memory(content="Memory mentioning test term", memory_type=MemoryType.SHORT_TERM)
        self.manager.add_memory(content="Memory without the term", memory_type=MemoryType.SHORT_TERM)

        # Search with min_score
        response = self.manager.search_memories("test", min_score=0.5)

        # Should only return memories with score >= min_score
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].content, "Memory mentioning test term")

    def test_search_memories_with_limit(self):
        """Test search_memories with result limit."""
        # Add several memories
        for i in range(10):
            self.manager.add_memory(content=f"Memory {i} with test term", memory_type=MemoryType.SHORT_TERM)

        # Search with limit
        response = self.manager.search_memories("test", limit=3)

        # Should return at most 'limit' memories
        self.assertEqual(len(response.results), 3)

    def test_to_json_serialization(self):
        """Test to_json handles serialization correctly."""
        # Add memory with complex metadata
        complex_metadata = {
            "array": [1, 2, 3],
            "nested": {"key": "value"},
            "datetime": datetime.now().isoformat(),  # Non-serializable directly
        }
        self.manager.add_memory(content="Test memory", memory_type=MemoryType.SHORT_TERM, metadata=complex_metadata)

        # Test serialization
        json_str = self.manager.to_json()

        # Verify it's valid JSON and can be parsed
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["session_id"], "test_session")

    def test_from_dict_empty_memories(self):
        """Test from_dict with empty memories."""
        data = {"session_id": "test_session", "memories": {}}
        manager = MemoryManager.from_dict(data)

        self.assertEqual(manager.session_id, "test_session")
        # Should initialize with empty memories for all types
        self.assertEqual(len(manager.memories[MemoryType.SHORT_TERM]), 0)
        self.assertEqual(len(manager.memories[MemoryType.WORKING]), 0)
        self.assertEqual(len(manager.memories[MemoryType.LONG_TERM]), 0)

    def test_deserialize_invalid_json(self):
        """Test deserialize with invalid JSON."""
        invalid_json = "{"  # Incomplete JSON

        with self.assertRaises(json.JSONDecodeError):
            MemoryManager.deserialize(invalid_json)


class TestBaseMemoryServiceAdditional(unittest.TestCase):
    """Additional tests for the BaseMemoryService class."""

    def test_memory_service_factory(self):
        """Test get_memory_service creates the correct service."""
        service = get_memory_service()
        self.assertIsInstance(service, InMemoryMemoryService)

        # Call it again to test the singleton pattern
        service2 = get_memory_service()
        self.assertIs(service, service2)  # Should be the same instance

    def test_memory_service_empty_search(self):
        """Test search with no memories added."""
        service = InMemoryMemoryService()
        response = service.search("test_session", "query")

        self.assertIsInstance(response, SearchMemoryResponse)
        self.assertEqual(len(response.results), 0)

    def test_memory_service_add_create_manager(self):
        """Test add creates a memory manager if it doesn't exist."""
        # Create the service
        service = InMemoryMemoryService()

        # Add content to a new session
        service.add("new_session", "test content")

        # Verify a manager was created and the content was added
        self.assertIn("new_session", service._managers)

        # Verify memory was added as LONG_TERM (as per implementation)
        memories = service._managers["new_session"].get_memories(MemoryType.LONG_TERM)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].content, "test content")

    def test_memory_service_search_create_manager(self):
        """Test search creates a memory manager if it doesn't exist."""
        # Create the service
        service = InMemoryMemoryService()

        # Add some content first to search
        service.add("new_session", "test query content")

        # Search for the content
        response = service.search("new_session", "test query")

        # Verify a manager was created and search was performed
        self.assertIn("new_session", service._managers)

        # Verify the search returned results
        self.assertEqual(len(response.results), 1)
        self.assertIn("test query", response.results[0].content.lower())


class TestGetMemoryManagerSingleton(unittest.TestCase):
    """Additional tests for get_memory_manager singleton pattern."""

    def test_memory_manager_singleton(self):
        """Test that get_memory_manager returns the same instance for the same session_id."""
        # Get two managers for the same session_id
        manager1 = get_memory_manager("same_session")
        manager2 = get_memory_manager("same_session")

        # They should be the same instance
        self.assertIs(manager1, manager2)

        # Get a manager for a different session_id
        manager3 = get_memory_manager("different_session")

        # It should be a different instance
        self.assertIsNot(manager1, manager3)

    def test_memory_manager_persistence(self):
        """Test that memory manager state persists between calls to get_memory_manager."""
        # Get a manager and add a memory
        manager1 = get_memory_manager("test_session")
        manager1.add_memory(content="Test memory", memory_type=MemoryType.SHORT_TERM)

        # Get the manager again and verify the memory is still there
        manager2 = get_memory_manager("test_session")
        memories = manager2.get_memories(MemoryType.SHORT_TERM)

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].content, "Test memory")
