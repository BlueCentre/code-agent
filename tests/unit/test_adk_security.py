"""
Tests for the code_agent.adk.security module.
"""

import datetime
from unittest.mock import MagicMock, patch

from code_agent.adk.security import (
    DEFAULT_SESSION_EXPIRY_SECONDS,
    DEFAULT_TOKEN_VALIDITY_SECONDS,
    SessionSecurityManager,
    SessionToken,
    SessionTokenManager,
)


class TestSessionToken:
    """Tests for the SessionToken class."""

    def test_session_token_creation(self):
        """Test that a SessionToken can be created with required fields."""
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(hours=1)

        token = SessionToken(
            token="abc123",
            user_id="user-123",
            created_at=now,
            expires_at=expires,
        )

        assert token.token == "abc123"
        assert token.user_id == "user-123"
        assert token.created_at == now
        assert token.expires_at == expires
        assert token.revoked is False
        assert token.metadata == {}

    def test_session_token_with_metadata(self):
        """Test that a SessionToken can be created with metadata."""
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(hours=1)
        metadata = {"session_id": "sess-456", "client_ip": "127.0.0.1"}

        token = SessionToken(
            token="abc123",
            user_id="user-123",
            created_at=now,
            expires_at=expires,
            metadata=metadata,
        )

        # Just verify the entire metadata object matches
        assert token.metadata == metadata


