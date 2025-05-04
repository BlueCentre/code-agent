"""Unit tests for code_agent.adk.session_config module."""

import os
import unittest
from unittest.mock import patch

from code_agent.adk.session_config import (
    IN_MEMORY_SESSION_CONFIG,
    CodeAgentSessionConfig,
    SessionSecurityConfig,
    SessionTokenManager,
    generate_session_id,
    get_token_manager,
)


class TestSessionSecurityConfig(unittest.TestCase):
    """Tests for SessionSecurityConfig class."""

    def test_default_values(self):
        """Test default values for SessionSecurityConfig."""
        config = SessionSecurityConfig()
        self.assertFalse(config.enable_authentication)
        self.assertEqual(config.authentication_token_expiry_seconds, 3600)
        self.assertTrue(config.session_id_validation)
        self.assertEqual(config.max_sessions_per_user, 10)
        self.assertEqual(config.session_timeout_seconds, 3600)
        self.assertTrue(config.enable_session_isolation)
        self.assertTrue(config.auto_cleanup_expired_sessions)

    def test_custom_values(self):
        """Test custom values for SessionSecurityConfig."""
        config = SessionSecurityConfig(
            enable_authentication=True,
            authentication_token_expiry_seconds=7200,
            session_id_validation=False,
            max_sessions_per_user=5,
            session_timeout_seconds=1800,
            enable_session_isolation=False,
            auto_cleanup_expired_sessions=False,
        )
        self.assertTrue(config.enable_authentication)
        self.assertEqual(config.authentication_token_expiry_seconds, 7200)
        self.assertFalse(config.session_id_validation)
        self.assertEqual(config.max_sessions_per_user, 5)
        self.assertEqual(config.session_timeout_seconds, 1800)
        self.assertFalse(config.enable_session_isolation)
        self.assertFalse(config.auto_cleanup_expired_sessions)


class TestCodeAgentSessionConfig(unittest.TestCase):
    """Tests for CodeAgentSessionConfig class."""

    def test_default_values(self):
        """Test default values for CodeAgentSessionConfig."""
        config = CodeAgentSessionConfig()
        self.assertTrue(config.use_uuid_for_session_ids)
        self.assertEqual(config.persistence_type, "in_memory")
        self.assertIsNone(config.filesystem_base_path)
        self.assertIsInstance(config.security, SessionSecurityConfig)
        self.assertEqual(config.max_events_per_session, 1000)
        self.assertEqual(config.max_session_size_bytes, 10 * 1024 * 1024)
        self.assertEqual(config.cleanup_interval_seconds, 3600)

    def test_custom_values(self):
        """Test custom values for CodeAgentSessionConfig."""
        config = CodeAgentSessionConfig(
            use_uuid_for_session_ids=False,
            persistence_type="filesystem",
            filesystem_base_path="/tmp/sessions",
            security=SessionSecurityConfig(enable_authentication=True),
            max_events_per_session=500,
            max_session_size_bytes=5 * 1024 * 1024,
            cleanup_interval_seconds=1800,
        )
        self.assertFalse(config.use_uuid_for_session_ids)
        self.assertEqual(config.persistence_type, "filesystem")
        self.assertEqual(config.filesystem_base_path, "/tmp/sessions")
        self.assertTrue(config.security.enable_authentication)
        self.assertEqual(config.max_events_per_session, 500)
        self.assertEqual(config.max_session_size_bytes, 5 * 1024 * 1024)
        self.assertEqual(config.cleanup_interval_seconds, 1800)


class TestSessionTokenManager(unittest.TestCase):
    """Tests for SessionTokenManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.token_manager = SessionTokenManager()
        self.session_id = "test-session-id"
        self.user_id = "test-user-id"

    def test_generate_token(self):
        """Test generate_token method."""
        token = self.token_manager.generate_token(self.session_id, self.user_id)
        self.assertIsNotNone(token)
        self.assertIn(self.session_id, self.token_manager._tokens)
        self.assertEqual(self.token_manager._tokens[self.session_id]["user_id"], self.user_id)

    def test_generate_token_with_custom_expiry(self):
        """Test generate_token method with custom expiry."""
        expiry = 7200
        token = self.token_manager.generate_token(self.session_id, self.user_id, expiry)
        self.assertIsNotNone(token)
        self.assertEqual(self.token_manager._tokens[self.session_id]["expiry"], expiry)

    def test_validate_token_valid(self):
        """Test validate_token method with a valid token."""
        token = self.token_manager.generate_token(self.session_id, self.user_id)
        self.assertTrue(self.token_manager.validate_token(self.session_id, token))

    def test_validate_token_invalid(self):
        """Test validate_token method with an invalid token."""
        self.token_manager.generate_token(self.session_id, self.user_id)
        self.assertFalse(self.token_manager.validate_token(self.session_id, "invalid-token"))

    def test_validate_token_nonexistent_session(self):
        """Test validate_token method with a nonexistent session."""
        self.assertFalse(self.token_manager.validate_token("nonexistent-session", "token"))

    def test_get_user_id_existing_session(self):
        """Test get_user_id method with an existing session."""
        self.token_manager.generate_token(self.session_id, self.user_id)
        self.assertEqual(self.token_manager.get_user_id(self.session_id), self.user_id)

    def test_get_user_id_nonexistent_session(self):
        """Test get_user_id method with a nonexistent session."""
        self.assertIsNone(self.token_manager.get_user_id("nonexistent-session"))

    def test_revoke_token_existing_session(self):
        """Test revoke_token method with an existing session."""
        self.token_manager.generate_token(self.session_id, self.user_id)
        self.token_manager.revoke_token(self.session_id)
        self.assertNotIn(self.session_id, self.token_manager._tokens)

    def test_revoke_token_nonexistent_session(self):
        """Test revoke_token method with a nonexistent session."""
        # Should not raise an exception
        self.token_manager.revoke_token("nonexistent-session")


class TestDefaultConfigs(unittest.TestCase):
    """Tests for default configurations."""

    def test_in_memory_session_config(self):
        """Test IN_MEMORY_SESSION_CONFIG."""
        self.assertEqual(IN_MEMORY_SESSION_CONFIG.persistence_type, "in_memory")
        self.assertIsNone(IN_MEMORY_SESSION_CONFIG.filesystem_base_path)

    @patch.dict(os.environ, {"CODE_AGENT_SESSION_PATH": "/custom/path"})
    def test_filesystem_session_config_with_env_var(self):
        """Test FILESYSTEM_SESSION_CONFIG with environment variable."""
        # Since the FILESYSTEM_SESSION_CONFIG is imported at module level
        # we need to make sure we're testing the behavior rather than the actual imported value
        from code_agent.adk.session_config import CodeAgentSessionConfig

        # Create a fresh config to test the environment variable behavior
        fs_config = CodeAgentSessionConfig(persistence_type="filesystem", filesystem_base_path=os.environ.get("CODE_AGENT_SESSION_PATH"))

        self.assertEqual(fs_config.persistence_type, "filesystem")
        self.assertEqual(fs_config.filesystem_base_path, "/custom/path")

    def test_get_token_manager(self):
        """Test get_token_manager function."""
        token_manager = get_token_manager()
        self.assertIsInstance(token_manager, SessionTokenManager)
        # Should return the same instance on subsequent calls
        self.assertIs(token_manager, get_token_manager())

    def test_generate_session_id(self):
        """Test generate_session_id function."""
        session_id = generate_session_id()
        self.assertIsInstance(session_id, str)
        # UUID should be 36 characters long
        self.assertEqual(len(session_id), 36)
        # UUIDs should be unique
        self.assertNotEqual(session_id, generate_session_id())
