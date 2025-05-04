"""Custom MemoryService implementation that persists sessions to a JSON file."""

import ast  # Import ast for literal_eval
import json
import logging
import os

# import uuid # No longer needed for memory IDs
from dataclasses import dataclass, field  # Add field
from typing import Any, Dict, List, Optional, Tuple

from google.adk.memory import BaseMemoryService
from google.adk.sessions import Session

# Remove config import - filepath is passed in
# from code_agent.config import get_config

logger = logging.getLogger(__name__)

# Define type for the internal session storage key
SessionKey = Tuple[str, str, str]  # (app_name, user_id, session_id)


# Define response structure for search_memory
@dataclass
class MemoryServiceResponse:  # Although search_memory returns List[Dict], load_memory might return this?
    memories: List[Dict[str, Any]]


# Define structure for a single fact/observation
@dataclass
class MemoryFact:
    entity_name: str
    content: Dict[str, Any]  # Flexible content storage
    # Add other potential fields like entity_type, relation_type if needed later


# Define the structure of the main memory store
@dataclass
class JsonMemoryStore:
    sessions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # str(SessionKey) -> Session dict
    facts: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # session_id -> List[Observation dicts]


class JsonFileMemoryService(BaseMemoryService):
    """
    An implementation of BaseMemoryService that stores session transcripts
    and discrete memory facts (observations) in a single JSON file.

    Search memory iterates through saved session histories.
    Search nodes iterates through saved facts for a given session.
    Adding session memory saves the specific session transcript.
    Adding observations saves discrete facts associated with a session.
    """

    def __init__(self, filepath: str):
        """
        Initializes the service, loading existing data from the JSON file.

        Args:
            filepath: The path to the JSON file for persistence.
        """
        super().__init__()
        self.filepath = filepath
        # Initialize with the dataclass structure
        self._memory_store = JsonMemoryStore()
        self._load_from_json()

    # Helper to generate string key for JSON
    def _get_str_key(self, app_name: str, user_id: str, session_id: str) -> str:
        return str((app_name, user_id, session_id))

    # Helper to parse string key back to tuple
    def _parse_str_key(self, key_str: str) -> Optional[SessionKey]:
        try:
            key_tuple = ast.literal_eval(key_str)
            if isinstance(key_tuple, tuple) and len(key_tuple) == 3:
                return key_tuple
            logger.warning(f"Invalid key format loaded from JSON: {key_str}.")
        except (ValueError, SyntaxError, TypeError) as e:
            logger.warning(f"Failed to parse key {key_str}: {e}.")
        return None

    def _load_from_json(self):
        """Loads the memory store from the JSON file."""
        if not os.path.exists(self.filepath):
            logger.info(f"Memory file not found at {self.filepath}. Starting with empty store.")
            self._memory_store = JsonMemoryStore()
            return

        logger.info(f"Loading memory store from {self.filepath}...")
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if loaded data is the new structure or old structure
            if isinstance(data, dict) and "sessions" in data and "facts" in data:
                # New structure
                loaded_sessions = data.get("sessions", {})
                loaded_facts = data.get("facts", {})

                # Basic validation (ensure sessions maps str->dict, facts maps str->list)
                valid_sessions = {}
                for k, v in loaded_sessions.items():
                    # Validate key format AND value structure
                    parsed_key = self._parse_str_key(k)
                    if parsed_key and isinstance(v, dict) and all(key in v for key in ["app_name", "user_id", "id", "events"]):
                        valid_sessions[k] = v
                    else:
                        logger.warning(f"Skipping session with invalid key '{k}' or missing essential fields.")

                valid_facts = {k: v for k, v in loaded_facts.items() if isinstance(k, str) and isinstance(v, list)}

                self._memory_store = JsonMemoryStore(sessions=valid_sessions, facts=valid_facts)
                logger.info(f"Successfully loaded {len(valid_sessions)} sessions and fact sets for {len(valid_facts)} sessions from {self.filepath}.")

            elif isinstance(data, dict):  # Assume old structure (dict of sessions keyed by str(SessionKey))
                logger.warning(f"Old memory file format detected at {self.filepath}. Migrating to new structure.")
                loaded_sessions = {}
                for key_str, session_data in data.items():
                    # Validate key format AND value structure during migration
                    parsed_key = self._parse_str_key(key_str)  # Try parsing old key
                    if parsed_key and isinstance(session_data, dict) and all(key in session_data for key in ["app_name", "user_id", "id", "events"]):
                        loaded_sessions[key_str] = session_data
                    else:
                        logger.warning(f"Skipping migrating session with invalid key '{key_str}' or missing essential fields.")

                self._memory_store = JsonMemoryStore(sessions=loaded_sessions, facts={})
                logger.info(f"Successfully migrated {len(loaded_sessions)} sessions from old format. Initializing empty facts.")
                # Optionally save immediately to persist the migration
                self._save_to_json()

            else:  # Handle unexpected format
                logger.error(f"Unrecognized format in memory file {self.filepath}. Starting with empty store.")
                self._memory_store = JsonMemoryStore()

        except FileNotFoundError:  # Should be caught by os.path.exists, but good practice
            logger.info(f"Memory file not found at {self.filepath}. Starting with empty store.")
            self._memory_store = JsonMemoryStore()
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.filepath}: {e}. Starting with empty store.")
            self._memory_store = JsonMemoryStore()
        except Exception as e:
            logger.error(f"Unexpected error loading memory from {self.filepath}: {e}. Starting with empty store.", exc_info=True)
            self._memory_store = JsonMemoryStore()

    def _save_to_json(self):
        """Saves the current internal memory store to the JSON file."""
        session_count = len(self._memory_store.sessions)
        fact_session_count = len(self._memory_store.facts)
        logger.info(f"Saving memory store ({session_count} sessions, facts for {fact_session_count} sessions) to {self.filepath}...")

        # Prepare data for serialization (already in JSON-compatible types mostly)
        data_to_save = {"sessions": self._memory_store.sessions, "facts": self._memory_store.facts}

        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"Successfully saved memory store to {self.filepath}.")
        except IOError as e:
            logger.error(f"Error saving memory to {self.filepath}: {e}")
        except TypeError as e:
            logger.error(f"Serialization error saving memory: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error saving memory: {e}", exc_info=True)

    # --- BaseMemoryService Implementation --- #

    def add_session_to_memory(self, session: Session):
        """Adds/updates a completed session transcript in the memory store and persists."""
        logger.info(f"*** add_session_to_memory CALLED for Session ID: {getattr(session, 'id', 'N/A')} ***")
        if not isinstance(session, Session):
            logger.warning(f"Attempted to add non-Session object to memory: {type(session)}")
            return

        # Use session attributes directly for the key, then stringify
        session_key: SessionKey = (session.app_name, session.user_id, session.id)
        session_key_str = str(session_key)  # Use string key for JSON compatibility

        logger.debug(f"Adding/updating session {session.id} (key: {session_key_str}) in memory store.")
        # Store the dictionary representation of the session under the 'sessions' key
        self._memory_store.sessions[session_key_str] = session.model_dump(mode="json")

        # Persist the entire store after adding/updating
        self._save_to_json()

    def search_memory(self, query: str, **kwargs) -> MemoryServiceResponse:  # Keep returning MemoryServiceResponse
        """
        Searches the message history of stored sessions for the query.
        Returns a MemoryServiceResponse containing matching session dictionaries.
        """
        logger.info(f"Searching session transcript memory for query: '{query}'")
        results: List[Dict[str, Any]] = []
        query_lower = query.lower()

        # Search within the 'sessions' part of the store
        for _, session_data in self._memory_store.sessions.items():
            # Access history within the stored session dictionary
            events = session_data.get("events", [])
            if events and isinstance(events, list):
                for event_dict in events:
                    # Reconstruct message text from parts dicts nested within content
                    content = event_dict.get("content")
                    if content and isinstance(content, dict):
                        parts = content.get("parts", [])
                        message_text = "".join([part.get("text", "") for part in parts if isinstance(part, dict)]).lower()

                        if query_lower in message_text:
                            # Add the dict representation of the whole session where match was found
                            results.append(session_data)
                            break  # Found match in this session, move to next session

        logger.info(f"Found {len(results)} relevant session transcript(s) containing query: '{query}'")
        # Log the structure of the found sessions for debugging
        logger.debug(f"Transcript search found session data: {json.dumps(results, indent=2)}")

        # Return the dataclass wrapper as expected by downstream consumers
        return MemoryServiceResponse(memories=results)

    # --- New methods for discrete fact memory ---

    def add_observations(self, session_id: str, observations: List[Dict[str, Any]], **kwargs):
        """Adds discrete facts (observations) associated with a session_id."""
        logger.info(f"*** add_observations CALLED for Session ID: {session_id} with {len(observations)} observations ***")
        if not session_id or not isinstance(session_id, str):
            logger.error("add_observations requires a valid session_id (string).")
            return
        if not isinstance(observations, list):
            logger.error("add_observations requires observations to be a list.")
            return

        logger.debug(f"Adding observations for session {session_id}: {observations}")

        # Ensure the list for this session_id exists in the facts dictionary
        if session_id not in self._memory_store.facts:
            self._memory_store.facts[session_id] = []

        # Append the new observations (assuming they are already dicts)
        self._memory_store.facts[session_id].extend(observations)

        # Persist the entire store
        self._save_to_json()

    def search_nodes(self, session_id: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Searches discrete facts (observations) stored for a specific session_id."""
        logger.info(f"*** search_nodes CALLED for Session ID: {session_id} with query: '{query}' ***")
        if not session_id or not isinstance(session_id, str):
            logger.error("search_nodes requires a valid session_id (string). Returning empty list.")
            return []

        query_lower = query.lower().strip()
        session_facts = self._memory_store.facts.get(session_id, [])

        # Log all available facts for debugging
        logger.debug(f"All facts for session {session_id}: {json.dumps(session_facts, indent=2)}")

        results: List[Dict[str, Any]] = []

        logger.debug(f"Searching {len(session_facts)} facts for session {session_id} with query '{query}'")

        # If no facts found, return empty list
        if not session_facts:
            logger.info(f"No facts found for session {session_id}")
            return []

        # Break query into keywords and bigrams for better matching
        query_words = query_lower.split()
        query_keywords = set(query_words)
        query_bigrams = set()
        for i in range(len(query_words) - 1):
            query_bigrams.add(f"{query_words[i]} {query_words[i+1]}")

        # Common question patterns for information retrieval
        question_starters = ["what", "tell me", "do i", "am i", "can you"]
        is_question = any(query_lower.startswith(starter) for starter in question_starters)

        # Score each fact for relevance to the query
        scored_facts = []

        for fact in session_facts:
            score = 0
            entity_name = fact.get("entity", "").lower()
            fact_content = fact.get("content", "").lower()
            combined_text = f"{entity_name} {fact_content}"

            logger.debug(f"Evaluating fact - entity: '{entity_name}', content: '{fact_content}'")

            # Direct match with complete query - highest score
            if query_lower in combined_text:
                score += 10
                logger.debug("  Direct match with complete query: +10")

            # Check for exact keyword matches
            for keyword in query_keywords:
                if keyword in combined_text:
                    score += 2
                    logger.debug(f"  Keyword match '{keyword}': +2")

                    # Bonus points for keywords in entity name (more specific)
                    if keyword in entity_name:
                        score += 1
                        logger.debug(f"  Keyword in entity name '{keyword}': +1")

            # Check for bigram matches (phrases)
            for bigram in query_bigrams:
                if bigram in combined_text:
                    score += 3
                    logger.debug(f"  Bigram match '{bigram}': +3")

            # Special handling for questions about preferences, work, etc.
            if is_question:
                # Question about what user likes/preferences
                if any(term in query_lower for term in ["like", "favorite", "prefer", "enjoy"]):
                    if any(term in combined_text for term in ["like", "favorite", "prefer", "enjoy"]):
                        score += 4
                        logger.debug("  Preference question match: +4")

                # Question about what user is working on
                if any(term in query_lower for term in ["working on", "project", "task"]):
                    if any(term in combined_text for term in ["working on", "project", "task", "developing"]):
                        score += 4
                        logger.debug("  Project/work question match: +4")

                # Question about user's activities or hobbies
                if any(term in query_lower for term in ["do", "activity", "hobby", "interest"]):
                    if any(term in combined_text for term in ["do", "activity", "hobby", "interest"]):
                        score += 4
                        logger.debug("  Activity/hobby question match: +4")

                # Questions about specific domains with more specific matching
                common_domains = {
                    "food": ["food", "eat", "meal", "dish", "cuisine", "pizza", "pasta"],
                    "drink": ["drink", "beverage", "coffee", "tea", "water"],
                    "color": ["color", "red", "blue", "green", "yellow"],
                    "project": ["project", "app", "application", "software", "program", "system", "database"],
                    "hobby": ["hobby", "activity", "sport", "game", "read", "hiking"],
                    "travel": ["travel", "trip", "vacation", "visit", "place"],
                    "technology": ["tech", "tool", "software", "program", "app", "language", "framework", "library"],
                    "database": ["database", "db", "sql", "nosql", "data"],
                }

                for domain, terms in common_domains.items():
                    if any(term in query_lower for term in terms):
                        if any(term in combined_text for term in terms):
                            score += 5
                            logger.debug(f"  Domain '{domain}' match: +5")

                # Special case for specific project types (like "database project")
                for project_type in ["database", "web", "mobile", "desktop", "ai", "ml"]:
                    project_phrase = f"{project_type} project"
                    if project_phrase in query_lower and (project_phrase in combined_text or (project_type in combined_text and "project" in combined_text)):
                        score += 6
                        logger.debug(f"  Specific project type '{project_phrase}' match: +6")

            # Add to scored list if there's any match at all
            if score > 0:
                scored_facts.append((score, fact))
                logger.debug(f"  Total score for fact: {score}")
            else:
                logger.debug("  No match found for this fact")

        # Sort by score descending and extract just the facts
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        results = [fact for _, fact in scored_facts]

        # Log the results
        if results:
            logger.info(f"Found {len(results)} relevant fact(s) for session {session_id} matching query: '{query}'")
            logger.debug(f"Top matched fact: {results[0]}")
        else:
            logger.info(f"No facts found for session {session_id} matching query: '{query}'")

        return results

    # --- End new methods ---

    def get_memory_service_info(self) -> Dict[str, Any]:
        """
        Returns information about this memory service.
        """
        session_count = len(self._memory_store.sessions)
        fact_session_count = len(self._memory_store.facts)
        return {
            "service_type": "JsonFileMemoryService",
            "description": "Stores session transcripts and discrete facts in a local JSON file.",
            "filepath": self.filepath,
            "current_session_count": session_count,
            "sessions_with_facts_count": fact_session_count,
            "capabilities": {
                "persistence": True,
                "search_memory": "basic_substring (session history transcripts)",
                "add_observations": True,
                "search_nodes": "basic_substring (discrete facts per session)",
            },
        }

    # load_memory is deprecated/internal? search_memory is the BaseMemoryService method
    # def load_memory(self, query: str, **kwargs) -> MemoryServiceResponse: ...
