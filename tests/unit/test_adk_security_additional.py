"""
Additional unit tests for the code_agent.adk.security module to increase coverage.

These tests focus on edge cases and error handling in the security module.
"""

import unittest
from datetime import datetime, timedelta

from code_agent.adk.security import SessionSecurityManager, SessionToken, SessionTokenManager


class TestSessionTokenAdditional(unittest.TestCase):
    """Additional tests for the SessionToken class."""

    def test_session_token_defaults(self):
        """Test SessionToken default values."""
        now = datetime.utcnow()
        token = SessionToken(
            token="test_token",
            user_id="test_user",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )

        # Check defaults
        self.assertFalse(token.revoked)
        self.assertEqual(token.metadata, {})


class TestSessionTokenManagerAdditional(unittest.TestCase):
    """Additional tests for the SessionTokenManager class."""

    def setUp(self):
        """Set up the test case."""
        self.token_manager = SessionTokenManager(token_validity_seconds=300)  # 5 minutes

    def test_generate_token_with_metadata(self):
        """Test generate_token with metadata."""
        metadata = {"key1": "value1", "key2": "value2"}
        token = self.token_manager.generate_token("test_user", metadata=metadata)

        # Verify token exists and metadata was stored
        self.assertIn(token, self.token_manager.tokens)
        self.assertEqual(self.token_manager.tokens[token].metadata, metadata)

    def test_validate_nonexistent_token(self):
        """Test validate_token with token that doesn't exist."""
        result = self.token_manager.validate_token("nonexistent_token")
        self.assertFalse(result)

    def test_validate_expired_token(self):
        """Test validate_token with expired token."""
        # Generate token
        token = self.token_manager.generate_token("test_user")

        # Manually expire the token
        self.token_manager.tokens[token].expires_at = datetime.utcnow() - timedelta(seconds=1)

        # Validate should return False
        result = self.token_manager.validate_token(token)
        self.assertFalse(result)

    def test_validate_revoked_token(self):
        """Test validate_token with revoked token."""
        # Generate token
        token = self.token_manager.generate_token("test_user")

        # Revoke the token
        self.token_manager.tokens[token].revoked = True

        # Validate should return False
        result = self.token_manager.validate_token(token)
        self.assertFalse(result)

    def test_get_user_id_from_invalid_token(self):
        """Test get_user_id with invalid token."""
        # With nonexistent token
        result = self.token_manager.get_user_id("nonexistent_token")
        self.assertIsNone(result)

        # With revoked token
        token = self.token_manager.generate_token("test_user")
        self.token_manager.tokens[token].revoked = True
        result = self.token_manager.get_user_id(token)
        self.assertIsNone(result)

        # With expired token
        token = self.token_manager.generate_token("test_user")
        self.token_manager.tokens[token].expires_at = datetime.utcnow() - timedelta(seconds=1)
        result = self.token_manager.get_user_id(token)
        self.assertIsNone(result)

    def test_revoke_nonexistent_token(self):
        """Test revoke_token with nonexistent token."""
        result = self.token_manager.revoke_token("nonexistent_token")
        self.assertFalse(result)

    def test_revoke_all_tokens_for_user_no_tokens(self):
        """Test revoke_all_tokens_for_user with no tokens for user."""
        # Should return 0 if no tokens exist for the user
        result = self.token_manager.revoke_all_tokens_for_user("nonexistent_user")
        self.assertEqual(result, 0)

    def test_revoke_all_tokens_for_user_mixed_states(self):
        """Test revoke_all_tokens_for_user with mix of active and revoked tokens."""
        # Generate 3 tokens for user1
        user1_token1 = self.token_manager.generate_token("user1")
        user1_token2 = self.token_manager.generate_token("user1")
        user1_token3 = self.token_manager.generate_token("user1")

        # Generate 1 token for user2
        user2_token = self.token_manager.generate_token("user2")

        # Revoke one of user1's tokens
        self.token_manager.revoke_token(user1_token1)

        # Revoke all tokens for user1
        result = self.token_manager.revoke_all_tokens_for_user("user1")

        # Should have revoked 2 tokens (not the already revoked one)
        self.assertEqual(result, 2)

        # Verify all user1 tokens are revoked
        self.assertTrue(self.token_manager.tokens[user1_token1].revoked)
        self.assertTrue(self.token_manager.tokens[user1_token2].revoked)
        self.assertTrue(self.token_manager.tokens[user1_token3].revoked)

        # Verify user2 token is not revoked
        self.assertFalse(self.token_manager.tokens[user2_token].revoked)

    def test_cleanup_expired_tokens_none_expired(self):
        """Test cleanup_expired_tokens with no expired tokens."""
        # Generate tokens that aren't expired
        self.token_manager.generate_token("user1")
        self.token_manager.generate_token("user2")

        # Cleanup should remove 0 tokens
        result = self.token_manager.cleanup_expired_tokens()
        self.assertEqual(result, 0)
        self.assertEqual(len(self.token_manager.tokens), 2)

    def test_cleanup_expired_tokens_mixed(self):
        """Test cleanup_expired_tokens with mix of expired and active tokens."""
        # Generate tokens
        token1 = self.token_manager.generate_token("user1")
        token2 = self.token_manager.generate_token("user2")
        token3 = self.token_manager.generate_token("user3")

        # Set some to be expired
        self.token_manager.tokens[token1].expires_at = datetime.utcnow() - timedelta(seconds=1)
        self.token_manager.tokens[token3].expires_at = datetime.utcnow() - timedelta(seconds=1)

        # Cleanup should remove the expired tokens
        result = self.token_manager.cleanup_expired_tokens()
        self.assertEqual(result, 2)
        self.assertEqual(len(self.token_manager.tokens), 1)
        self.assertIn(token2, self.token_manager.tokens)


