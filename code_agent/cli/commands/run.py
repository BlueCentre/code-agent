"""
This module contains the commands for the run sub-app.
"""

import importlib.util
import json
import logging
import sys
import traceback
import warnings
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

# Local application imports
from code_agent.config import get_config, initialize_config

# Import ADK components if available
try:
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

    # Try importing the memory service
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    ADK_INSTALLED = True
    # Placeholder is no longer needed here if import succeeds
    # InMemoryMemoryService = None # type: ignore
except ImportError:
    # Set all to None if ANY import fails
    InMemoryArtifactService = None  # type: ignore
    InMemorySessionService = None  # type: ignore
    InMemoryMemoryService = None  # type: ignore # Keep this for the check below
    ADK_INSTALLED = False

# Import our custom session service
# from code_agent.services.memory_service import FileSystemMemoryService # Old import
# from code_agent.services.memory_service import MemoryServiceWrapper # Not the wrapper
from code_agent.adk.json_memory_service import JsonFileMemoryService  # Import the correct one

# Import helpers from utils
from code_agent.cli.utils import (
    _resolve_agent_path_str,
    operation_complete,
    operation_error,
    operation_warning,
    run_cli,
    setup_logging,
    thinking_indicator,
)
from code_agent.services.session_service import FileSystemSessionService

logger = logging.getLogger(__name__)  # Define logger at module level

# --- Constants for Typer Arguments/Options ---
AGENT_PATH_DEFAULT = None  # Can't use Path() here directly
AGENT_PATH_HELP = (
    "Path to the Python module containing the agent definition (e.g.,"
    " 'my_agent/' or 'my_agent/agent.py'). If not provided, uses the default"
    " agent path from config."
)
INSTRUCTION_HELP = "The initial instruction or query for the agent."
SESSION_ID_HELP = "The session ID to continue or view history for."
LEVEL_HELP = "Verbosity level to set (0-3, QUIET, NORMAL, VERBOSE, DEBUG)."


# Create module-level singletons for argument types to avoid B008
INSTRUCTION_ARG = typer.Argument(help=INSTRUCTION_HELP)
# Use Optional[Path] and handle None/existence check in the command
AGENT_PATH_ARG = typer.Argument(
    help=AGENT_PATH_HELP,
    exists=False,
    file_okay=True,
    dir_okay=True,
    readable=True,
)


# --- Run Command ---


