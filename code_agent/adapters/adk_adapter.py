"""
ADK CLI Adapter - Provides compatibility with Google ADK CLI functionality.

This module adapts our Typer-based CLI to work with ADK CLI patterns and components.
It handles agent loading, session management, and other ADK-specific functionality.
"""

import importlib
import logging
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

# Try to import ADK components - these will be optional
try:
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.sessions.session import Session

    # Try to import Runner from main module (ADK 0.4.0 structure)
    try:
        from google.adk import Runner

        runner_available = True
    except ImportError:
        # Fallback to older structure
        try:
            from google.adk.runners import Runner

            runner_available = True
        except ImportError:
            Runner = None
            runner_available = False

    # Try different module paths for Content/Part (these classes may not be directly importable in ADK 0.4.0)
    try:
        from google.adk.genai.types import Content, Part
    except ImportError:
        try:
            from google.adk.models.types import Content, Part
        except ImportError:
            # Fallback to basic implementations if needed
            from dataclasses import dataclass

            @dataclass
            class Part:
                text: Optional[str] = None

            @dataclass
            class Content:
                role: str = "user"
                parts: Optional[List[Part]] = None

                def __post_init__(self):
                    if self.parts is None:
                        self.parts = []

    # Memory service might be optional in some ADK versions
    try:
        from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

        memory_service_available = True
    except ImportError:
        InMemoryMemoryService = None
        memory_service_available = False

    ADK_AVAILABLE = True

except ImportError as e:
    # ADK is not available, set all components to None
    InMemoryArtifactService = None
    InMemorySessionService = None
    InMemoryMemoryService = None
    Content = None
    Part = None
    Session = None
    Runner = None
    ADK_AVAILABLE = False
    memory_service_available = False
    runner_available = False
    logging.debug(f"ADK not available: {e}")

from code_agent.config import get_config

logger = logging.getLogger(__name__)