class TestSessionTokenManager:
    """Tests for the SessionTokenManager class."""

    def test_init_default(self):
        """Test that SessionTokenManager initializes with default parameters."""
        manager = SessionTokenManager()
        assert manager.token_validity_seconds == DEFAULT_TOKEN_VALIDITY_SECONDS
        assert manager.tokens == {}

    def test_init_custom_validity(self):
        """Test that SessionTokenManager can be initialized with custom token validity."""
        custom_validity = 3600 * 24  # 1 day
        manager = SessionTokenManager(token_validity_seconds=custom_validity)
        assert manager.token_validity_seconds == custom_validity

    def test_generate_token(self):
        """Test generating a new token."""
        manager = SessionTokenManager()
        user_id = "user-123"

        # Test generating token without metadata
        token = manager.generate_token(user_id)

        # Check token is stored
        assert token in manager.tokens

        # Check token properties
        token_entry = manager.tokens[token]
        assert token_entry.token == token
        assert token_entry.user_id == user_id
        assert isinstance(token_entry.created_at, datetime.datetime)
        assert isinstance(token_entry.expires_at, datetime.datetime)
        assert token_entry.revoked is False
        assert token_entry.metadata == {}

    def test_generate_token_with_metadata(self):
        """Test generating a token with metadata."""
        manager = SessionTokenManager()
        user_id = "user-123"
        metadata = {"client": "web", "ip": "192.168.1.1"}

        token = manager.generate_token(user_id, metadata)

        # Check metadata was stored
        assert manager.tokens[token].metadata == metadata

    def test_validate_token_valid(self):
        """Test validating a valid token."""
        manager = SessionTokenManager()
        user_id = "user-123"
        token = manager.generate_token(user_id)

        # Should be valid
        assert manager.validate_token(token) is True

    def test_validate_token_nonexistent(self):
        """Test validating a token that doesn't exist."""
        manager = SessionTokenManager()

        # Should be invalid
        assert manager.validate_token("nonexistent-token") is False

    def test_validate_token_expired(self):
        """Test validating an expired token."""
        manager = SessionTokenManager(token_validity_seconds=1)
        user_id = "user-123"
        token = manager.generate_token(user_id)

        # Fast-forward time
        future_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
        with patch("code_agent.adk.security.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = future_time

            # Should be invalid
            assert manager.validate_token(token) is False

    def test_validate_token_revoked(self):
        """Test validating a revoked token."""
        manager = SessionTokenManager()
        user_id = "user-123"
        token = manager.generate_token(user_id)

        # Revoke the token
        manager.revoke_token(token)

        # Should be invalid
        assert manager.validate_token(token) is False

    def test_get_user_id_valid(self):
        """Test getting user ID from a valid token."""
        manager = SessionTokenManager()
        user_id = "user-123"
        token = manager.generate_token(user_id)

        # Should return the user ID
        assert manager.get_user_id(token) == user_id

    def test_get_user_id_invalid(self):
        """Test getting user ID from an invalid token."""
        manager = SessionTokenManager()

        # Should return None
        assert manager.get_user_id("nonexistent-token") is None

    def test_revoke_token_existing(self):
        """Test revoking an existing token."""
        manager = SessionTokenManager()
        user_id = "user-123"
        token = manager.generate_token(user_id)

        # Revoke should succeed
        assert manager.revoke_token(token) is True

        # Token should be revoked
        assert manager.tokens[token].revoked is True

    def test_revoke_token_nonexistent(self):
        """Test revoking a token that doesn't exist."""
        manager = SessionTokenManager()

        # Revoke should fail
        assert manager.revoke_token("nonexistent-token") is False

    def test_revoke_all_tokens_for_user(self):
        """Test revoking all tokens for a user."""
        manager = SessionTokenManager()
        user_id = "user-123"
        other_user_id = "user-456"

        # Generate multiple tokens for both users
        token1 = manager.generate_token(user_id)
        token2 = manager.generate_token(user_id)
        token3 = manager.generate_token(user_id)
        token4 = manager.generate_token(other_user_id)

        # Revoke all tokens for user-123
        count = manager.revoke_all_tokens_for_user(user_id)

        # Should have revoked 3 tokens
        assert count == 3

        # User-123's tokens should be revoked
        assert manager.tokens[token1].revoked is True
        assert manager.tokens[token2].revoked is True
        assert manager.tokens[token3].revoked is True

        # Other user's token should not be revoked
        assert manager.tokens[token4].revoked is False

    def test_cleanup_expired_tokens(self):
        """Test cleaning up expired tokens."""
        manager = SessionTokenManager(token_validity_seconds=1)
        user_id = "user-123"

        # Generate a token
        token = manager.generate_token(user_id)

        # Fast-forward time
        future_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
        with patch("code_agent.adk.security.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = future_time

            # Clean up expired tokens
            count = manager.cleanup_expired_tokens()

            # Should have removed 1 token
            assert count == 1

            # Token should be removed from storage
            assert token not in manager.tokens


class TestSessionSecurityManager:
    """Tests for the SessionSecurityManager class."""

    def test_init_default(self):
        """Test that SessionSecurityManager initializes with default parameters."""
        manager = SessionSecurityManager()

        assert isinstance(manager.token_manager, SessionTokenManager)
        assert manager.session_expiry_seconds == DEFAULT_SESSION_EXPIRY_SECONDS
        assert manager.authorized_sessions == {}
        assert manager.session_activity == {}

    def test_init_custom(self):
        """Test that SessionSecurityManager can be initialized with custom parameters."""
        token_manager = SessionTokenManager()
        custom_expiry = 3600 * 4  # 4 hours

        manager = SessionSecurityManager(token_manager=token_manager, session_expiry_seconds=custom_expiry)

        assert manager.token_manager is token_manager
        assert manager.session_expiry_seconds == custom_expiry

    def test_register_session(self):
        """Test registering a new session."""
        manager = SessionSecurityManager()
        session_id = "session-123"
        user_id = "user-123"

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.generate_token.return_value = "mocked-token"

        # Register session
        token = manager.register_session(session_id, user_id)

        # Check token
        assert token == "mocked-token"

        # Check token manager was called
        manager.token_manager.generate_token.assert_called_once_with(user_id, metadata={"session_id": session_id})

        # Check session was registered
        assert manager.authorized_sessions[session_id] == user_id

        # Check activity was updated
        assert session_id in manager.session_activity
        assert isinstance(manager.session_activity[session_id], datetime.datetime)

    def test_verify_session_access_valid(self):
        """Test verifying access to a valid session."""
        manager = SessionSecurityManager()
        session_id = "session-123"
        user_id = "user-123"

        # Set up session
        manager.authorized_sessions[session_id] = user_id
        manager.update_session_activity(session_id)

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.get_user_id.return_value = user_id

        # Verify access
        result = manager.verify_session_access(session_id, "valid-token")

        # Should succeed
        assert result is True

        # Check token manager was called
        manager.token_manager.get_user_id.assert_called_once_with("valid-token")

    def test_verify_session_access_invalid_token(self):
        """Test verifying access with an invalid token."""
        manager = SessionSecurityManager()
        session_id = "session-123"

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.get_user_id.return_value = None

        # Verify access
        result = manager.verify_session_access(session_id, "invalid-token")

        # Should fail
        assert result is False

    def test_verify_session_access_unregistered_session(self):
        """Test verifying access to an unregistered session."""
        manager = SessionSecurityManager()
        user_id = "user-123"

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.get_user_id.return_value = user_id

        # Verify access to unregistered session
        result = manager.verify_session_access("unregistered-session", "valid-token")

        # Should fail
        assert result is False

    def test_verify_session_access_unauthorized_user(self):
        """Test verifying access for an unauthorized user."""
        manager = SessionSecurityManager()
        session_id = "session-123"
        authorized_user_id = "user-123"
        unauthorized_user_id = "user-456"

        # Set up session
        manager.authorized_sessions[session_id] = authorized_user_id
        manager.update_session_activity(session_id)

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.get_user_id.return_value = unauthorized_user_id

        # Verify access
        result = manager.verify_session_access(session_id, "unauthorized-token")

        # Should fail
        assert result is False

    def test_verify_session_access_expired(self):
        """Test verifying access to an expired session."""
        manager = SessionSecurityManager(session_expiry_seconds=1)
        session_id = "session-123"
        user_id = "user-123"

        # Set up session
        manager.authorized_sessions[session_id] = user_id
        manager.update_session_activity(session_id)

        # Mock token manager
        manager.token_manager = MagicMock()
        manager.token_manager.get_user_id.return_value = user_id

        # Fast-forward time
        future_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
        with patch("code_agent.adk.security.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = future_time

            # Verify access
            result = manager.verify_session_access(session_id, "valid-token")

            # Should fail due to expiration
            assert result is False

    def test_revoke_session_access_existing(self):
        """Test revoking access to an existing session."""
        manager = SessionSecurityManager()
        session_id = "session-123"
        user_id = "user-123"

        # Set up session
        manager.authorized_sessions[session_id] = user_id
        manager.session_activity[session_id] = datetime.datetime.utcnow()

        # Revoke access
        result = manager.revoke_session_access(session_id)

        # Should succeed
        assert result is True

        # Session should be removed
        assert session_id not in manager.authorized_sessions
        assert session_id not in manager.session_activity

    def test_revoke_session_access_nonexistent(self):
        """Test revoking access to a nonexistent session."""
        manager = SessionSecurityManager()

        # Revoke access
        result = manager.revoke_session_access("nonexistent-session")

        # Should fail
        assert result is False

    def test_update_session_activity(self):
        """Test updating session activity timestamp."""
        manager = SessionSecurityManager()
        session_id = "session-123"

        # Update activity
        manager.update_session_activity(session_id)

        # Check timestamp was set
        assert session_id in manager.session_activity
        assert isinstance(manager.session_activity[session_id], datetime.datetime)

    def test_is_session_expired_nonexistent(self):
        """Test checking if a nonexistent session is expired."""
        manager = SessionSecurityManager()

        # Nonexistent sessions are considered expired
        assert manager.is_session_expired("nonexistent-session") is True

    def test_is_session_expired_valid(self):
        """Test checking if a valid session is expired."""
        manager = SessionSecurityManager()
        session_id = "session-123"

        # Set up activity
        manager.update_session_activity(session_id)

        # Should not be expired
        assert manager.is_session_expired(session_id) is False

    def test_is_session_expired_outdated(self):
        """Test checking if an outdated session is expired."""
        manager = SessionSecurityManager(session_expiry_seconds=1)
        session_id = "session-123"

        # Set up activity
        manager.session_activity[session_id] = datetime.datetime.utcnow()

        # Fast-forward time
        future_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
        with patch("code_agent.adk.security.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = future_time

            # Should be expired
            assert manager.is_session_expired(session_id) is True

    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        manager = SessionSecurityManager(session_expiry_seconds=1)

        # Set up multiple sessions
        manager.authorized_sessions = {
            "session-1": "user-1",
            "session-2": "user-2",
            "session-3": "user-3",
        }

        # Set up activity (session-3 is recent, others are old)
        now = datetime.datetime.utcnow()
        manager.session_activity = {
            "session-1": now - datetime.timedelta(seconds=2),
            "session-2": now - datetime.timedelta(seconds=2),
            "session-3": now,
        }

        # Clean up expired sessions
        count = manager.cleanup_expired_sessions()

        # Should have removed 2 sessions
        assert count == 2

        # Check which sessions were removed
        assert "session-1" not in manager.authorized_sessions
        assert "session-2" not in manager.authorized_sessions
        assert "session-3" in manager.authorized_sessions

        assert "session-1" not in manager.session_activity
        assert "session-2" not in manager.session_activity
        assert "session-3" in manager.session_activity
