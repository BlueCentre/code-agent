"""
Unit tests for code_agent.adk.memory module.
"""

import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from code_agent.adk.memory import (
    BaseMemoryService,
    Memory,
    MemoryManager,
    MemoryResult,
    MemoryType,
    SearchMemoryResponse,
    get_memory_manager,
)


class TestMemoryClasses(unittest.TestCase):
    """Test the base memory classes."""

    def test_memory_result(self):
        """Test the MemoryResult class."""
        # Test with minimal arguments
        result = MemoryResult(content="Test content")
        self.assertEqual(result.content, "Test content")
        self.assertEqual(result.metadata, {})
        self.assertIsNone(result.score)

        # Test with all arguments
        result = MemoryResult(content="Test content", metadata={"key": "value"}, score=0.9)
        self.assertEqual(result.content, "Test content")
        self.assertEqual(result.metadata, {"key": "value"})
        self.assertEqual(result.score, 0.9)

        # Test to_dict method
        result_dict = result.to_dict()
        self.assertEqual(result_dict["content"], "Test content")
        self.assertEqual(result_dict["metadata"], {"key": "value"})
        self.assertEqual(result_dict["score"], 0.9)

    def test_search_memory_response(self):
        """Test the SearchMemoryResponse class."""
        # Test with empty results
        response = SearchMemoryResponse()
        self.assertEqual(response.results, [])

        # Test with provided results
        results = [MemoryResult(content="Result 1", score=0.9), MemoryResult(content="Result 2", score=0.8)]
        response = SearchMemoryResponse(results=results)
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.results[0].content, "Result 1")
        self.assertEqual(response.results[1].content, "Result 2")

        # Test to_dict method
        response_dict = response.to_dict()
        self.assertEqual(len(response_dict["results"]), 2)
        self.assertEqual(response_dict["results"][0]["content"], "Result 1")
        self.assertEqual(response_dict["results"][1]["content"], "Result 2")

    def test_memory(self):
        """Test the Memory class."""
        # Test with minimal arguments
        memory = Memory(content="Test memory", memory_type=MemoryType.SHORT_TERM)
        self.assertEqual(memory.content, "Test memory")
        self.assertEqual(memory.memory_type, MemoryType.SHORT_TERM)
        self.assertEqual(memory.importance, 1.0)  # Default value
        self.assertEqual(memory.metadata, {})
        self.assertIsInstance(memory.created_at, datetime)
        self.assertIsInstance(memory.last_accessed, datetime)
        self.assertEqual(memory.access_count, 0)

        # Test with all arguments
        memory = Memory(content="Test memory", memory_type=MemoryType.LONG_TERM, importance=0.7, metadata={"key": "value"})
        self.assertEqual(memory.content, "Test memory")
        self.assertEqual(memory.memory_type, MemoryType.LONG_TERM)
        self.assertEqual(memory.importance, 0.7)
        self.assertEqual(memory.metadata, {"key": "value"})

        # Test to_dict method
        memory_dict = memory.to_dict()
        self.assertEqual(memory_dict["content"], "Test memory")
        self.assertEqual(memory_dict["memory_type"], "long_term")
        self.assertEqual(memory_dict["importance"], 0.7)
        self.assertEqual(memory_dict["metadata"], {"key": "value"})
        self.assertIn("created_at", memory_dict)
        self.assertIn("last_accessed", memory_dict)
        self.assertEqual(memory_dict["access_count"], 0)

        # Test from_dict method
        # First create a complete dictionary
        now = datetime.now()
        now_str = now.isoformat()
        mem_dict = {
            "content": "Reconstructed memory",
            "memory_type": "working",
            "importance": 0.5,
            "metadata": {"source": "test"},
            "created_at": now_str,
            "last_accessed": now_str,
            "access_count": 3,
        }

        # Reconstruct the Memory object
        reconstructed = Memory.from_dict(mem_dict)
        self.assertEqual(reconstructed.content, "Reconstructed memory")
        self.assertEqual(reconstructed.memory_type, MemoryType.WORKING)
        self.assertEqual(reconstructed.importance, 0.5)
        self.assertEqual(reconstructed.metadata, {"source": "test"})
        self.assertEqual(reconstructed.created_at.isoformat(), now_str)
        self.assertEqual(reconstructed.last_accessed.isoformat(), now_str)
        self.assertEqual(reconstructed.access_count, 3)


