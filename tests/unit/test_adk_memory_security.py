import time
from unittest.mock import MagicMock, patch

import pytest
from google.adk.events.event import Event
from google.genai import types as genai_types

from code_agent.adk.memory import MemoryEntry, MemoryManager, MemoryType, get_memory_manager
from code_agent.adk.services import CodeAgentADKSessionManager, SessionAccessError, SessionSecurityManager
from code_agent.adk.session_config import CodeAgentSessionConfig, SessionSecurityConfig, SessionTokenManager

# --- Memory Tests ---


class TestMemoryTypes:
    """Test the memory type enumeration."""

    def test_memory_type_values(self):
        """Test that memory types have expected values."""
        assert MemoryType.SHORT_TERM.value == "short_term"
        assert MemoryType.LONG_TERM.value == "long_term"
        assert MemoryType.SEMANTIC.value == "semantic"
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.WORKING.value == "working"


class TestMemoryEntry:
    """Test the memory entry class."""

    def test_memory_entry_creation(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(content="Test memory", memory_type=MemoryType.SHORT_TERM, importance=1.5, metadata={"source": "user", "context": "test"})

        assert entry.content == "Test memory"
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert entry.importance == 1.5
        assert entry.metadata == {"source": "user", "context": "test"}

    def test_memory_entry_defaults(self):
        """Test memory entry default values."""
        entry = MemoryEntry(content="Test memory", memory_type=MemoryType.SHORT_TERM)

        assert entry.importance == 1.0
        assert entry.timestamp is None
        assert isinstance(entry.metadata, dict)
        assert len(entry.metadata) == 0


class TestMemoryManager:
    """Test the memory manager class."""

    def test_memory_manager_creation(self):
        """Test creating a memory manager."""
        manager = MemoryManager("test_session_id")

        assert manager.session_id == "test_session_id"
        assert isinstance(manager._memories, dict)
        assert len(manager._memories) == len(MemoryType)

        # Check that all memory types are initialized with empty lists
        for memory_type in MemoryType:
            assert memory_type in manager._memories
            assert isinstance(manager._memories[memory_type], list)
            assert len(manager._memories[memory_type]) == 0

    def test_add_memory(self):
        """Test adding memories to the manager."""
        manager = MemoryManager("test_session_id")

        # Add memories of different types
        manager.add_memory(content="Short-term memory", memory_type=MemoryType.SHORT_TERM, importance=1.0)

        manager.add_memory(content="Long-term memory", memory_type=MemoryType.LONG_TERM, importance=2.0, metadata={"persistent": True})

        # Check that memories were added correctly
        short_term_memories = manager.get_memories(MemoryType.SHORT_TERM)
        assert len(short_term_memories) == 1
        assert short_term_memories[0].content == "Short-term memory"
        assert short_term_memories[0].importance == 1.0

        long_term_memories = manager.get_memories(MemoryType.LONG_TERM)
        assert len(long_term_memories) == 1
        assert long_term_memories[0].content == "Long-term memory"
        assert long_term_memories[0].importance == 2.0
        assert long_term_memories[0].metadata == {"persistent": True}

    def test_get_memories_by_type(self):
        """Test retrieving memories by type."""
        manager = MemoryManager("test_session_id")

        # Add memories of different types
        manager.add_memory(content="Memory 1", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Memory 2", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Memory 3", memory_type=MemoryType.LONG_TERM)

        # Get memories by type
        short_term = manager.get_memories(MemoryType.SHORT_TERM)
        long_term = manager.get_memories(MemoryType.LONG_TERM)
        working = manager.get_memories(MemoryType.WORKING)

        assert len(short_term) == 2
        assert len(long_term) == 1
        assert len(working) == 0

    def test_get_memories_by_importance(self):
        """Test retrieving memories by importance threshold."""
        manager = MemoryManager("test_session_id")

        # Add memories with different importance
        manager.add_memory(content="Low importance", memory_type=MemoryType.SHORT_TERM, importance=0.5)
        manager.add_memory(content="Medium importance", memory_type=MemoryType.SHORT_TERM, importance=1.0)
        manager.add_memory(content="High importance", memory_type=MemoryType.SHORT_TERM, importance=1.5)

        # Get memories by importance threshold
        low_threshold = manager.get_memories(MemoryType.SHORT_TERM, min_importance=0.0)
        medium_threshold = manager.get_memories(MemoryType.SHORT_TERM, min_importance=1.0)
        high_threshold = manager.get_memories(MemoryType.SHORT_TERM, min_importance=1.5)
        very_high_threshold = manager.get_memories(MemoryType.SHORT_TERM, min_importance=2.0)

        assert len(low_threshold) == 3
        assert len(medium_threshold) == 2
        assert len(high_threshold) == 1
        assert len(very_high_threshold) == 0

    def test_get_all_memories(self):
        """Test retrieving all memories across types."""
        manager = MemoryManager("test_session_id")

        # Add memories of different types
        manager.add_memory(content="Short-term 1", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Short-term 2", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Long-term", memory_type=MemoryType.LONG_TERM)
        manager.add_memory(content="Working", memory_type=MemoryType.WORKING)

        # Get all memories
        all_memories = manager.get_memories()

        assert len(all_memories) == 4

        # Check content is all present
        contents = [m.content for m in all_memories]
        assert "Short-term 1" in contents
        assert "Short-term 2" in contents
        assert "Long-term" in contents
        assert "Working" in contents

    def test_clear_memories_by_type(self):
        """Test clearing memories by type."""
        manager = MemoryManager("test_session_id")

        # Add memories of different types
        manager.add_memory(content="Short-term", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Long-term", memory_type=MemoryType.LONG_TERM)

        # Clear short-term memories
        manager.clear_memories(MemoryType.SHORT_TERM)

        # Check that only short-term memories were cleared
        assert len(manager.get_memories(MemoryType.SHORT_TERM)) == 0
        assert len(manager.get_memories(MemoryType.LONG_TERM)) == 1

    def test_clear_all_memories(self):
        """Test clearing all memories."""
        manager = MemoryManager("test_session_id")

        # Add memories of different types
        manager.add_memory(content="Short-term", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Long-term", memory_type=MemoryType.LONG_TERM)
        manager.add_memory(content="Working", memory_type=MemoryType.WORKING)

        # Clear all memories
        manager.clear_memories()

        # Check that all memories were cleared
        for memory_type in MemoryType:
            assert len(manager.get_memories(memory_type)) == 0

    def test_serialize_deserialize(self):
        """Test serializing and deserializing memory manager state."""
        manager = MemoryManager("test_session_id")

        # Add some memories
        manager.add_memory(content="Memory 1", memory_type=MemoryType.SHORT_TERM)
        manager.add_memory(content="Memory 2", memory_type=MemoryType.LONG_TERM, importance=1.5)

        # Serialize
        serialized = manager.serialize()

        # Deserialize to a new manager
        new_manager = MemoryManager.deserialize(serialized)

        # Check that the new manager has the same memories
        assert new_manager.session_id == "test_session_id"
        assert len(new_manager.get_memories(MemoryType.SHORT_TERM)) == 1
        assert len(new_manager.get_memories(MemoryType.LONG_TERM)) == 1
        assert new_manager.get_memories(MemoryType.SHORT_TERM)[0].content == "Memory 1"
        assert new_manager.get_memories(MemoryType.LONG_TERM)[0].content == "Memory 2"
        assert new_manager.get_memories(MemoryType.LONG_TERM)[0].importance == 1.5

    @patch("code_agent.adk.memory.Session")
    def test_extract_memories_from_session(self, mock_session):
        """Test extracting memories from session events."""
        # Create a mock session with events
        mock_session.events = [
            # User message
            Event(author="user", content=genai_types.Content(parts=[genai_types.Part(text="User query")])),
            # Assistant message
            Event(author="assistant", content=genai_types.Content(parts=[genai_types.Part(text="Assistant response")])),
            # Assistant message with function call
            Event(
                author="assistant",
                content=genai_types.Content(parts=[genai_types.Part(function_call=genai_types.FunctionCall(name="test_function", args={"arg1": "value1"}))]),
            ),
            # Function response
            Event(
                author="system",
                content=genai_types.Content(
                    parts=[genai_types.Part(function_response=genai_types.FunctionResponse(name="test_function", response={"result": "function result"}))]
                ),
            ),
        ]

        manager = MemoryManager("test_session_id")
        memories = manager.extract_memories_from_session(mock_session)

        # Check that memories were extracted
        assert len(memories) == 4  # One for each event part that generates a memory

        # Check that the manager's internal memory was updated
        assert len(manager.get_memories(MemoryType.SHORT_TERM)) == 2  # User query and assistant response
        assert len(manager.get_memories(MemoryType.WORKING)) == 2  # Function call and function response


class TestMemoryManagerFactory:
    """Test the memory manager factory function."""

    def test_get_memory_manager(self):
        """Test getting a memory manager instance."""
        # Get a manager for a session
        manager1 = get_memory_manager("session1")
        assert manager1.session_id == "session1"

        # Get the same manager again
        manager2 = get_memory_manager("session1")
        assert manager2 is manager1  # Should be the same instance

        # Get a manager for a different session
        manager3 = get_memory_manager("session2")
        assert manager3.session_id == "session2"
        assert manager3 is not manager1  # Should be a different instance


# --- Security Tests ---


class TestSessionTokenManager:
    """Test the session token manager class."""

    def test_token_generation(self):
        """Test generating authentication tokens."""
        manager = SessionTokenManager()

        # Generate tokens for different sessions
        token1 = manager.generate_token("session1", "user1")
        token2 = manager.generate_token("session2", "user1")
        token3 = manager.generate_token("session3", "user2")

        # Check that tokens are different
        assert token1 != token2
        assert token1 != token3
        assert token2 != token3

        # Check that tokens are strings
        assert isinstance(token1, str)
        assert len(token1) > 0

    def test_token_validation(self):
        """Test validating authentication tokens."""
        manager = SessionTokenManager()

        # Generate a token
        token = manager.generate_token("session1", "user1")

        # Valid token
        assert manager.validate_token("session1", token) == True

        # Invalid token
        assert manager.validate_token("session1", "invalid_token") == False

        # Invalid session
        assert manager.validate_token("invalid_session", token) == False

    def test_get_user_id(self):
        """Test getting the user ID associated with a session."""
        manager = SessionTokenManager()

        # Register sessions for different users
        manager.generate_token("session1", "user1")
        manager.generate_token("session2", "user2")

        # Check user IDs
        assert manager.get_user_id("session1") == "user1"
        assert manager.get_user_id("session2") == "user2"
        assert manager.get_user_id("invalid_session") is None

    def test_revoke_token(self):
        """Test revoking authentication tokens."""
        manager = SessionTokenManager()

        # Generate a token
        token = manager.generate_token("session1", "user1")

        # Revoke the token
        manager.revoke_token("session1")

        # Token should no longer be valid
        assert manager.validate_token("session1", token) == False

        # User ID should no longer be available
        assert manager.get_user_id("session1") is None


class TestSessionSecurityManager:
    """Test the session security manager class."""

    def test_register_session(self):
        """Test registering sessions with users."""
        config = CodeAgentSessionConfig(security=SessionSecurityConfig(max_sessions_per_user=2))
        manager = SessionSecurityManager(config)

        # Register sessions
        token1 = manager.register_session("session1", "user1")
        token2 = manager.register_session("session2", "user1")

        # Check that tokens were generated
        assert isinstance(token1, str)
        assert isinstance(token2, str)

        # Check sessions per user limit
        with pytest.raises(ValueError):
            manager.register_session("session3", "user1")  # Exceeds limit

    def test_verify_session_access(self):
        """Test verifying session access."""
        config = CodeAgentSessionConfig(security=SessionSecurityConfig(enable_authentication=True))
        manager = SessionSecurityManager(config)

        # Register a session
        token = manager.register_session("session1", "user1")

        # Valid access
        assert manager.verify_session_access("session1", token) == True

        # Invalid token
        assert manager.verify_session_access("session1", "invalid_token") == False

        # No token
        assert manager.verify_session_access("session1", None) == False

        # Disable authentication
        manager.config.security.enable_authentication = False
        assert manager.verify_session_access("session1", None) == True

    def test_revoke_session_access(self):
        """Test revoking session access."""
        manager = SessionSecurityManager(CodeAgentSessionConfig())

        # Register a session
        token = manager.register_session("session1", "user1")

        # Revoke access
        manager.revoke_session_access("session1")

        # Session should no longer be accessible
        assert manager.verify_session_access("session1", token) == False

    def test_is_session_expired(self):
        """Test checking session expiration."""
        config = CodeAgentSessionConfig(
            security=SessionSecurityConfig(session_timeout_seconds=1)  # 1 second timeout
        )
        manager = SessionSecurityManager(config)

        # Register a session
        manager.register_session("session1", "user1")

        # Session should not be expired initially
        assert manager.is_session_expired("session1") == False

        # Wait for session to expire
        time.sleep(1.1)

        # Session should now be expired
        assert manager.is_session_expired("session1") == True

    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        config = CodeAgentSessionConfig(
            security=SessionSecurityConfig(session_timeout_seconds=1)  # 1 second timeout
        )
        manager = SessionSecurityManager(config)

        # Register sessions
        token1 = manager.register_session("session1", "user1")
        token2 = manager.register_session("session2", "user2")

        # Wait for sessions to expire
        time.sleep(1.1)

        # Clean up expired sessions
        manager._cleanup_expired_sessions()

        # Sessions should no longer be accessible
        assert manager.verify_session_access("session1", token1) == False
        assert manager.verify_session_access("session2", token2) == False


@pytest.mark.asyncio
class TestCodeAgentADKSessionManager:
    """Test the session manager class with integrated security and memory."""

    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_create_session(self, mock_service_class):
        """Test creating a session with security and memory."""
        # Setup mocks
        mock_service = mock_service_class.return_value
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        mock_service.create_session.return_value = mock_session

        # Create session manager
        config = CodeAgentSessionConfig()
        manager = CodeAgentADKSessionManager(mock_service, config)

        # Create a session
        session_id, auth_token = manager.create_session("test_user")

        # Check that session was created
        assert session_id == "test_session_id"
        assert isinstance(auth_token, str)
        assert len(auth_token) > 0

        # Check that memory manager was initialized
        assert session_id in manager._memory_managers

    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_get_session_with_authentication(self, mock_service_class):
        """Test retrieving a session with authentication."""
        # Setup mocks
        mock_service = mock_service_class.return_value
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        # Create session manager with authentication enabled
        config = CodeAgentSessionConfig(security=SessionSecurityConfig(enable_authentication=True))
        manager = CodeAgentADKSessionManager(mock_service, config)

        # Create a session
        session_id, auth_token = manager.create_session("test_user")

        # Get session with valid token
        session = await manager.get_session(session_id, auth_token)
        assert session is mock_session

        # Get session with invalid token
        with pytest.raises(SessionAccessError):
            await manager.get_session(session_id, "invalid_token")

        # Get session with no token
        with pytest.raises(SessionAccessError):
            await manager.get_session(session_id, None)

    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_add_event_with_memory_integration(self, mock_service_class):
        """Test adding events with integrated memory management."""
        # Setup mocks
        mock_service = mock_service_class.return_value
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        # Create session manager
        config = CodeAgentSessionConfig(
            security=SessionSecurityConfig(enable_authentication=False)  # Disable auth for simplicity
        )
        manager = CodeAgentADKSessionManager(mock_service, config)

        # Create a session
        session_id, _ = manager.create_session("test_user")

        # Add a user message
        await manager.add_user_message(session_id, "User query")

        # Check that memory was created
        memory_manager = manager._get_memory_manager(session_id)
        memories = memory_manager.get_memories(MemoryType.SHORT_TERM)
        assert len(memories) == 1
        assert memories[0].content == "User query"
        assert memories[0].metadata.get("author") == "user"

    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_close_session(self, mock_service_class):
        """Test closing a session and cleaning up resources."""
        # Setup mocks
        mock_service = mock_service_class.return_value
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        mock_service.create_session.return_value = mock_session

        # Create session manager
        config = CodeAgentSessionConfig(security=SessionSecurityConfig(enable_authentication=True))
        manager = CodeAgentADKSessionManager(mock_service, config)

        # Create a session
        session_id, auth_token = manager.create_session("test_user")

        # Close the session
        await manager.close_session(session_id, auth_token)

        # Check that memory manager was cleaned up
        assert session_id not in manager._memory_managers

        # Check that security access was revoked
        with pytest.raises(SessionAccessError):
            await manager.get_session(session_id, auth_token)

    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_memory_retrieval_methods(self, mock_service_class):
        """Test retrieving memories through the session manager."""
        # Setup mocks
        mock_service = mock_service_class.return_value
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        mock_service.create_session.return_value = mock_session
        mock_service.get_session.return_value = mock_session

        # Create session manager
        config = CodeAgentSessionConfig(
            security=SessionSecurityConfig(enable_authentication=False)  # Disable auth for simplicity
        )
        manager = CodeAgentADKSessionManager(mock_service, config)

        # Create a session
        session_id, _ = manager.create_session("test_user")

        # Add messages
        await manager.add_user_message(session_id, "User query")
        await manager.add_assistant_message(session_id, "Assistant response")

        # Get memories
        memories = await manager.get_memories(session_id)

        # Check that memories were retrieved
        assert len(memories) == 2
        assert any(m["content"] == "User query" for m in memories)
        assert any(m["content"] == "Assistant response" for m in memories)

        # Get specific memory type
        user_memories = await manager.get_memories(
            session_id,
            memory_type=MemoryType.SHORT_TERM,
            min_importance=1.0,  # User queries have importance 1.0
        )
        assert len(user_memories) == 1
        assert user_memories[0]["content"] == "User query"
