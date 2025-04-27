"""
Session management services using ADK.

This module contains implementations of session services that connect the Code Agent with ADK.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai  # Import for API key configuration
from google.adk.events import Event

# ADK Imports
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from google.genai import types as genai_types  # For FunctionCall/Response types

from code_agent.adk.memory import BaseMemoryService, InMemoryMemoryService, MemoryManager, MemoryType, get_memory_manager
from code_agent.adk.session_config import IN_MEMORY_SESSION_CONFIG, CodeAgentSessionConfig
from code_agent.tools.verbosity import get_controller

logger = logging.getLogger(__name__)
verbosity_controller = get_controller()

# Singleton services
_adk_session_service: Optional[BaseSessionService] = None
_memory_service: Optional[BaseMemoryService] = None


# Temporary placeholders for missing classes - just to make code compile
class SessionSecurityManager:
    """Placeholder for session security management."""

    def __init__(self, config):
        self.config = config

    def start_cleanup_task(self):
        """Placeholder for starting cleanup task."""
        pass

    def register_session(self, session_id, user_id):
        """Placeholder for registering session."""
        return "dummy_token"

    def verify_session_access(self, session_id, token):
        """Placeholder for verifying session access."""
        return True

    def is_session_expired(self, session_id):
        """Placeholder for checking if session is expired."""
        return False

    def revoke_session_access(self, session_id):
        """Placeholder for revoking session access."""
        pass


class SessionAccessError(Exception):
    """Placeholder for session access error."""

    pass


def generate_session_id():
    """Placeholder for generating session ID."""
    import uuid

    return str(uuid.uuid4())


def initialize_adk_with_api_key(api_key: Optional[str] = None) -> None:
    """Initialize the Google Generative AI API with the provided API key."""
    # Use the provided API key or get from environment variables
    effective_api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_STUDIO_API_KEY")
    if effective_api_key:
        verbosity_controller.show_verbose(f"Initializing Google Generative AI with API key from {'provided parameter' if api_key else 'environment variable'}")
        genai.configure(api_key=effective_api_key)
    else:
        verbosity_controller.show_warning("No API key provided for Google Generative AI. Check GOOGLE_API_KEY or AI_STUDIO_API_KEY environment variables.")


async def get_adk_session_service(
    config: CodeAgentSessionConfig = IN_MEMORY_SESSION_CONFIG,
) -> BaseSessionService:
    """Get or create an ADK session service based on the provided configuration.

    Args:
        config: The session configuration to use

    Returns:
        An ADK session service
    """
    global _adk_session_service

    # Make sure the API key is configured
    initialize_adk_with_api_key()

    if _adk_session_service is None:
        # Currently only supports InMemorySessionService
        # Future: support persistent session service
        _adk_session_service = InMemorySessionService()
        verbosity_controller.show_verbose(f"Created new ADK {type(_adk_session_service).__name__} service")

    return _adk_session_service


# --- Memory Service ---
_memory_service: Optional[BaseMemoryService] = None


def get_memory_service(force_refresh: bool = False) -> BaseMemoryService:
    """
    Initializes and returns a singleton instance of the ADK Memory Service.
    Currently uses InMemoryMemoryService. Stored within services.py to break circular import.
    """
    global _memory_service
    if _memory_service is None or force_refresh:
        # In a real application, you might load configuration here
        # to decide which memory service implementation to use.
        # For now, we default to InMemoryMemoryService.
        _memory_service = InMemoryMemoryService()
        logger.info("Initialized InMemoryMemoryService.")
    return _memory_service


# --- End Memory Service ---


class CodeAgentADKSessionManager:
    """Manages interaction with the ADK session service."""

    def __init__(self, session_service: BaseSessionService, config: CodeAgentSessionConfig = IN_MEMORY_SESSION_CONFIG):
        self._session_service = session_service
        self._memory_managers: Dict[str, MemoryManager] = {}
        self.config = config
        self.security_manager = SessionSecurityManager(config)

        # Start the cleanup task if auto-cleanup is enabled
        if config.security.auto_cleanup_expired_sessions:
            self.security_manager.start_cleanup_task()

    def create_session(self, user_id: str = "default_user") -> Tuple[str, str]:
        """Creates a new session.

        Args:
            user_id: The ID of the user creating the session

        Returns:
            A tuple of (session_id, auth_token)

        Raises:
            ValueError: If the user has reached their session limit
        """
        # Generate a session ID if using UUIDs
        custom_session_id = generate_session_id() if self.config.use_uuid_for_session_ids else None

        # Create the session
        session = self._session_service.create_session(app_name="code_agent", user_id=user_id, session_id=custom_session_id)

        # Register the session with the security manager
        auth_token = self.security_manager.register_session(session.id, user_id)

        # Initialize memory manager for this session
        self._memory_managers[session.id] = get_memory_manager(session.id)

        return session.id, auth_token

    async def get_session(self, session_id: str, auth_token: Optional[str] = None) -> Session:
        """Retrieves an existing session.

        Args:
            session_id: The ID of the session to retrieve
            auth_token: The authentication token for the session

        Returns:
            The session object

        Raises:
            SessionAccessError: If access to the session is denied
            ValueError: If the session is not found
        """
        # Only check session access if authentication is enabled and the session exists
        if self.config.security.enable_authentication and isinstance(session_id, str):
            try:
                # First try to retrieve the session without auth check
                session = self._session_service.get_session(app_name="code_agent", user_id="default_user", session_id=session_id)

                # If session exists, check auth
                if session and not self.security_manager.verify_session_access(session_id, auth_token):
                    raise SessionAccessError(f"Access denied to session: {session_id}")

                # Check if session has expired
                if session and self.security_manager.is_session_expired(session_id):
                    raise SessionAccessError(f"Session has expired: {session_id}")

                # Return the session if it exists and passes checks
                if session:
                    return session
            except Exception as e:
                # If any error occurs during retrieval, create a new session
                if "not found" in str(e).lower():
                    # Session doesn't exist, continue to create a new one
                    pass
                else:
                    # Re-raise other errors
                    raise

        # Get the session or create if it doesn't exist
        session = self._session_service.get_session(app_name="code_agent", user_id="default_user", session_id=session_id)

        if not session:
            raise ValueError(f"Session not found: {session_id}")

        return session

    async def add_event(self, session_id: str, event: Event, auth_token: Optional[str] = None) -> None:
        """Adds an event to the specified session.

        Args:
            session_id: The ID of the session
            event: The event to add
            auth_token: The authentication token for the session

        Raises:
            SessionAccessError: If access to the session is denied
        """
        # Retrieve session (with access check)
        session = await self.get_session(session_id, auth_token)

        # Check event count limit
        if hasattr(session, "events") and len(session.events) >= self.config.max_events_per_session:
            raise ValueError(f"Session has reached the maximum number of events: {self.config.max_events_per_session}")

        # Add the event
        self._session_service.append_event(session=session, event=event)

    async def add_user_message(self, session_id: str, content: str, invocation_id: Optional[str] = None) -> None:  # SessionId -> str
        """Adds a user message event."""
        # Event structure based on events/event.py
        event = Event(
            author="user",
            content=genai_types.Content(parts=[genai_types.Part(text=content)]),
            invocation_id=invocation_id or "",  # Ensure it's a string, even if empty
        )
        await self.add_event(session_id, event)

        # Add to memory manager
        memory_manager = self._get_memory_manager(session_id)
        memory_manager.add_memory(content=content, memory_type=MemoryType.SHORT_TERM, importance=1.0, metadata={"author": "user", "type": "query"})

    async def add_assistant_message(
        self,
        session_id: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[genai_types.FunctionCall]] = None,
        invocation_id: Optional[str] = None,
        partial: bool = False,  # Add partial flag
    ) -> None:  # SessionId -> str, Tool call type updated
        """Adds an assistant message event, potentially including tool calls or partial content."""
        parts = []
        if content is not None:
            parts.append(genai_types.Part(text=content))
        if tool_calls:
            for tc in tool_calls:
                parts.append(genai_types.Part(function_call=tc))

        event = Event(
            author="assistant",  # Assuming a fixed author name for now
            content=genai_types.Content(parts=parts),
            invocation_id=invocation_id or "",
            partial=partial,  # Set partial flag
        )
        await self.add_event(session_id, event)

        # Add to memory manager (skip if partial)
        if not partial:
            memory_manager = self._get_memory_manager(session_id)
            memory_manager.add_memory(content=content, memory_type=MemoryType.SHORT_TERM, importance=0.8, metadata={"author": "assistant", "type": "response"})

            # Add tool calls to working memory
            if tool_calls:
                for tc in tool_calls:
                    memory_manager.add_memory(
                        content=f"Called function {tc.name} with args: {tc.args}",
                        memory_type=MemoryType.WORKING,
                        importance=0.7,
                        metadata={"author": "assistant", "type": "function_call", "function_name": tc.name},
                    )

    async def add_tool_result(
        self, session_id: str, tool_call_id: str, tool_name: str, content: Any, author: str = "assistant", invocation_id: Optional[str] = None
    ):
        """Adds a tool result event to the session, following ADK history conventions."""
        session = await self.get_session(session_id)

        # Ensure content is a simple string
        content_str = str(content)

        try:
            # Create a simple dictionary with the result string
            response_dict = {"result": content_str}

            # Create function response with a dictionary
            function_response = genai_types.FunctionResponse(name=tool_name, response=response_dict)

            # Create the Content object with role='function' for history formatting
            event_content = genai_types.Content(
                parts=[genai_types.Part(function_response=function_response)],
                role="function",  # Set role='function' for tool results in history
            )

            event = Event(author=author, content=event_content, invocation_id=invocation_id or "")

            # Append event using the underlying service
            self._session_service.append_event(session=session, event=event)
        except Exception as e:
            # If we can't create the response properly, log the error
            import traceback

            print(f"Error creating tool result: {e}")
            print(traceback.format_exc())

            # Try a simpler approach - text response instead of function response
            try:
                simple_content = genai_types.Content(parts=[genai_types.Part(text=f"Tool {tool_name} result: {content_str}")], role="user")
                simple_event = Event(author=author, content=simple_content, invocation_id=invocation_id or "")
                self._session_service.append_event(session=session, event=simple_event)
            except Exception as e2:
                print(f"Error creating simplified tool result: {e2}")
                print(traceback.format_exc())

        # Add to memory manager
        try:
            memory_manager = self._get_memory_manager(session_id)
            memory_manager.add_memory(
                content=f"Function {tool_name} returned: {content_str}",
                memory_type=MemoryType.WORKING,
                importance=0.7,
                metadata={"author": author, "type": "function_response", "function_name": tool_name},
            )
        except Exception as mem_error:
            print(f"Error adding tool result to memory: {mem_error}")
            # Continue without adding to memory

    async def add_error_event(
        self, session_id: str, error_message: str, error_code: Optional[str] = None, author: str = "assistant", invocation_id: Optional[str] = None
    ):
        """Adds an error event to the session."""
        # Create an Event object specifically for errors
        error_content = genai_types.Content(parts=[genai_types.Part(text=error_message)], role="user")
        event = Event(
            author=author,
            content=error_content,
            custom_metadata={"event_type": "error"},
            invocation_id=invocation_id or "",
        )
        # Directly call add_event which handles session retrieval and appending
        await self.add_event(session_id, event)

    async def add_system_message(self, session_id: str, content: str, invocation_id: Optional[str] = None):
        """Adds a system message event."""
        # ADK v0.3.0 might not have a dedicated system message type.
        # Using author="system" convention.
        event = Event(author="system", content=genai_types.Content(parts=[genai_types.Part(text=content)]), invocation_id=invocation_id or "")
        await self.add_event(session_id, event)

    async def get_history(self, session_id: str) -> List[Event]:  # SessionId -> str
        """Retrieves the event history for a session."""
        # TODO: Verify get_history arguments/return type for BaseSessionService v0.3.0
        session = await self.get_session(session_id)
        # History is likely stored within the session object
        return session.events if session and hasattr(session, "events") else []

    async def clear_history(self, session_id: str) -> None:  # SessionId -> str
        """Clears the history for a session (if supported by the service)."""
        # Note: Not all session services might support clearing.
        # InMemorySessionService typically clears on restart or explicit delete.
        # For InMemory, creating a new session via create_session() might be the intended way.
        # This method might need removal or modification based on BaseSessionService capabilities.
        pass  # Placeholder - actual clear logic depends on service capabilities

    async def add_partial_assistant_message(self, session_id: str, content: str, invocation_id: Optional[str] = None) -> None:
        """Adds a partial assistant message event (for streaming)."""
        # Use the existing add_assistant_message but force partial=True
        await self.add_assistant_message(
            session_id=session_id,
            content=content,
            tool_calls=None,  # Partial messages shouldn't contain tool calls
            invocation_id=invocation_id,
            partial=True,
        )

    def _get_memory_manager(self, session_id: str) -> MemoryManager:
        """Gets or creates a memory manager for the session.

        Args:
            session_id: The ID of the session to get a memory manager for

        Returns:
            A MemoryManager instance for the session
        """
        if session_id not in self._memory_managers:
            self._memory_managers[session_id] = get_memory_manager(session_id)
        return self._memory_managers[session_id]

    async def get_conversation_summary(self, session_id: str) -> str:
        """Generate a summary of the conversation in the session.

        Args:
            session_id: The ID of the session to summarize

        Returns:
            A string summary of the conversation
        """
        session = await self.get_session(session_id)
        memory_manager = self._get_memory_manager(session_id)
        return memory_manager.summarize_conversation(session)

    async def extract_session_memories(self, session_id: str) -> None:
        """Extract memories from the session and store them in the memory manager.

        Args:
            session_id: The ID of the session to extract memories from
        """
        session = await self.get_session(session_id)
        memory_manager = self._get_memory_manager(session_id)
        memory_manager.extract_memories_from_session(session)

    async def get_memories(self, session_id: str, memory_type: Optional[MemoryType] = None, min_importance: float = 0.0) -> List[Dict[str, Any]]:
        """Get memories for a session of a specific type with minimum importance.

        Args:
            session_id: The ID of the session to get memories for
            memory_type: The type of memory to retrieve, or None for all types
            min_importance: Minimum importance score for retrieved memories

        Returns:
            List of memory entries matching the criteria
        """
        memory_manager = self._get_memory_manager(session_id)
        memories = memory_manager.get_memories(memory_type, min_importance)

        # Convert to dictionaries for easier handling in the agent
        return [
            {"content": memory.content, "memory_type": memory.memory_type.value, "importance": memory.importance, "metadata": memory.metadata}
            for memory in memories
        ]

    async def close_session(self, session_id: str, auth_token: Optional[str] = None) -> None:
        """Closes a session, cleaning up resources.

        Args:
            session_id: The ID of the session to close
            auth_token: The authentication token for the session

        Raises:
            SessionAccessError: If access to the session is denied
        """
        # Check session access
        if self.config.security.enable_authentication and not self.security_manager.verify_session_access(session_id, auth_token):
            raise SessionAccessError(f"Access denied to session: {session_id}")

        # Clean up memory manager
        if session_id in self._memory_managers:
            # The memory manager doesn't need explicit cleanup beyond removing the reference
            del self._memory_managers[session_id]

        # Revoke session access
        self.security_manager.revoke_session_access(session_id)

        # Note: ADK v0.3.0 doesn't seem to have an explicit method to close or delete sessions
        # The session will be garbage collected when no longer referenced
        logger.info(f"Closed session: {session_id}")