class TestSessionSecurityManagerAdditional(unittest.TestCase):
    """Additional tests for the SessionSecurityManager class."""

    def setUp(self):
        """Set up the test case."""
        self.token_manager = SessionTokenManager()
        self.security_manager = SessionSecurityManager(token_manager=self.token_manager, session_expiry_seconds=300)  # 5 minutes

    def test_register_session_with_metadata(self):
        """Test register_session stores metadata correctly."""
        token = self.security_manager.register_session("test_session", "test_user")

        # Verify token exists and has the correct metadata
        self.assertIn(token, self.token_manager.tokens)
        self.assertEqual(self.token_manager.tokens[token].metadata["session_id"], "test_session")

    def test_verify_session_access_with_expired_session(self):
        """Test verify_session_access with expired session."""
        # Register a session
        token = self.security_manager.register_session("test_session", "test_user")

        # Set the session to be expired
        self.security_manager.session_activity["test_session"] = datetime.utcnow() - timedelta(seconds=301)  # Expired by 1 second

        # Verify should return False
        result = self.security_manager.verify_session_access("test_session", token)
        self.assertFalse(result)

    def test_verify_session_access_with_invalid_session_id(self):
        """Test verify_session_access with invalid session ID."""
        # Register a session
        token = self.security_manager.register_session("test_session", "test_user")

        # Verify with wrong session ID
        result = self.security_manager.verify_session_access("wrong_session", token)
        self.assertFalse(result)

    def test_verify_session_access_with_mismatched_user(self):
        """Test verify_session_access with mismatched user."""
        # Register a session
        token = self.security_manager.register_session("test_session", "test_user")

        # Change the authorized user for the session
        self.security_manager.authorized_sessions["test_session"] = "different_user"

        # Verify should return False
        result = self.security_manager.verify_session_access("test_session", token)
        self.assertFalse(result)

    def test_revoke_session_access_with_nonexistent_session(self):
        """Test revoke_session_access with nonexistent session."""
        result = self.security_manager.revoke_session_access("nonexistent_session")
        self.assertFalse(result)

    def test_revoke_session_access_removes_from_tracking(self):
        """Test revoke_session_access removes session from tracking."""
        # Register a session
        self.security_manager.register_session("test_session", "test_user")

        # Verify session is tracked
        self.assertIn("test_session", self.security_manager.authorized_sessions)
        self.assertIn("test_session", self.security_manager.session_activity)

        # Revoke session access
        result = self.security_manager.revoke_session_access("test_session")
        self.assertTrue(result)

        # Verify session is no longer tracked
        self.assertNotIn("test_session", self.security_manager.authorized_sessions)
        self.assertNotIn("test_session", self.security_manager.session_activity)

    def test_update_session_activity_nonexistent_session(self):
        """Test update_session_activity with nonexistent session."""
        # Should silently add the session to tracking
        self.security_manager.update_session_activity("nonexistent_session")

        # Verify session activity was updated
        self.assertIn("nonexistent_session", self.security_manager.session_activity)

    def test_is_session_expired_nonexistent_session(self):
        """Test is_session_expired with nonexistent session."""
        # Should return True if session doesn't exist
        result = self.security_manager.is_session_expired("nonexistent_session")
        self.assertTrue(result)

    def test_is_session_expired_recent_activity(self):
        """Test is_session_expired with recent activity."""
        # Register a session
        self.security_manager.register_session("test_session", "test_user")

        # Should not be expired
        result = self.security_manager.is_session_expired("test_session")
        self.assertFalse(result)

    def test_is_session_expired_old_activity(self):
        """Test is_session_expired with old activity."""
        # Register a session
        self.security_manager.register_session("test_session", "test_user")

        # Set old activity time
        self.security_manager.session_activity["test_session"] = datetime.utcnow() - timedelta(seconds=301)  # Expired by 1 second

        # Should be expired
        result = self.security_manager.is_session_expired("test_session")
        self.assertTrue(result)

    def test_cleanup_expired_sessions_none_expired(self):
        """Test cleanup_expired_sessions with no expired sessions."""
        # Register sessions
        self.security_manager.register_session("session1", "user1")
        self.security_manager.register_session("session2", "user2")

        # Cleanup should remove 0 sessions
        result = self.security_manager.cleanup_expired_sessions()
        self.assertEqual(result, 0)
        self.assertEqual(len(self.security_manager.authorized_sessions), 2)

    def test_cleanup_expired_sessions_mixed(self):
        """Test cleanup_expired_sessions with mix of expired and active sessions."""
        # Register sessions
        self.security_manager.register_session("session1", "user1")
        self.security_manager.register_session("session2", "user2")
        self.security_manager.register_session("session3", "user3")

        # Set some to be expired
        self.security_manager.session_activity["session1"] = datetime.utcnow() - timedelta(seconds=301)  # Expired by 1 second
        self.security_manager.session_activity["session3"] = datetime.utcnow() - timedelta(seconds=301)  # Expired by 1 second

        # Cleanup should remove the expired sessions
        result = self.security_manager.cleanup_expired_sessions()
        self.assertEqual(result, 2)
        self.assertEqual(len(self.security_manager.authorized_sessions), 1)
        self.assertIn("session2", self.security_manager.authorized_sessions)
