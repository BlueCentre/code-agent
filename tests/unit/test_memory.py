import unittest
from unittest.mock import MagicMock, patch

# Remove Session and Event imports as they are not directly used by the service methods
# from google.adk.events.event import Event
# from google.adk.sessions import Session
from code_agent.adk.memory import (
    InMemoryMemoryService,
    MemoryManager,  # Import for mocking spec
    MemoryResult,
    MemoryType,  # Import for assertions
    SearchMemoryResponse,  # Import for patching target
)


@patch("code_agent.adk.memory.get_memory_manager")
class TestInMemoryMemoryService(unittest.TestCase):
    """Test cases for the InMemoryMemoryService."""

    def setUp(self):
        # No need to instantiate the service in setUp if it's stateless
        # and we are mocking its dependency anyway.
        pass

    def test_search_empty_memory(self, mock_get_memory_manager):
        """Test search when the memory manager finds nothing."""
        # Arrange
        mock_manager = MagicMock(spec=MemoryManager)
        mock_get_memory_manager.return_value = mock_manager
        # Simulate MemoryManager returning a proper SearchMemoryResponse with empty results
        mock_manager.search_memories.return_value = SearchMemoryResponse(results=[])

        memory_service = InMemoryMemoryService()
        session_id = "test_session_search_empty"
        query = "empty_query"

        # Act
        response = memory_service.search(session_id, query)

        # Assert
        mock_get_memory_manager.assert_called_once_with(session_id)
        mock_manager.search_memories.assert_called_once_with(query, MemoryType.LONG_TERM, limit=5)
        assert isinstance(response, SearchMemoryResponse)
        assert len(response.results) == 0

    def test_add(self, mock_get_memory_manager):
        """Test adding content to memory."""
        # Arrange
        mock_manager = MagicMock(spec=MemoryManager)
        mock_get_memory_manager.return_value = mock_manager

        memory_service = InMemoryMemoryService()
        session_id = "test_session_add"
        content = "This is some content to add."
        metadata = {"key": "value"}

        # Act
        memory_service.add(session_id, content, metadata)

        # Assert
        mock_get_memory_manager.assert_called_once_with(session_id)
        mock_manager.add_memory.assert_called_once_with(content, MemoryType.LONG_TERM, 1.0, metadata)

    def test_search_memory_found(self, mock_get_memory_manager):
        """Test searching memory finds relevant information."""
        # Arrange
        mock_manager = MagicMock(spec=MemoryManager)
        mock_get_memory_manager.return_value = mock_manager

        # Simulate results found by MemoryManager
        mock_results = [
            MemoryResult(content="Found Python related stuff.", score=0.9, metadata={}),
            MemoryResult(content="Something else about Python.", score=0.8, metadata={}),
        ]
        mock_manager.search_memories.return_value = SearchMemoryResponse(results=mock_results)

        memory_service = InMemoryMemoryService()
        session_id = "test_session_search_found"
        query = "python"
        limit = 2  # Example limit

        # Act
        response = memory_service.search(session_id, query, limit=limit)

        # Assert
        mock_get_memory_manager.assert_called_once_with(session_id)
        mock_manager.search_memories.assert_called_once_with(query, MemoryType.LONG_TERM, limit=limit)
        self.assertIsInstance(response, SearchMemoryResponse)
        self.assertEqual(len(response.results), 2)
        self.assertEqual(response.results[0].content, "Found Python related stuff.")
        self.assertEqual(response.results[0].score, 0.9)
        self.assertEqual(response.results[1].content, "Something else about Python.")
        self.assertEqual(response.results[1].score, 0.8)


# Remove old tests based on non-existent methods and direct _memories access
# class TestInMemoryMemoryService(unittest.TestCase):
# ... (old test_add_session_to_memory and test_search_memory removed)

if __name__ == "__main__":
    unittest.main()
