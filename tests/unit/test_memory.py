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


# Patch the MemoryManager class used internally by InMemoryMemoryService
@patch("code_agent.adk.memory.MemoryManager")
class TestInMemoryMemoryService(unittest.TestCase):
    """Test cases for the InMemoryMemoryService."""

    def test_search_empty_memory(self, MockMemoryManager):
        """Test search when the memory manager finds nothing."""
        # Arrange
        memory_service = InMemoryMemoryService()
        session_id = "test_session_search_empty"
        query = "empty_query"

        # Create a mock manager instance *specifically for this session*
        mock_manager_instance = MagicMock(spec=MemoryManager)
        mock_manager_instance.search_memories.return_value = SearchMemoryResponse(results=[])
        # Manually insert the mock manager into the service's dictionary
        memory_service._managers[session_id] = mock_manager_instance

        # Act
        response = memory_service.search(session_id, query)

        # Assert
        # Check that the manually inserted mock manager instance was used
        mock_manager_instance.search_memories.assert_called_once_with(query, limit=5)
        assert isinstance(response, SearchMemoryResponse)
        assert len(response.results) == 0

    def test_add(self, MockMemoryManager):
        """Test adding content to memory."""
        # Arrange
        # Configure the mock class to return our instance when called
        mock_manager_instance = MagicMock(spec=MemoryManager)
        MockMemoryManager.return_value = mock_manager_instance

        memory_service = InMemoryMemoryService()
        session_id = "test_session_add"
        content = "This is some content to add."
        metadata = {"key": "value"}

        # Act
        # This call will create the manager instance using the patched class
        memory_service.add(session_id, content, metadata)

        # Assert
        # Check that the class was instantiated
        MockMemoryManager.assert_called_once_with(session_id)
        # Check that the mock instance's method was called
        mock_manager_instance.add_memory.assert_called_once_with(content, MemoryType.LONG_TERM, metadata=metadata)

    def test_search_memory_found(self, MockMemoryManager):
        """Test searching memory finds relevant information."""
        # Arrange
        memory_service = InMemoryMemoryService()
        session_id = "test_session_search_found"
        query = "python"
        limit = 2

        # Create and configure a mock manager instance for this session
        mock_manager_instance = MagicMock(spec=MemoryManager)
        mock_results = [
            MemoryResult(content="Found Python related stuff.", score=0.9, metadata={}),
            MemoryResult(content="Something else about Python.", score=0.8, metadata={}),
        ]
        mock_manager_instance.search_memories.return_value = SearchMemoryResponse(results=mock_results)
        # Manually insert the mock manager
        memory_service._managers[session_id] = mock_manager_instance

        # Act
        response = memory_service.search(session_id, query, limit=limit)

        # Assert
        # Check that the manually inserted mock instance's method was called
        mock_manager_instance.search_memories.assert_called_once_with(query, limit=limit)
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
