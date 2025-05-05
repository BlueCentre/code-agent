"""
Mock implementations of Event-related classes from google.adk.events.
This is needed because the real implementations might not be available or may have changed.
"""

from enum import Enum
from typing import Any, Dict, List, Optional


# Mock Event State enum
class EventState(Enum):
    """Mock enum for Event state."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"


# Mock Event Type enum
class EventType(Enum):
    """Mock enum for Event type."""

    TEXT = "text"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESPONSE = "function_response"
    ERROR = "error"


# Mock Event class - simplified version but compatible with test usage
class Event:
    """Mock Event class."""

    def __init__(
        self,
        id: str,
        author: str = "test_author",
        invocation_id: str = "",
        type: Optional[EventType] = None,
        state: Optional[EventState] = None,
        parts: Optional[List[Dict[str, Any]]] = None,
        content=None,
        metadata=None,
    ):
        self.id = id
        self.author = author
        self.invocation_id = invocation_id
        self.type = type
        self.state = state
        self.parts = parts or []
        self.content = content
        self.metadata = metadata or {}
        # For compatibility with tests
        self.actions = EventActions()


# Mock EventActions class
class EventActions:
    """Mock EventActions class."""

    def __init__(self):
        self.actions = []
