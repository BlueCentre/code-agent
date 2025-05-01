"""Custom MemoryService implementation that persists sessions to a JSON file."""

import ast  # Import ast for literal_eval
import json
import logging
import os
from dataclasses import dataclass  # Import dataclass
from typing import Any, Dict, List, Tuple

from google.adk.memory import BaseMemoryService
from google.adk.sessions import Session

logger = logging.getLogger(__name__)

# Define type for the internal session storage key
SessionKey = Tuple[str, str, str]  # (app_name, user_id, session_id)


# Define a simple response structure for load_memory/search_memory
@dataclass
class MemoryServiceResponse:
    memories: List[Dict[str, Any]]


class JsonFileMemoryService(BaseMemoryService):
    """
    An implementation of BaseMemoryService that stores sessions in memory
    and persists them to/loads them from a JSON file.

    The load_memory implementation is a basic substring search.
    """

    def __init__(self, filepath: str):
        """
        Initializes the service, loading existing data from the JSON file if it exists.

        Args:
            filepath: The path to the JSON file for persistence.
        """
        super().__init__()
        self.filepath = filepath
        # Store Session objects directly, keyed by the tuple
        self._sessions: Dict[SessionKey, Session] = {}
        self._load_from_json()

    def _get_session_key(self, session: Session) -> SessionKey:
        """Helper to generate the dictionary key for a session."""
        # Use the correct attribute name 'id' based on Session model
        return (session.app_name, session.user_id, session.id)

    def _load_from_json(self):
        """Loads session data from the JSON file into the internal dictionary."""
        if not os.path.exists(self.filepath):
            logger.info(f"Memory file not found at {self.filepath}. Starting with empty memory.")
            self._sessions = {}
            return

        logger.info(f"Loading memory from {self.filepath}...")
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                serialized_sessions: Dict[str, Dict[str, Any]] = json.load(f)

            # Store validated Session objects
            loaded_sessions: Dict[SessionKey, Session] = {}
            for key_str, session_data in serialized_sessions.items():
                try:
                    # Convert string key back to tuple using safe evaluation
                    key_tuple = ast.literal_eval(key_str)
                    if not isinstance(key_tuple, tuple) or len(key_tuple) != 3:
                        logger.warning(f"Invalid key format loaded from JSON: {key_str}. Skipping.")
                        continue
                    key: SessionKey = key_tuple  # Cast to type hint

                    # Recreate Session object from stored data
                    session = Session.model_validate(session_data)
                    # Store the Session object with the correct tuple key
                    loaded_sessions[key] = session
                except (ValueError, SyntaxError, TypeError) as e:
                    logger.warning(f"Failed to parse key {key_str}: {e}. Skipping.")
                except Exception as e:
                    logger.warning(f"Failed to validate session data for key {key_str}: {e}. Skipping.")
            self._sessions = loaded_sessions
            logger.info(f"Successfully loaded {len(self._sessions)} sessions from {self.filepath}.")

        except FileNotFoundError:
            logger.info(f"Memory file not found at {self.filepath}. Starting with empty memory.")
            self._sessions = {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.filepath}: {e}. Starting with empty memory.")
            self._sessions = {}
        except Exception as e:
            logger.error(f"Unexpected error loading memory from {self.filepath}: {e}. Starting with empty memory.")
            self._sessions = {}

    def _save_to_json(self):
        """Saves the current internal session dictionary to the JSON file."""
        logger.info(f"Saving memory ({len(self._sessions)} sessions) to {self.filepath}...")
        # Serialize Session objects using Pydantic's model_dump
        # Use a string representation of the tuple key for JSON compatibility
        serialized_sessions: Dict[str, Dict[str, Any]] = {str(key): session.model_dump(mode="json") for key, session in self._sessions.items()}

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(serialized_sessions, f, indent=4)
        except IOError as e:
            logger.error(f"Error saving memory to {self.filepath}: {e}")
        except TypeError as e:
            logger.error(f"Unexpected error saving memory to {self.filepath}: {e}")

    def add_session_to_memory(self, session: Session):
        """
        Adds a completed session to the memory store and persists to JSON.

        Args:
            session: The Session object to add.
        """
        # Add logging to see if runner calls this
        logger.info(f"JsonFileMemoryService.add_session_to_memory called by Runner? Session ID: {getattr(session, 'session_id', 'N/A')}")

        if not isinstance(session, Session):
            logger.warning(f"Attempted to add non-Session object to memory: {type(session)}")
            return

        key = self._get_session_key(session)
        logger.debug(f"Adding session with key {key} to memory.")
        self._sessions[key] = session  # Store the session object
        self._save_to_json()  # Persist after adding

    def load_memory(self, query: str, **kwargs) -> MemoryServiceResponse:
        """
        Retrieves relevant information based on a query.

        Args:
            query: The natural language query string.
            **kwargs: Additional keyword arguments (currently ignored).

        Returns:
            A MemoryServiceResponse containing a list of dictionaries,
            each representing a relevant message's session data.
        """
        logger.info(f"Loading memory with query: '{query}'")
        results: List[Dict[str, Any]] = []
        query_lower = query.lower()

        for session in self._sessions.values():  # Iterate over Session objects
            session_matched = False
            # Access history directly from the Session object
            if session.history:
                for message in session.history:
                    # Access parts directly from the Content object in history
                    message_text = ""
                    if message.parts:
                        message_text = "".join([part.text for part in message.parts if hasattr(part, "text") and part.text is not None]).lower()

                    if query_lower in message_text:
                        session_matched = True
                        break  # Found a match in this session's history

            if session_matched:
                # Add relevant session data (e.g., the whole session dump)
                results.append(session.model_dump(mode="json"))

        logger.info(f"Found {len(results)} relevant session(s) for query: '{query}'")
        # Return as an instance of the dataclass
        return MemoryServiceResponse(memories=results)

    # Implementing the abstract method required by BaseMemoryService
    # Type hint reflects Base class, but implementation delegates to load_memory which returns MemoryServiceResponse
    def search_memory(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Searches the stored sessions for relevant information based on a query.
        This method fulfills the abstract requirement from BaseMemoryService.
        """
        # For this implementation, search_memory simply delegates to load_memory.
        # A more sophisticated implementation might differ.
        logger.debug(f"search_memory called, delegating to load_memory for query: '{query}'")
        response = self.load_memory(query, **kwargs)
        # Base class expects List[Dict], extract from dataclass
        return response.memories

    def get_memory_service_info(self) -> Dict[str, Any]:
        """
        Returns information about this memory service.
        """
        return {
            "service_type": "JsonFileMemoryService",
            "description": "Stores session memory in a local JSON file.",
            "filepath": self.filepath,
            "current_session_count": len(self._sessions),
            "capabilities": {"persistence": True, "search_type": "basic_substring"},
        }