# Define the run command function separately
# We will register it with the main app in main.py
def run_command(
    instruction: Annotated[
        str,
        INSTRUCTION_ARG,
    ],
    # Correct the type hint for agent_path and default value assignment
    agent_path: Annotated[
        Optional[Path],  # Make Path optional
        # Remove default from Argument, it will be set via function default
        AGENT_PATH_ARG,
    ] = AGENT_PATH_DEFAULT,  # Assign default value here using =
    session_id: Annotated[
        Optional[str],
        typer.Option("--session-id", "-s", help=SESSION_ID_HELP),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Continue conversation in interactive mode after initial query."),
    ] = False,
    show_timestamps: Annotated[
        bool,
        typer.Option("--timestamps", "-t", help="Show timestamps for each message"),
    ] = False,
    log_level: Annotated[
        Optional[str],
        typer.Option(
            "--log-level",
            "-l",
            help=LEVEL_HELP + " Overrides config/verbose flag.",  # Clarify override
        ),
    ] = None,
    provider: Annotated[
        Optional[str],
        typer.Option(
            "--provider",
            "-p",
            help="LLM provider to use (e.g., openai, ai_studio, groq, anthropic, ollama). Overrides config file.",
        ),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            "-m",
            help="LLM model to use (e.g., gemini-1.5-flash-latest, gpt-4o, claude-3-opus, etc.). Overrides config file.",
        ),
    ] = None,
    temperature: Annotated[
        Optional[float],
        typer.Option(
            "--temperature",
            help="Temperature setting for the LLM (0.0-1.0). Overrides config file.",
        ),
    ] = None,
    max_tokens: Annotated[
        Optional[int],
        typer.Option(
            "--max-tokens",
            help="Maximum number of tokens to generate. Overrides config file.",
        ),
    ] = None,
    save_session_cli: Annotated[
        bool,
        typer.Option("--save-session", help="Save the conversation session to a file."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output (sets logging to INFO/verbosity 2 unless --log-level is higher).",
            is_flag=True,  # Make it a flag
        ),
    ] = False,
):
    """
    Run a Code Agent powered by ADK.
    """
    console = Console()

    try:
        # --- Configuration and Logging Setup ---
        # Suppress warnings during initialization
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Initialize config with CLI overrides
            # Pass temperature and max_tokens as well
            initialize_config(
                cli_provider=provider,
                cli_model=model,
                cli_log_level=log_level,
                cli_verbose=verbose,
                force_reinit=True,
                validate=True,  # Validate the final effective config
            )
            cfg = get_config()  # Get the final effective config

        # Setup logging based on the *final* configuration from initialize_config
        setup_logging(verbosity_level=cfg.verbosity)
        logging.debug(f"Logging setup complete in 'run' command. Level: {logging.getLevelName(logging.getLogger().getEffectiveLevel())}")

        # --- ADK Check ---
        if not ADK_INSTALLED:
            console.print("[bold red]Error:[/bold red] Google ADK is required for the 'run' command but is not installed.")
            console.print("Please install it using: [yellow]uv add google-adk[/yellow]")
            raise typer.Exit(code=1)
        if InMemorySessionService is None:  # Check again just in case
            console.print("[bold red]Error:[/bold red] Failed to import ADK's InMemorySessionService.")
            raise typer.Exit(code=1)

        # --- Agent Path Resolution ---
        resolved_agent_path_str = _resolve_agent_path_str(agent_path, cfg)
        if not resolved_agent_path_str:
            # Error message printed by _resolve_agent_path_str
            raise typer.Exit(code=1)
        resolved_agent_path = Path(resolved_agent_path_str)  # Path object for loading

        # --- Agent Loading ---
        console.print(f"[bold cyan]Running agent[/bold cyan] with instruction: '[italic]{instruction}[/italic]'")
        # Print provider info using the correct config attribute
        # Check if provider attribute exists, otherwise fallback might be needed (e.g., default_provider)
        provider_display = getattr(cfg, "provider", cfg.default_provider)  # Attempt to get effective provider, fallback to default
        console.print(f"[dim]Provider: {provider_display}[/dim]")  # Use the determined provider

        agent_to_run = None
        try:
            with thinking_indicator(console, "Loading agent..."):
                # Dynamically load the agent module
                spec = None
                agent_module = None

                if resolved_agent_path.is_file() and resolved_agent_path.suffix == ".py":
                    module_name = resolved_agent_path.stem
                    # Use importlib.util.spec_from_file_location for robust loading
                    spec = importlib.util.spec_from_file_location(module_name, resolved_agent_path)
                    if spec and spec.loader:
                        agent_module = importlib.util.module_from_spec(spec)
                        # Add module to sys.modules BEFORE executing
                        sys.modules[module_name] = agent_module
                        spec.loader.exec_module(agent_module)
                    else:
                        raise ImportError(f"Could not create module spec for {resolved_agent_path}")

                elif resolved_agent_path.is_dir():
                    # Assume it's a package directory
                    # Add parent directory to path to allow direct import
                    parent_dir = str(resolved_agent_path.parent)
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)  # Insert at beginning

                    module_name = resolved_agent_path.name
                    try:
                        # Attempt to import the directory as a package
                        agent_module = importlib.import_module(module_name)
                    except ImportError as e:
                        # Re-raise the original ImportError but chain the context
                        raise ImportError(f"Could not import agent package '{module_name}' from {resolved_agent_path}: {e}") from e
                    finally:
                        # Clean up sys.path if needed, though generally safe to leave
                        # if parent_dir in sys.path and sys.path[0] == parent_dir:
                        #     sys.path.pop(0)
                        pass
                else:
                    raise ImportError(f"Agent path is neither a Python file nor a directory: {resolved_agent_path}")

                # --- Get Agent Instance (Revert to previous working logic) ---
                if hasattr(agent_module, "root_agent"):
                    agent_to_run = agent_module.root_agent
                    operation_warning(console, f"Found 'agent.root_agent' structure in {resolved_agent_path.name}.")
                elif hasattr(agent_module, "agent"):
                    potential_agent = agent_module.agent
                    # Previous check: Look for expected attributes like name/tools
                    if hasattr(potential_agent, "name") and hasattr(potential_agent, "tools"):
                        agent_to_run = potential_agent
                        operation_warning(console, f"Found top-level 'agent' variable in {resolved_agent_path.name} and using it.")
                        operation_warning(console, "Consider renaming to 'root_agent' for clarity.")
                    # Check if agent_module.agent contains root_agent (less common)
                    elif hasattr(potential_agent, "root_agent"):
                        agent_to_run = potential_agent.root_agent
                        operation_warning(console, f"Found 'agent.root_agent' structure in {resolved_agent_path.name}.")
                    else:
                        # If root_agent doesn't exist, try 'agent'
                        raise AttributeError(f"Module {resolved_agent_path} has 'agent' but not 'root_agent'. Please expose 'root_agent'.")
                else:
                    # Look for common factory functions or patterns if needed
                    operation_error(console, f"Could not find 'root_agent' or a suitable 'agent' variable in the module: {resolved_agent_path.name}")
                    raise ImportError(f"Could not find 'root_agent' or 'agent' in the module: {resolved_agent_path.name}")

                if not agent_to_run:
                    # Should have been caught above, but double check
                    raise ImportError("Failed to load a valid agent instance.")

                operation_complete(console, f"Agent '{getattr(agent_to_run, 'name', 'Unnamed Agent')}' loaded successfully.")

        except (ImportError, AttributeError) as e:
            operation_error(console, f"Failed to load agent: {e}")
            # Chain the original exception
            raise typer.Exit(code=1) from e
        except Exception as e:
            # Catch any other unexpected loading errors
            operation_error(console, f"An unexpected error occurred during agent loading: {e}")
            logger.error(traceback.format_exc())  # - Logger should be defined
            # Chain the original exception
            raise typer.Exit(code=1) from e

        # --- Instantiate Services ---
        # Session Service (using FileSystemSessionService)
        sessions_dir_path = Path(cfg.sessions_dir).expanduser()
        sessions_dir_str = str(sessions_dir_path)
        # Ensure directory exists (FileSystemSessionService might do this, but good practice)
        try:
            sessions_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            operation_error(console, f"Failed to create sessions directory {sessions_dir_str}: {e}")
            raise typer.Exit(code=1)  # noqa: B904

        logging.debug(f"Initializing FileSystemSessionService. Sessions dir: {sessions_dir_str}")
        file_system_session_service = FileSystemSessionService(sessions_dir=sessions_dir_str)

        # Memory Service (using JsonFileMemoryService)
        # Place memory store inside the sessions directory for organization
        memory_file_path = sessions_dir_path / "memory_store.json"
        memory_file_path_str = str(memory_file_path)
        logging.info(f"Using JSON memory store file: {memory_file_path_str}")
        json_memory_service = JsonFileMemoryService(filepath=memory_file_path_str)

        # Artifact Service (using default InMemory for now)
        # If needed, instantiate a specific one here
        artifact_service = InMemoryArtifactService()
        logging.debug("Using default InMemoryArtifactService.")

        # --- Execute Agent via run_cli --- #
        run_output = None  # Initialize run_output
        final_session_id = None  # Initialize final_session_id
        try:
            # Prepare arguments for run_cli
            run_cli_args = {
                "agent": agent_to_run,
                "app_name": cfg.app_name,  # Use app_name from config
                "user_id": cfg.user_id,  # Use user_id from config
                "initial_instruction": instruction,
                "session_id": session_id,
                "interactive": interactive,
                "show_timestamps": show_timestamps,
                # Pass the instantiated services
                "session_service": file_system_session_service,
                "memory_service": json_memory_service,
                "artifact_service": artifact_service,
            }

            # Run the agent using the utility function
            run_output = run_cli(**run_cli_args)

            # --- Session Saving Logic ---
            # Determine the session ID used (either provided or created)
            # Make final_session_id determination more robust
            if isinstance(run_output, dict):
                final_session_id = run_output.get("session_id")
            elif isinstance(run_output, str):
                final_session_id = run_output  # Assume string output is the session ID
            else:
                final_session_id = session_id  # Fallback to initial ID if run_output is None or unexpected type

            # If still no ID after checks, use the one from run_cli_args if it was provided
            if not final_session_id and run_cli_args.get("session_id"):
                final_session_id = run_cli_args["session_id"]

            if final_session_id:
                console.print(f"Session ID: {final_session_id}")

                # Check if saving is requested via CLI flag
                should_save = save_session_cli
                # If not via CLI, check config (assuming a config setting like `save_sessions_by_default`)
                # if not should_save and hasattr(cfg, 'save_sessions_by_default') and cfg.save_sessions_by_default:
                #     should_save = True

                if should_save:
                    sessions_dir_path = Path(cfg.sessions_dir).expanduser()
                    sessions_dir_str = str(sessions_dir_path)

                    # Ensure the directory exists
                    try:
                        sessions_dir_path.mkdir(parents=True, exist_ok=True)
                    except OSError as e:
                        operation_error(console, f"Failed to create sessions directory {sessions_dir_str} for saving: {e}")
                        # Don't exit, just report error and continue
                        should_save = False  # Prevent attempting save

                    if should_save:
                        save_path = sessions_dir_path / f"{final_session_id}.session.json"
                        try:
                            # Fetch the complete session data using the service
                            # Note: get_session might return None if the session ended abruptly
                            # Use the *final* session ID determined above
                            session_data = file_system_session_service.get_session(app_name=cfg.app_name, user_id=cfg.user_id, session_id=final_session_id)

                            if session_data:
                                # Convert Session object to dict before saving
                                session_dict = session_data.model_dump(mode="json")
                                with open(save_path, "w", encoding="utf-8") as f:
                                    json.dump(session_dict, f, indent=4)
                                operation_complete(console, f"Session saved to: {save_path}")
                            else:
                                operation_warning(console, f"Could not retrieve session data for ID {final_session_id} to save.")

                        except Exception as e:
                            operation_error(console, f"Failed to save session {final_session_id} to {save_path}: {e}")
                            logging.error(f"Saving Traceback:\n{traceback.format_exc()}")
            elif save_session_cli:
                operation_warning(console, "--save-session flag was used, but no final session ID was determined. Cannot save.")

        except Exception as e:
            operation_error(console, f"An error occurred during agent execution: {e}")
            logging.error(f"Execution Traceback:\n{traceback.format_exc()}")
            raise typer.Exit(code=1)  # noqa: B904

    except typer.Exit as e:
        # Let Typer Exit exceptions propagate naturally
        raise e
    except Exception as e:
        # Catch-all for other unexpected errors during the run process
        operation_error(console, f"An unexpected error occurred: {e}")
        logger.error(traceback.format_exc())  # Log the full traceback # - Logger should be defined
        raise typer.Exit(code=1) from e


# Note: Command registration happens in main.py
