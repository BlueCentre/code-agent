import json
import logging
from pathlib import Path
from typing import Optional

from google.adk.sessions import Session  # Keep Session import

# No longer need SessionService import
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# Restore inheritance from InMemorySessionService
class FileSystemSessionService(InMemorySessionService):
    """
    An implementation of SessionService that persists sessions to the filesystem
    by extending InMemorySessionService and loading from disk on cache miss.
    """

    def __init__(self, sessions_dir: str):
        """Initializes the service, ensuring the session directory exists.

        Args:
            sessions_dir: The path to the directory where sessions should be stored.
        """
        super().__init__()  # Call parent init to ensure _sessions exists
        # self._memory_cache = InMemorySessionService() # No longer needed

        if not sessions_dir:
            logger.error("sessions_dir argument cannot be empty.")
            raise ValueError("sessions_dir argument cannot be empty.")

        self.sessions_dir = Path(sessions_dir)  # Store as Path object

        try:
            # No longer need get_config() here
            # cfg = get_config() # Assumes config is already initialized
            # self.sessions_dir = cfg.sessions_dir
            # if not self.sessions_dir:
            #     logger.error("Session directory is not configured.")
            #     raise ValueError("Session directory not configured.")

            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"FileSystemSessionService initialized. Sessions dir: {self.sessions_dir}")

        except OSError as e:
            logger.exception(f"Error creating session directory {self.sessions_dir}: {e}")
            raise RuntimeError(f"Failed to initialize FileSystemSessionService: Could not create directory {self.sessions_dir}.") from e
        except Exception as e:
            logger.exception(f"Error initializing FileSystemSessionService: {e}")
            raise RuntimeError("Failed to initialize FileSystemSessionService due to an unexpected error.") from e

    # Override create_session to ensure consistency if needed, or rely on parent?
    # For now, let's assume parent create_session is sufficient if we load correctly in get_session
    # def create_session(self, app_name: str, user_id: str) -> Session:
    #     logger.debug(f"Calling super().create_session ({app_name=}, {user_id=})")
    #     return super().create_session(app_name=app_name, user_id=user_id)

    # Remove update_session as we can't guarantee parent has it, and we update cache directly
    # def update_session(self, session: Session) -> None:
    #     logger.debug(f"Calling super().update_session for {session.id}")
    #     super().update_session(session=session)

    def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        """
        Retrieves a session, first checking in-memory cache via super(), then loading from
        the filesystem if necessary and adding to the cache.
        """
        # 1. Check in-memory cache first using super() with correct keywords
        session = super().get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        if session:
            logger.debug(f"Session {session_id} found in memory cache via super().get_session.")
            return session

        # 2. If not in memory, try loading from filesystem
        if not self.sessions_dir:
            logger.error("Cannot load session from file: sessions_dir not set.")
            return None

        session_file_path = self.sessions_dir / f"{session_id}.session.json"
        logger.debug(f"Session {session_id} not in memory, attempting load from {session_file_path}")

        if not session_file_path.is_file():
            logger.debug(f"Session file not found: {session_file_path}")
            return None

        # 3. Load from file if it exists
        try:
            json_content = session_file_path.read_text()
            loaded_session = Session.model_validate_json(json_content)
            logger.info(f"Successfully loaded session {session_id} from {session_file_path}")

            # 4. Return the loaded session directly. Do not attempt to add it back to the
            #    parent's in-memory cache to avoid relying on internal implementation details.
            return loaded_session

        except OSError as e:
            logger.error(f"Error reading session file {session_file_path}: {e}", exc_info=True)
            return None
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Error parsing session file {session_file_path}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred loading session {session_id} from file: {e}", exc_info=True)
            return None

    # Note: We are not overriding update_session or create_session here.
    # Session *saving* will still rely on the logic in `run_command` which calls
    # get_session again after execution and writes the file.
    # Session *creation* still happens in memory via the parent class.
    # If a session is created and then saved, the next run will load it via get_session.