class TestMemoryManager(unittest.TestCase):
    """Test the MemoryManager class."""

    def setUp(self):
        """Set up the test case."""
        self.manager = MemoryManager("test_session")

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.manager.session_id, "test_session")
        self.assertEqual(len(self.manager.memories), 3)  # Three memory types
        self.assertEqual(len(self.manager.memories[MemoryType.SHORT_TERM]), 0)
        self.assertEqual(len(self.manager.memories[MemoryType.WORKING]), 0)
        self.assertEqual(len(self.manager.memories[MemoryType.LONG_TERM]), 0)

    def test_add_memory(self):
        """Test the add_memory method."""
        # Add a memory
        self.manager.add_memory(content="Test memory", memory_type=MemoryType.SHORT_TERM, importance=0.8, metadata={"key": "value"})

        # Verify it was added
        self.assertEqual(len(self.manager.memories[MemoryType.SHORT_TERM]), 1)
        memory = self.manager.memories[MemoryType.SHORT_TERM][0]
        self.assertEqual(memory.content, "Test memory")
        self.assertEqual(memory.memory_type, MemoryType.SHORT_TERM)
        self.assertEqual(memory.importance, 0.8)
        self.assertEqual(memory.metadata, {"key": "value"})

        # Add another memory of a different type
        self.manager.add_memory(content="Working memory", memory_type=MemoryType.WORKING)

        # Verify both memories exist
        self.assertEqual(len(self.manager.memories[MemoryType.SHORT_TERM]), 1)
        self.assertEqual(len(self.manager.memories[MemoryType.WORKING]), 1)
        self.assertEqual(len(self.manager.memories[MemoryType.LONG_TERM]), 0)

    def test_get_memories_with_type(self):
        """Test the get_memories method with a specific memory type."""
        # Add memories of different types
        self.manager.add_memory(content="Memory 1", memory_type=MemoryType.SHORT_TERM, importance=0.5)
        self.manager.add_memory(content="Memory 2", memory_type=MemoryType.SHORT_TERM, importance=0.9)
        self.manager.add_memory(content="Memory 3", memory_type=MemoryType.WORKING, importance=0.7)

        # Get SHORT_TERM memories
        memories = self.manager.get_memories(memory_type=MemoryType.SHORT_TERM)
        self.assertEqual(len(memories), 2)
        self.assertEqual(memories[0].content, "Memory 1")
        self.assertEqual(memories[1].content, "Memory 2")

        # Verify access counts and timestamps were updated
        self.assertEqual(memories[0].access_count, 1)
        self.assertEqual(memories[1].access_count, 1)

        # Get with importance filter
        memories = self.manager.get_memories(memory_type=MemoryType.SHORT_TERM, min_importance=0.7)
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0].content, "Memory 2")
        self.assertEqual(memories[0].access_count, 2)  # Incremented again

    def test_get_memories_all_types(self):
        """Test the get_memories method without specifying a type."""
        # Add memories of different types
        self.manager.add_memory(content="Memory 1", memory_type=MemoryType.SHORT_TERM, importance=0.5)
        self.manager.add_memory(content="Memory 2", memory_type=MemoryType.WORKING, importance=0.9)
        self.manager.add_memory(content="Memory 3", memory_type=MemoryType.LONG_TERM, importance=0.7)

        # Get all memories
        memories = self.manager.get_memories()
        self.assertEqual(len(memories), 3)

        # Get with importance filter
        memories = self.manager.get_memories(min_importance=0.6)
        self.assertEqual(len(memories), 2)
        # Just check contents since order is not guaranteed
        contents = [m.content for m in memories]
        self.assertIn("Memory 2", contents)
        self.assertIn("Memory 3", contents)

    def test_search_memories(self):
        """Test the search_memories method with direct method call."""
        # Add some memories
        self.manager.add_memory(content="Python is a programming language", memory_type=MemoryType.LONG_TERM)
        self.manager.add_memory(content="JavaScript is used for web development", memory_type=MemoryType.LONG_TERM)
        self.manager.add_memory(content="Python has great libraries for data science", memory_type=MemoryType.LONG_TERM)

        # Test searching for different terms
        python_response = self.manager.search_memories(query="python")
        web_response = self.manager.search_memories(query="web", memory_type=MemoryType.LONG_TERM)
        limit_response = self.manager.search_memories(query="python", limit=1)

        # Test that results contain the expected content
        python_contents = [r.content for r in python_response.results]
        self.assertIn("Python is a programming language", python_contents)
        self.assertIn("Python has great libraries for data science", python_contents)

        # Test that searching for web finds JavaScript content
        web_contents = [r.content for r in web_response.results]
        self.assertIn("JavaScript is used for web development", web_contents)

        # Test that limit parameter works
        self.assertEqual(len(limit_response.results), 1)

    def test_clear_memories(self):
        """Test the clear_memories method."""
        # Add memories of different types
        self.manager.add_memory(content="Memory 1", memory_type=MemoryType.SHORT_TERM)
        self.manager.add_memory(content="Memory 2", memory_type=MemoryType.WORKING)
        self.manager.add_memory(content="Memory 3", memory_type=MemoryType.LONG_TERM)

        # Clear only SHORT_TERM memories
        self.manager.clear_memories(memory_type=MemoryType.SHORT_TERM)
        self.assertEqual(len(self.manager.memories[MemoryType.SHORT_TERM]), 0)
        self.assertEqual(len(self.manager.memories[MemoryType.WORKING]), 1)
        self.assertEqual(len(self.manager.memories[MemoryType.LONG_TERM]), 1)

        # Clear all memories
        self.manager.clear_memories()
        self.assertEqual(len(self.manager.memories[MemoryType.SHORT_TERM]), 0)
        self.assertEqual(len(self.manager.memories[MemoryType.WORKING]), 0)
        self.assertEqual(len(self.manager.memories[MemoryType.LONG_TERM]), 0)

    def test_summarize_conversation(self):
        """Test the summarize_conversation method."""
        mock_session = MagicMock()

        # Test with no memories
        summary = self.manager.summarize_conversation(mock_session)
        self.assertEqual(summary, "No conversation data to summarize.")

        # Test with a memory
        self.manager.add_memory(content="User asked about Python performance", memory_type=MemoryType.SHORT_TERM)
        summary = self.manager.summarize_conversation(mock_session)
        self.assertEqual(summary, "Conversation summary: User asked about Python performance")

    def test_extract_memories_from_session(self):
        """Test the extract_memories_from_session method."""
        mock_session = MagicMock()
        # This method is a placeholder in the implementation, so just ensure it doesn't crash
        self.manager.extract_memories_from_session(mock_session)

    def test_to_dict_and_to_json(self):
        """Test the to_dict and to_json methods."""
        # Add a memory
        self.manager.add_memory(content="Serialization test", memory_type=MemoryType.LONG_TERM, metadata={"test": True})

        # Convert to dict
        manager_dict = self.manager.to_dict()
        self.assertEqual(manager_dict["session_id"], "test_session")
        self.assertIn("memories", manager_dict)
        self.assertIn("long_term", manager_dict["memories"])
        self.assertEqual(len(manager_dict["memories"]["long_term"]), 1)
        self.assertEqual(manager_dict["memories"]["long_term"][0]["content"], "Serialization test")

        # Convert to JSON
        json_str = self.manager.to_json()
        self.assertIsInstance(json_str, str)

        # Verify the JSON can be parsed
        parsed = json.loads(json_str)
        self.assertEqual(parsed["session_id"], "test_session")

    def test_from_dict_and_deserialize(self):
        """Test the from_dict and deserialize methods."""
        # Create test data
        data = {
            "session_id": "serialized_session",
            "memories": {
                "short_term": [],
                "working": [],
                "long_term": [
                    {
                        "content": "Deserialized memory",
                        "memory_type": "long_term",
                        "importance": 0.6,
                        "metadata": {"source": "test"},
                        "created_at": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat(),
                        "access_count": 2,
                    }
                ],
            },
        }

        # Create from dict
        manager = MemoryManager.from_dict(data)
        self.assertEqual(manager.session_id, "serialized_session")
        self.assertEqual(len(manager.memories[MemoryType.LONG_TERM]), 1)
        self.assertEqual(manager.memories[MemoryType.LONG_TERM][0].content, "Deserialized memory")

        # Test deserialize
        json_str = json.dumps(data)
        manager = MemoryManager.deserialize(json_str)
        self.assertEqual(manager.session_id, "serialized_session")
        self.assertEqual(manager.memories[MemoryType.LONG_TERM][0].content, "Deserialized memory")


class TestMemoryManagerSingleton(unittest.TestCase):
    """Test the get_memory_manager function."""

    def setUp(self):
        """Set up the test case."""
        # Clear the singleton dictionary
        with patch("code_agent.adk.memory._memory_managers", {}):
            pass

    def test_get_memory_manager(self):
        """Test the get_memory_manager function."""
        # Get a manager
        with patch("code_agent.adk.memory._memory_managers", {}):
            manager1 = get_memory_manager("test_session")
            self.assertEqual(manager1.session_id, "test_session")

            # Get the same manager again
            manager2 = get_memory_manager("test_session")
            self.assertIs(manager1, manager2)

            # Get a different manager
            manager3 = get_memory_manager("another_session")
            self.assertIsNot(manager1, manager3)
            self.assertEqual(manager3.session_id, "another_session")


class TestBaseMemoryService(unittest.TestCase):
    """Test the BaseMemoryService class."""

    def test_base_methods(self):
        """Test that base methods raise NotImplementedError."""
        service = BaseMemoryService()

        with self.assertRaises(NotImplementedError):
            service.add("session_id", "content")

        with self.assertRaises(NotImplementedError):
            service.search("session_id", "query")


if __name__ == "__main__":
    unittest.main()
