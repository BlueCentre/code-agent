"""
Unit tests for memory service functionality in code_agent.adk.services.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from code_agent.adk.memory import BaseMemoryService, InMemoryMemoryService, MemoryType
from code_agent.adk.services import get_memory_service


class TestMemoryService(unittest.TestCase):
    """Tests for the memory service in services.py."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing memory service
        with patch("code_agent.adk.services._memory_service", None):
            pass

    def test_get_memory_service(self):
        """Test that get_memory_service returns the expected service type."""
        # Clear any existing memory service
        with patch("code_agent.adk.services._memory_service", None):
            # Get the memory service
            service = get_memory_service()

            # Verify it's the expected type
            self.assertIsInstance(service, InMemoryMemoryService)
            self.assertIsInstance(service, BaseMemoryService)

    def test_get_memory_service_singleton(self):
        """Test that get_memory_service returns the same instance on subsequent calls."""
        # Clear any existing memory service
        with patch("code_agent.adk.services._memory_service", None):
            # Get the memory service twice
            service1 = get_memory_service()
            service2 = get_memory_service()

            # Verify they're the same instance
            self.assertIs(service1, service2)

    def test_get_memory_service_force_refresh(self):
        """Test that get_memory_service creates a new instance when force_refresh is True."""
        # Clear any existing memory service
        with patch("code_agent.adk.services._memory_service", None):
            # Get the memory service
            service1 = get_memory_service()

            # Get it again with force_refresh=True
            service2 = get_memory_service(force_refresh=True)

            # Verify they're different instances
            self.assertIsNot(service1, service2)


@pytest.mark.asyncio
class TestADKSessionManager:
    """Tests for CodeAgentADKSessionManager methods related to memory."""

    @pytest.fixture
    def session_manager(self):
        """Fixture for CodeAgentADKSessionManager."""
        from code_agent.adk.services import CodeAgentADKSessionManager

        # Create a session manager with mocked service
        mock_service = MagicMock()
        manager = CodeAgentADKSessionManager(mock_service)

        return manager

    @patch("code_agent.adk.services.get_memory_manager")
    async def test_get_memory_manager(self, mock_get_memory_manager, session_manager):
        """Test the _get_memory_manager method."""
        # Setup mock
        mock_memory_manager = MagicMock()
        mock_get_memory_manager.return_value = mock_memory_manager

        # Call the method
        manager = session_manager._get_memory_manager("test_session_id")

        # Verify the result
        assert manager is mock_memory_manager
        mock_get_memory_manager.assert_called_once_with("test_session_id")

    @patch("code_agent.adk.services.CodeAgentADKSessionManager._get_memory_manager")
    async def test_get_conversation_summary(self, mock_get_memory_manager, session_manager):
        """Test the get_conversation_summary method."""
        # Setup mock
        mock_memory_manager = MagicMock()
        mock_get_memory_manager.return_value = mock_memory_manager
        mock_memory_manager.get_conversation_summary.return_value = "Test summary"

        # Call the method
        summary = await session_manager.get_conversation_summary("test_session_id")

        # Verify the result
        assert summary == "Test summary"
        mock_get_memory_manager.assert_called_once_with("test_session_id")
        mock_memory_manager.get_conversation_summary.assert_called_once()

    @patch("code_agent.adk.services.CodeAgentADKSessionManager._get_memory_manager")
    async def test_extract_session_memories(self, mock_get_memory_manager, session_manager):
        """Test the extract_session_memories method."""
        # Setup mock
        mock_memory_manager = MagicMock()
        mock_get_memory_manager.return_value = mock_memory_manager

        # Call the method
        await session_manager.extract_session_memories("test_session_id")

        # Verify the result
        mock_get_memory_manager.assert_called_once_with("test_session_id")
        mock_memory_manager.extract_memories_from_history.assert_called_once()

    @patch("code_agent.adk.services.CodeAgentADKSessionManager._get_memory_manager")
    async def test_get_memories(self, mock_get_memory_manager, session_manager):
        """Test the get_memories method."""
        # Setup mock
        mock_memory_manager = MagicMock()
        mock_get_memory_manager.return_value = mock_memory_manager
        mock_memory_manager.get_memories.return_value = [{"content": "Test memory"}]

        # Call the method with default parameters
        memories = await session_manager.get_memories("test_session_id")

        # Verify the result
        assert memories == [{"content": "Test memory"}]
        mock_get_memory_manager.assert_called_once_with("test_session_id")
        mock_memory_manager.get_memories.assert_called_once()
        args, kwargs = mock_memory_manager.get_memories.call_args
        assert args[0] is None  # memory_type
        assert args[1] == 0.0  # min_importance

        # Reset mocks
        mock_get_memory_manager.reset_mock()
        mock_memory_manager.get_memories.reset_mock()

        # Call the method with custom parameters
        memories = await session_manager.get_memories("test_session_id", MemoryType.LONG_TERM, 0.5)

        # Verify the result
        mock_get_memory_manager.assert_called_once_with("test_session_id")
        # Check the positional arguments
        args, kwargs = mock_memory_manager.get_memories.call_args
        assert args[0] == MemoryType.LONG_TERM
        assert args[1] == 0.5
