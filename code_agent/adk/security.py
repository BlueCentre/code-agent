# Session security utilities for ADK integration
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Session token validity duration in seconds (default: 1 hour)
DEFAULT_TOKEN_VALIDITY_SECONDS = 60 * 60

# Default session expiration: 8 hours of inactivity
DEFAULT_SESSION_EXPIRY_SECONDS = 8 * 60 * 60


class SessionToken(BaseModel):
    """Token used for session authentication."""

    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False
    metadata: Dict[str, str] = Field(default_factory=dict)


class SessionTokenManager:
    """Manages session tokens for authentication."""

    def __init__(self, token_validity_seconds: int = DEFAULT_TOKEN_VALIDITY_SECONDS):
        """Initialize the token manager.

        Args:
            token_validity_seconds: How long tokens are valid for in seconds
        """
        self.tokens: Dict[str, SessionToken] = {}
        self.token_validity_seconds = token_validity_seconds

    def generate_token(self, user_id: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """Generate a new session token.

        Args:
            user_id: ID of the user to generate token for
            metadata: Optional metadata to associate with the token

        Returns:
            The generated token string
        """
        # Generate secure random token
        token_bytes = secrets.token_bytes(32)
        token = hashlib.sha256(token_bytes).hexdigest()

        # Create token entry
        now = datetime.utcnow()
        token_entry = SessionToken(
            token=token, user_id=user_id, created_at=now, expires_at=now + timedelta(seconds=self.token_validity_seconds), metadata=metadata or {}
        )

        # Store token
        self.tokens[token] = token_entry
        logger.debug(f"Generated token for user {user_id}")

        return token

    def validate_token(self, token: str) -> bool:
        """Check if a token is valid.

        Args:
            token: The token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Check if token exists
        if token not in self.tokens:
            logger.debug("Token validation failed: token doesn't exist")
            return False

        token_entry = self.tokens[token]

        # Check if token is expired
        if token_entry.expires_at < datetime.utcnow():
            logger.debug("Token validation failed: token expired")
            return False

        # Check if token is revoked
        if token_entry.revoked:
            logger.debug("Token validation failed: token revoked")
            return False

        return True

    def get_user_id(self, token: str) -> Optional[str]:
        """Get the user ID associated with a token.

        Args:
            token: The token to get user ID for

        Returns:
            User ID if token is valid, None otherwise
        """
        if not self.validate_token(token):
            return None

        return self.tokens[token].user_id

    def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: The token to revoke

        Returns:
            True if token was revoked, False otherwise
        """
        if token not in self.tokens:
            return False

        self.tokens[token].revoked = True
        logger.debug(f"Revoked token for user {self.tokens[token].user_id}")
        return True

    def revoke_all_tokens_for_user(self, user_id: str) -> int:
        """Revoke all tokens for a user.

        Args:
            user_id: The user ID to revoke tokens for

        Returns:
            Number of tokens revoked
        """
        count = 0
        for token_entry in self.tokens.values():
            if token_entry.user_id == user_id and not token_entry.revoked:
                token_entry.revoked = True
                count += 1

        logger.debug(f"Revoked {count} tokens for user {user_id}")
        return count

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from storage.

        Returns:
            Number of tokens removed
        """
        now = datetime.utcnow()
        expired_tokens = [token for token, entry in self.tokens.items() if entry.expires_at < now]

        for token in expired_tokens:
            del self.tokens[token]

        logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens")
        return len(expired_tokens)


class SessionSecurityManager:
    """Manages security for ADK sessions."""

    def __init__(self, token_manager: Optional[SessionTokenManager] = None, session_expiry_seconds: int = DEFAULT_SESSION_EXPIRY_SECONDS):
        """Initialize the session security manager.

        Args:
            token_manager: Token manager to use for authentication
            session_expiry_seconds: How long sessions can be inactive before expiring
        """
        self.token_manager = token_manager or SessionTokenManager()
        self.session_expiry_seconds = session_expiry_seconds

        # Maps session IDs to authorized user IDs
        self.authorized_sessions: Dict[str, str] = {}

        # Maps session IDs to last activity time
        self.session_activity: Dict[str, datetime] = {}

    def register_session(self, session_id: str, user_id: str) -> str:
        """Register a new session and generate an auth token.

        Args:
            session_id: ID of the session to register
            user_id: ID of the user who owns the session

        Returns:
            Auth token for the session
        """
        # Generate token
        token = self.token_manager.generate_token(user_id, metadata={"session_id": session_id})

        # Register session
        self.authorized_sessions[session_id] = user_id
        self.update_session_activity(session_id)

        logger.info(f"Registered session {session_id} for user {user_id}")
        return token

    def verify_session_access(self, session_id: str, token: str) -> bool:
        """Verify that a token grants access to a session.

        Args:
            session_id: ID of the session to check access for
            token: Token to check

        Returns:
            True if token grants access to session, False otherwise
        """
        # Validate token
        user_id = self.token_manager.get_user_id(token)
        if not user_id:
            logger.warning("Session access denied: invalid token")
            return False

        # Check if session is registered
        if session_id not in self.authorized_sessions:
            logger.warning(f"Session access denied: session {session_id} not registered")
            return False

        # Check if session is authorized for user
        if self.authorized_sessions[session_id] != user_id:
            logger.warning(f"Session access denied: session {session_id} not authorized for user {user_id}")
            return False

        # Check if session is expired
        if self.is_session_expired(session_id):
            logger.warning(f"Session access denied: session {session_id} expired")
            return False

        # Update activity timestamp
        self.update_session_activity(session_id)

        return True

    def revoke_session_access(self, session_id: str) -> bool:
        """Revoke access to a session.

        Args:
            session_id: ID of the session to revoke access for

        Returns:
            True if session access was revoked, False otherwise
        """
        if session_id not in self.authorized_sessions:
            return False

        user_id = self.authorized_sessions[session_id]
        del self.authorized_sessions[session_id]

        if session_id in self.session_activity:
            del self.session_activity[session_id]

        logger.info(f"Revoked access to session {session_id} for user {user_id}")
        return True

    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity time for a session.

        Args:
            session_id: ID of the session to update activity for
        """
        self.session_activity[session_id] = datetime.utcnow()

    def is_session_expired(self, session_id: str) -> bool:
        """Check if a session has expired due to inactivity.

        Args:
            session_id: ID of the session to check

        Returns:
            True if session has expired, False otherwise
        """
        if session_id not in self.session_activity:
            return True

        last_activity = self.session_activity[session_id]
        expiry_time = last_activity + timedelta(seconds=self.session_expiry_seconds)

        return expiry_time < datetime.utcnow()

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from storage.

        Returns:
            Number of sessions removed
        """
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, last_activity in self.session_activity.items():
            expiry_time = last_activity + timedelta(seconds=self.session_expiry_seconds)
            if expiry_time < now:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            if session_id in self.authorized_sessions:
                del self.authorized_sessions[session_id]

            if session_id in self.session_activity:
                del self.session_activity[session_id]

        # Also cleanup expired tokens
        self.token_manager.cleanup_expired_tokens()

        logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)
