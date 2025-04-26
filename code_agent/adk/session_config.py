import os
import secrets
import uuid
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

# Placeholder for ADK Session configuration options


class SessionSecurityConfig(BaseModel):
    """Security configuration for sessions."""

    enable_authentication: bool = False
    authentication_token_expiry_seconds: int = 3600  # 1 hour
    session_id_validation: bool = True
    max_sessions_per_user: int = 10
    session_timeout_seconds: int = 3600  # 1 hour
    enable_session_isolation: bool = True
    auto_cleanup_expired_sessions: bool = True


class CodeAgentSessionConfig(BaseModel):
    """Configuration specific to Code Agent sessions."""

    # Session ID generation
    use_uuid_for_session_ids: bool = True

    # Persistence settings
    persistence_type: str = "in_memory"  # Options: "in_memory", "filesystem"
    filesystem_base_path: Optional[str] = None

    # Security settings
    security: SessionSecurityConfig = SessionSecurityConfig()

    # Resource limits
    max_events_per_session: int = 1000
    max_session_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Clean up settings
    cleanup_interval_seconds: int = 3600  # 1 hour


class SessionTokenManager:
    """Manages authentication tokens for sessions."""

    def __init__(self):
        self._tokens: Dict[str, Dict] = {}  # session_id -> {token, expiry, user_id}

    def generate_token(self, session_id: str, user_id: str, expiry_seconds: int = 3600) -> str:
        """Generate a new authentication token for a session.

        Args:
            session_id: The ID of the session
            user_id: The ID of the user who owns the session
            expiry_seconds: Number of seconds until the token expires

        Returns:
            A secure token string
        """
        token = secrets.token_urlsafe(32)
        self._tokens[session_id] = {"token": token, "user_id": user_id, "expiry": expiry_seconds}
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate an authentication token for a session.

        Args:
            session_id: The ID of the session
            token: The token to validate

        Returns:
            True if the token is valid, False otherwise
        """
        if session_id not in self._tokens:
            return False

        session_token = self._tokens.get(session_id, {}).get("token")
        return session_token == token

    def get_user_id(self, session_id: str) -> Optional[str]:
        """Get the user ID associated with a session.

        Args:
            session_id: The ID of the session

        Returns:
            The user ID, or None if the session doesn't exist
        """
        return self._tokens.get(session_id, {}).get("user_id")

    def revoke_token(self, session_id: str) -> None:
        """Revoke the token for a session.

        Args:
            session_id: The ID of the session
        """
        if session_id in self._tokens:
            del self._tokens[session_id]


# Default configurations
IN_MEMORY_SESSION_CONFIG = CodeAgentSessionConfig(persistence_type="in_memory", security=SessionSecurityConfig())

# Filesystem-based session configuration
FILESYSTEM_SESSION_CONFIG = CodeAgentSessionConfig(
    persistence_type="filesystem",
    filesystem_base_path=os.environ.get("CODE_AGENT_SESSION_PATH", str(Path.home() / ".code_agent" / "sessions")),
    security=SessionSecurityConfig(
        session_timeout_seconds=86400  # 24 hours
    ),
)

# Shared instances
_token_manager = SessionTokenManager()


def get_token_manager() -> SessionTokenManager:
    """Get the shared token manager instance."""
    return _token_manager


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        A unique session ID string
    """
    return str(uuid.uuid4())
