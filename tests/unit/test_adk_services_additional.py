"""
Additional unit tests for code_agent.adk.services module to increase coverage.

These tests focus on edge cases and error handling in the services module.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from code_agent.adk.memory import MemoryType
from code_agent.adk.services import (
    CodeAgentADKSessionManager,
    SessionAccessError,
    get_adk_session_service,
    get_memory_service,
    initialize_adk_with_api_key,
)
from code_agent.adk.session_config import CodeAgentSessionConfig, SessionSecurityConfig


class TestInitializeAdkWithApiKey(unittest.TestCase):
    """Test the initialize_adk_with_api_key function."""

    @patch("code_agent.adk.services.genai")
    @patch("code_agent.adk.services.os.environ.get")
    def test_initialize_with_provided_key(self, mock_environ_get, mock_genai):
        """Test initializing with a provided API key."""
        # Call with a provided key
        initialize_adk_with_api_key(api_key="test_key")

        # Verify genai.configure was called with the provided key
        mock_genai.configure.assert_called_once_with(api_key="test_key")

        # Verify os.environ.get was not called
        mock_environ_get.assert_not_called()

    @patch("code_agent.adk.services.genai")
    @patch("code_agent.adk.services.os.environ.get")
    def test_initialize_with_environment_variable_google_api_key(self, mock_environ_get, mock_genai):
        """Test initializing with GOOGLE_API_KEY environment variable."""
        # Set up mock to return API key from GOOGLE_API_KEY
        mock_environ_get.side_effect = lambda key, default=None: "env_key" if key == "GOOGLE_API_KEY" else None

        # Call without a provided key
        initialize_adk_with_api_key()

        # Verify genai.configure was called with the environment key
        mock_genai.configure.assert_called_once_with(api_key="env_key")

        # Verify os.environ.get was called with the right keys
        mock_environ_get.assert_any_call("GOOGLE_API_KEY")

    @patch("code_agent.adk.services.genai")
    @patch("code_agent.adk.services.os.environ.get")
    def test_initialize_with_environment_variable_ai_studio_api_key(self, mock_environ_get, mock_genai):
        """Test initializing with AI_STUDIO_API_KEY environment variable."""
        # Set up mock to return API key from AI_STUDIO_API_KEY but not GOOGLE_API_KEY
        mock_environ_get.side_effect = lambda key, default=None: "ai_studio_key" if key == "AI_STUDIO_API_KEY" else None

        # Call without a provided key
        initialize_adk_with_api_key()

        # Verify genai.configure was called with the environment key
        mock_genai.configure.assert_called_once_with(api_key="ai_studio_key")

        # Verify os.environ.get was called with the right keys
        mock_environ_get.assert_any_call("GOOGLE_API_KEY")
        mock_environ_get.assert_any_call("AI_STUDIO_API_KEY")

    @patch("code_agent.adk.services.genai")
    @patch("code_agent.adk.services.os.environ.get")
    @patch("code_agent.adk.services.verbosity_controller")
    def test_initialize_without_api_key(self, mock_verbosity, mock_environ_get, mock_genai):
        """Test initializing without any API key."""
        # Set up mock to return None for all environment variables
        mock_environ_get.return_value = None

        # Call without a provided key
        initialize_adk_with_api_key()

        # Verify genai.configure was not called
        mock_genai.configure.assert_not_called()

        # Verify warning was shown
        mock_verbosity.show_warning.assert_called_once()


class TestGetAdkSessionService(unittest.TestCase):
    """Test the get_adk_session_service function."""

    @pytest.mark.asyncio
    @patch("code_agent.adk.services.initialize_adk_with_api_key")
    @patch("code_agent.adk.services.InMemorySessionService")
    @patch("code_agent.adk.services._adk_session_service", None)  # Reset singleton
    async def test_get_adk_session_service_creates_new(self, mock_service_class, mock_initialize):
        """Test get_adk_session_service creates a new service when none exists."""
        # Set up mock service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Call the function
        service = await get_adk_session_service()

        # Verify a new service was created
        mock_service_class.assert_called_once()
        self.assertEqual(service, mock_service)

        # Verify API key was initialized
        mock_initialize.assert_called_once()

    @pytest.mark.asyncio
    @patch("code_agent.adk.services.initialize_adk_with_api_key")
    @patch("code_agent.adk.services.InMemorySessionService")
    async def test_get_adk_session_service_returns_existing(self, mock_service_class, mock_initialize):
        """Test get_adk_session_service returns the existing service when one exists."""
        # Set up mock service
        mock_service = MagicMock()

        # Set the global service
        import code_agent.adk.services

        code_agent.adk.services._adk_session_service = mock_service

        # Call the function
        service = await get_adk_session_service()

        # Verify no new service was created
        mock_service_class.assert_not_called()
        self.assertEqual(service, mock_service)

        # Verify API key was initialized
        mock_initialize.assert_called_once()

        # Clean up global state
        code_agent.adk.services._adk_session_service = None


class TestGetMemoryService(unittest.TestCase):
    """Test the get_memory_service function."""

    @patch("code_agent.adk.services.InMemoryMemoryService")
    @patch("code_agent.adk.services._memory_service", None)  # Reset singleton
    def test_get_memory_service_creates_new(self, mock_service_class):
        """Test get_memory_service creates a new service when none exists."""
        # Set up mock service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Call the function
        service = get_memory_service()

        # Verify a new service was created
        mock_service_class.assert_called_once()
        self.assertEqual(service, mock_service)

    @patch("code_agent.adk.services.InMemoryMemoryService")
    def test_get_memory_service_returns_existing(self, mock_service_class):
        """Test get_memory_service returns the existing service when one exists."""
        # Set up mock service
        mock_service = MagicMock()

        # Set the global service
        import code_agent.adk.services

        code_agent.adk.services._memory_service = mock_service

        # Call the function
        service = get_memory_service()

        # Verify no new service was created
        mock_service_class.assert_not_called()
        self.assertEqual(service, mock_service)

        # Clean up global state
        code_agent.adk.services._memory_service = None

    @patch("code_agent.adk.services.InMemoryMemoryService")
    def test_get_memory_service_force_refresh(self, mock_service_class):
        """Test get_memory_service with force_refresh=True creates a new service even when one exists."""
        # Set up mock services for both calls
        mock_service1 = MagicMock()
        mock_service2 = MagicMock()
        mock_service_class.side_effect = [mock_service2]  # Only need to mock the second creation

        # Set the global service
        import code_agent.adk.services

        code_agent.adk.services._memory_service = mock_service1

        # Call the function with force_refresh=True
        service = get_memory_service(force_refresh=True)

        # Verify a new service was created
        mock_service_class.assert_called_once()

        # Verify that the returned service is different from the original one
        self.assertIsNot(service, mock_service1)

        # Clean up global state
        code_agent.adk.services._memory_service = None


class TestCodeAgentADKSessionManager(unittest.TestCase):
    """Test the CodeAgentADKSessionManager class."""

    def setUp(self):
        """Set up common test fixtures."""
        self.mock_session_service = MagicMock()
        self.mock_security_manager = MagicMock()

        # Set up a configuration with authentication enabled
        self.test_config = CodeAgentSessionConfig(
            use_uuid_for_session_ids=False,
            security=SessionSecurityConfig(enable_authentication=True, token_validity_seconds=300, session_expiry_seconds=600),
        )

        # Create a manager with mocks injected
        self.manager = CodeAgentADKSessionManager(self.mock_session_service, config=self.test_config)
        self.manager.security_manager = self.mock_security_manager

    def test_create_session_with_default_config(self):
        """Test create_session with default configuration."""
        # Set up mocks
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        self.mock_session_service.create_session.return_value = mock_session
        self.mock_security_manager.register_session.return_value = "test_token"

        # Call the function
        session_id, auth_token = self.manager.create_session()

        # Verify results
        self.assertEqual(session_id, "test_session_id")
        self.assertEqual(auth_token, "test_token")

        # Verify session was created with default user_id
        self.mock_session_service.create_session.assert_called_once()
        created_args = self.mock_session_service.create_session.call_args[1]
        self.assertEqual(created_args["app_name"], "code_agent")
        self.assertEqual(created_args["user_id"], "default_user")

        # Verify security manager was called
        self.mock_security_manager.register_session.assert_called_once_with("test_session_id", "default_user")

    def test_create_session_with_custom_user_id(self):
        """Test create_session with a custom user ID."""
        # Set up mocks
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        self.mock_session_service.create_session.return_value = mock_session
        self.mock_security_manager.register_session.return_value = "test_token"

        # Call the function with a custom user ID
        session_id, auth_token = self.manager.create_session(user_id="custom_user")

        # Verify results
        self.assertEqual(session_id, "test_session_id")
        self.assertEqual(auth_token, "test_token")

        # Verify session was created with the custom user ID
        # Note: We only need to check that user_id is the expected value - don't check session_id
        # as it might be auto-generated and not predictable
        call_args = self.mock_session_service.create_session.call_args[1]
        self.assertEqual(call_args["app_name"], "code_agent")
        self.assertEqual(call_args["user_id"], "custom_user")

        # Verify security manager was called
        self.mock_security_manager.register_session.assert_called_once_with("test_session_id", "custom_user")

    def test_create_session_with_uuid(self):
        """Test create_session with UUID for session IDs enabled."""
        # Set up a configuration with UUIDs enabled
        uuid_config = CodeAgentSessionConfig(
            use_uuid_for_session_ids=True,
            security=SessionSecurityConfig(enable_authentication=True, token_validity_seconds=300, session_expiry_seconds=600),
        )

        # Create a new manager with the UUID config
        uuid_manager = CodeAgentADKSessionManager(self.mock_session_service, config=uuid_config)
        uuid_manager.security_manager = self.mock_security_manager

        # Set up mocks for UUID manager
        mock_session = MagicMock()
        mock_session.id = "test_session_id"
        self.mock_session_service.create_session.return_value = mock_session
        self.mock_security_manager.register_session.return_value = "test_token"

        # Set up patch for generate_session_id
        with patch("code_agent.adk.services.generate_session_id", return_value="generated_uuid"):
            # Call the function
            session_id, auth_token = uuid_manager.create_session()

            # Verify results
            self.assertEqual(session_id, "test_session_id")
            self.assertEqual(auth_token, "test_token")

            # Verify session was created with a UUID
            self.mock_session_service.create_session.assert_called_once()
            created_args = self.mock_session_service.create_session.call_args[1]
            self.assertEqual(created_args["session_id"], "generated_uuid")

    @pytest.mark.asyncio
    async def test_get_session_without_auth(self):
        """Test get_session when authentication is not enabled."""
        # Create a session manager with auth disabled
        no_auth_config = CodeAgentSessionConfig(
            use_uuid_for_session_ids=False,
            security=SessionSecurityConfig(enable_authentication=False, token_validity_seconds=300, session_expiry_seconds=600),
        )
        no_auth_manager = CodeAgentADKSessionManager(self.mock_session_service, config=no_auth_config)
        no_auth_manager.security_manager = self.mock_security_manager

        # Set up mock to return a session
        mock_session = MagicMock()
        self.mock_session_service.get_session.return_value = mock_session

        # Call the function without providing an auth token
        result = await no_auth_manager.get_session("test_session")

        # Verify the session was returned without checking auth
        self.assertEqual(result, mock_session)
        self.mock_session_service.get_session.assert_called_once()
        self.mock_security_manager.verify_session_access.assert_not_called()
        self.mock_security_manager.is_session_expired.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_session_with_auth_enabled(self):
        """Test get_session when authentication is enabled."""
        # Set up mocks to pass auth checks
        mock_session = MagicMock()
        self.mock_session_service.get_session.return_value = mock_session
        self.mock_security_manager.verify_session_access.return_value = True
        self.mock_security_manager.is_session_expired.return_value = False

        # Call the function with an auth token
        result = await self.manager.get_session("test_session", auth_token="test_token")

        # Verify the session was returned after passing auth checks
        self.assertEqual(result, mock_session)
        self.mock_session_service.get_session.assert_called_once()
        self.mock_security_manager.verify_session_access.assert_called_once_with("test_session", "test_token")
        self.mock_security_manager.is_session_expired.assert_called_once_with("test_session")

        # Check that the args to get_session were what we expect
        get_session_args = self.mock_session_service.get_session.call_args[1]
        self.assertEqual(get_session_args["app_name"], "code_agent")
        self.assertEqual(get_session_args["user_id"], "default_user")
        self.assertEqual(get_session_args["session_id"], "test_session")

    @pytest.mark.asyncio
    async def test_get_session_auth_denied(self):
        """Test get_session when authentication is denied."""
        # Set up mock to deny auth
        mock_session = MagicMock()
        self.mock_session_service.get_session.return_value = mock_session
        self.mock_security_manager.verify_session_access.return_value = False

        # Call the function, should raise SessionAccessError
        with self.assertRaises(SessionAccessError):
            await self.manager.get_session("test_session", auth_token="invalid_token")

        # Verify get_session was called to check if session exists
        self.mock_session_service.get_session.assert_called_once()
        # Verify auth was checked
        self.mock_security_manager.verify_session_access.assert_called_once_with("test_session", "invalid_token")
        # Verify expiry was not checked (short-circuited by auth failure)
        self.mock_security_manager.is_session_expired.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """Test get_session when session has expired."""
        # Set up mocks to pass auth but fail expiry check
        mock_session = MagicMock()
        self.mock_session_service.get_session.return_value = mock_session
        self.mock_security_manager.verify_session_access.return_value = True
        self.mock_security_manager.is_session_expired.return_value = True

        # Call the function, should raise SessionAccessError
        with self.assertRaises(SessionAccessError):
            await self.manager.get_session("test_session", auth_token="test_token")

        # Verify get_session was called
        self.mock_session_service.get_session.assert_called_once()
        # Verify auth was checked and passed
        self.mock_security_manager.verify_session_access.assert_called_once_with("test_session", "test_token")
        # Verify expiry was checked and failed
        self.mock_security_manager.is_session_expired.assert_called_once_with("test_session")

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test get_session when session is not found."""
        # Set up mock to return None (session not found)
        self.mock_session_service.get_session.return_value = None

        # Call the function, should raise ValueError
        with self.assertRaises(ValueError):
            await self.manager.get_session("nonexistent_session", auth_token="test_token")

        # Verify get_session was called
        self.mock_session_service.get_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memories(self):
        """Test get_memories retrieves memories from the manager."""
        # Set up mock session and memory manager
        mock_session = MagicMock()
        self.mock_session_service.get_session.return_value = mock_session

        # Mock the memory manager
        mock_memory_manager = MagicMock()
        mock_memories = [
            MagicMock(content="Memory 1", memory_type=MemoryType.SHORT_TERM, importance=0.5, metadata={}),
            MagicMock(content="Memory 2", memory_type=MemoryType.WORKING, importance=0.8, metadata={"key": "value"}),
        ]
        mock_memory_manager.get_memories.return_value = mock_memories

        # Set up the manager's _memory_managers dict
        self.manager._memory_managers = {"test_session": mock_memory_manager}

        # Call the function
        result = await self.manager.get_memories("test_session", MemoryType.SHORT_TERM, min_importance=0.3)

        # Verify memory manager was called correctly
        mock_memory_manager.get_memories.assert_called_once_with(MemoryType.SHORT_TERM, 0.3)

        # Verify result format
        self.assertEqual(len(result), 2)
        # Check that the memories were converted to dictionaries
        self.assertIsInstance(result[0], dict)
        self.assertIsInstance(result[1], dict)

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test close_session removes the memory manager and revokes access."""
        # Set up memory manager for the session
        mock_memory_manager = MagicMock()
        self.manager._memory_managers = {"test_session": mock_memory_manager}

        # Set up auth check to pass
        self.mock_security_manager.verify_session_access.return_value = True

        # Call the function
        await self.manager.close_session("test_session", auth_token="test_token")

        # Verify auth was checked
        self.mock_security_manager.verify_session_access.assert_called_once_with("test_session", "test_token")

        # Verify memory manager was removed
        self.assertNotIn("test_session", self.manager._memory_managers)

        # Verify access was revoked
        self.mock_security_manager.revoke_session_access.assert_called_once_with("test_session")
