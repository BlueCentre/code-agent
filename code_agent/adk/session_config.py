"""
Session configuration for Google ADK integration.

This module defines the configuration options for ADK sessions, including
memory management, persistence, and other session-related settings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionPersistenceType(Enum):
    """Defines how session data is persisted."""

    MEMORY = "memory"  # In-memory only
    FILE = "file"  # Local file persistence
    CLOUD = "cloud"  # Cloud storage (when implemented)


class SessionMemoryType(Enum):
    """Defines the type of memory management used for the session."""

    BASIC = "basic"  # Simple message history
    STRUCTURED = "structured"  # Structured memory with entity tracking
    VECTOR = "vector"  # Vector-based memory with embedding search


@dataclass
class SessionConfig:
    """Configuration for ADK sessions."""

    # Session identification and basics
    session_id: Optional[str] = None  # If None, will be auto-generated
    session_name: Optional[str] = None

    # Persistence configuration
    persistence_type: SessionPersistenceType = SessionPersistenceType.MEMORY
    persistence_path: Optional[str] = None  # For FILE persistence

    # Memory configuration
    memory_type: SessionMemoryType = SessionMemoryType.BASIC
    memory_options: Dict[str, Any] = field(default_factory=dict)

    # Session limits
    max_turns: Optional[int] = None  # Maximum conversation turns, None for unlimited
    max_tokens: Optional[int] = None  # Maximum tokens in memory, None for unlimited

    # Session metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Agent configuration
    agent_options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for ADK."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "persistence": {
                "type": self.persistence_type.value,
                "path": self.persistence_path,
            },
            "memory": {
                "type": self.memory_type.value,
                "options": self.memory_options,
            },
            "limits": {
                "max_turns": self.max_turns,
                "max_tokens": self.max_tokens,
            },
            "metadata": self.metadata,
            "tags": self.tags,
            "agent_options": self.agent_options,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionConfig":
        """Create session config from dictionary."""
        persistence_data = data.get("persistence", {})
        memory_data = data.get("memory", {})
        limits_data = data.get("limits", {})

        return cls(
            session_id=data.get("session_id"),
            session_name=data.get("session_name"),
            persistence_type=SessionPersistenceType(persistence_data.get("type", "memory")),
            persistence_path=persistence_data.get("path"),
            memory_type=SessionMemoryType(memory_data.get("type", "basic")),
            memory_options=memory_data.get("options", {}),
            max_turns=limits_data.get("max_turns"),
            max_tokens=limits_data.get("max_tokens"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            agent_options=data.get("agent_options", {}),
        )


def create_default_session_config() -> SessionConfig:
    """Create a default session configuration."""
    return SessionConfig(
        memory_type=SessionMemoryType.BASIC,
        persistence_type=SessionPersistenceType.MEMORY,
    )


def create_persistent_session_config(session_name: str, persistence_path: Optional[str] = None) -> SessionConfig:
    """Create a session configuration with file persistence."""
    return SessionConfig(
        session_name=session_name,
        persistence_type=SessionPersistenceType.FILE,
        persistence_path=persistence_path,
        memory_type=SessionMemoryType.STRUCTURED,
    )