class AdkCliAdapter:
    """
    Adapter class for ADK CLI functionality.

    This class provides methods that mirror ADK CLI functionality,
    but implemented for our Typer-based CLI structure.
    """

    def __init__(self):
        """Initialize the adapter."""
        self.config = get_config()
        self.console = Console()

        # Services
        self.artifact_service = self._create_artifact_service()
        self.session_service = self._create_session_service()
        self.memory_service = self._create_memory_service() if memory_service_available else None

        # Cache for loaded agents and runners
        self._agent_cache = {}
        self._runner_cache = {}

    def _create_artifact_service(self) -> Any:
        """Create an artifact service instance."""
        if not ADK_AVAILABLE:
            logger.warning("ADK not available, can't create artifact service")
            return None

        return InMemoryArtifactService()

    def _create_session_service(self) -> Any:
        """Create a session service instance."""
        if not ADK_AVAILABLE:
            logger.warning("ADK not available, can't create session service")
            return None

        return InMemorySessionService()

    def _create_memory_service(self) -> Any:
        """Create a memory service instance."""
        if not memory_service_available:
            logger.warning("ADK memory service not available")
            return None

        return InMemoryMemoryService()

    def load_dotenv_for_agent(self, agent_folder_name: str, agent_parent_dir: str) -> None:
        """
        Load environment variables from .env file in the agent directory.

        Args:
            agent_folder_name: Name of the agent folder
            agent_parent_dir: Parent directory containing the agent folder
        """
        try:
            from dotenv import load_dotenv

            env_path = Path(agent_parent_dir) / agent_folder_name / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                logger.debug(f"Loaded environment from {env_path}")
            else:
                logger.debug(f"No .env file found at {env_path}")

        except ImportError:
            logger.warning("python-dotenv not available, can't load .env file")

    def load_agent(self, agent_path: Path) -> Optional[Any]:
        """
        Load an agent from a directory or file path.

        Args:
            agent_path: Path to the agent directory or file

        Returns:
            The loaded agent object or None if loading fails
        """
        if not agent_path:
            logger.error("No agent path provided")
            return None

        # Resolve the agent path
        agent_path = Path(agent_path).resolve()
        cache_key = str(agent_path)

        # Check cache first
        if cache_key in self._agent_cache:
            return self._agent_cache[cache_key]

        try:
            # Determine if path is a directory or file
            if agent_path.is_dir():
                agent_parent_dir = str(agent_path.parent)
                agent_folder_name = agent_path.name
                agent_module_path = agent_path / "agent.py"
            else:
                agent_parent_dir = str(agent_path.parent.parent)
                agent_folder_name = agent_path.parent.name
                agent_module_path = agent_path

            # Add parent directory to sys.path if not already there
            if agent_parent_dir not in sys.path:
                sys.path.append(agent_parent_dir)

            # Load environment variables from .env file
            self.load_dotenv_for_agent(agent_folder_name, agent_parent_dir)

            # Try to import the agent module
            if agent_path.is_dir():
                # Import as a package
                try:
                    agent_module = importlib.import_module(agent_folder_name)
                    root_agent = getattr(agent_module.agent, "root_agent", None)
                except (ImportError, AttributeError) as e:
                    logger.error(f"Failed to import agent as package: {e}")

                    # Try alternative import approach
                    agent_module_name = f"agent_{uuid.uuid4().hex[:8]}"
                    spec = importlib.util.spec_from_file_location(agent_module_name, agent_module_path)
                    if not spec or not spec.loader:
                        logger.error(f"Could not load spec for {agent_module_path}")
                        return None

                    agent_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(agent_module)
                    root_agent = getattr(agent_module, "root_agent", None)
            else:
                # Import as a file
                agent_module_name = f"agent_{uuid.uuid4().hex[:8]}"
                spec = importlib.util.spec_from_file_location(agent_module_name, agent_module_path)
                if not spec or not spec.loader:
                    logger.error(f"Could not load spec for {agent_module_path}")
                    return None

                agent_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(agent_module)
                root_agent = getattr(agent_module, "root_agent", None)

            # If root_agent not found, look for other common patterns
            if not root_agent:
                for attr_name in ["agent", "assistant", "llm_agent", "my_agent"]:
                    if hasattr(agent_module, attr_name):
                        root_agent = getattr(agent_module, attr_name)
                        break

            # Cache and return the agent
            if root_agent:
                self._agent_cache[cache_key] = root_agent
                return root_agent
            else:
                logger.error(f"No agent found in {agent_module_path}")
                return None

        except Exception as e:
            logger.exception(f"Error loading agent from {agent_path}: {e}")
            return None

    def get_runner(self, agent: Any, app_name: str) -> Optional[Any]:
        """
        Get a runner for the given agent.

        Args:
            agent: The agent object
            app_name: The application name

        Returns:
            A runner instance or None if not available
        """
        if not runner_available or not agent:
            return None

        cache_key = f"{id(agent)}:{app_name}"

        # Check cache first
        if cache_key in self._runner_cache:
            return self._runner_cache[cache_key]

        try:
            runner = Runner(
                app_name=app_name,
                agent=agent,
                artifact_service=self.artifact_service,
                session_service=self.session_service,
                memory_service=self.memory_service if memory_service_available else None,
            )

            self._runner_cache[cache_key] = runner
            return runner

        except Exception as e:
            logger.exception(f"Error creating runner: {e}")
            return None

    def create_session(self, app_name: str, user_id: str, state: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Create a new session.

        Args:
            app_name: The application name
            user_id: The user ID
            state: Optional initial state

        Returns:
            A session instance or None if not available
        """
        if not self.session_service:
            logger.error("Session service not available")
            return None

        try:
            if not state:
                state = {}

            # Add timestamp to state
            state["_time"] = datetime.now()

            # Create and return session
            return self.session_service.create_session(app_name=app_name, user_id=user_id, state=state)

        except Exception as e:
            logger.exception(f"Error creating session: {e}")
            return None

    def load_session_from_file(self, file_path: Path) -> Optional[Any]:
        """
        Load a session from a file.

        Args:
            file_path: Path to the session file

        Returns:
            A session instance or None if loading fails
        """
        if not ADK_AVAILABLE or not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                session_json = f.read()
                return Session.model_validate_json(session_json)

        except Exception as e:
            logger.exception(f"Error loading session from {file_path}: {e}")
            return None

    def save_session_to_file(self, session: Any, file_path: Path) -> bool:
        """
        Save a session to a file.

        Args:
            session: The session to save
            file_path: Path to save the session to

        Returns:
            True if successful, False otherwise
        """
        if not ADK_AVAILABLE or not session:
            return False

        try:
            # Create parent directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(session.model_dump_json(indent=2, exclude_none=True))

            return True

        except Exception as e:
            logger.exception(f"Error saving session to {file_path}: {e}")
            return False

    def create_content(self, message: str, role: str = "user") -> Any:
        """
        Create a content object from a message.

        Args:
            message: The message text
            role: The role (user, assistant, system)

        Returns:
            A content object or None if not available
        """
        if not ADK_AVAILABLE:
            return None

        try:
            return Content(role=role, parts=[Part(text=message)])

        except Exception as e:
            logger.exception(f"Error creating content: {e}")
            return None

    @contextmanager
    def add_to_sys_path(self, path: str):
        """
        Temporarily add a path to sys.path.

        Args:
            path: The path to add
        """
        path_added = False

        try:
            if path not in sys.path:
                sys.path.append(path)
                path_added = True

            yield

        finally:
            if path_added:
                sys.path.remove(path)


# Create a singleton instance
adk_adapter = AdkCliAdapter()
