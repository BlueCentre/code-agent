import importlib.util
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
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    ADK_INSTALLED = True
except ImportError:
    InMemorySessionService = None  # type: ignore
    ADK_INSTALLED = False


# Import helpers from utils
from code_agent.cli.utils import (
    _resolve_agent_path_str,
    operation_error,
    operation_warning,
    run_cli,
    setup_logging,
    thinking_indicator,
)

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
            console.print("Please install it using: [yellow]uv pip install google-adk[/yellow]")
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
                        raise ImportError(f"Could not import agent package '{module_name}' from {resolved_agent_path}: {e}") from e
                    finally:
                        # Clean up sys.path if needed, though generally safe to leave
                        # if parent_dir in sys.path and sys.path[0] == parent_dir:
                        #     sys.path.pop(0)
                        pass
                else:
                    raise ImportError(f"Agent path is neither a Python file nor a directory: {resolved_agent_path}")

                # Try to get the root_agent from the loaded module
                if hasattr(agent_module, "root_agent"):
                    agent_to_run = agent_module.root_agent
                elif hasattr(agent_module, "agent"):
                    # Check if module.agent itself looks like an agent instance
                    potential_agent = agent_module.agent
                    if hasattr(potential_agent, "name") and hasattr(potential_agent, "tools"):
                        agent_to_run = potential_agent
                        # Split the warning into two lines
                        operation_warning(console, f"Found top-level 'agent' variable in {module_name} and using it.")
                        operation_warning(console, "Consider renaming to 'root_agent' for clarity.")
                    # Check if agent_module.agent contains root_agent (less common)
                    elif hasattr(potential_agent, "root_agent"):
                        agent_to_run = potential_agent.root_agent
                        operation_warning(console, f"Found 'agent.root_agent' structure in {module_name}.")
                    else:
                        # Split the error message across lines
                        error_msg = f"Found 'agent' variable in {module_name}, but it doesn't look " "like an agent instance or contain 'root_agent'."
                        operation_error(console, error_msg)
                        raise ImportError("Cannot determine agent instance from 'agent' variable.")
                else:
                    # Look for common factory functions or patterns if needed
                    operation_error(console, f"Could not find 'root_agent' or a suitable 'agent' variable in the module: {module_name}")
                    raise ImportError(f"Could not find 'root_agent' or 'agent' in the module: {module_name}")

                if not agent_to_run:
                    # Should have been caught above, but double check
                    raise ImportError("Failed to load a valid agent instance.")

                # Use operation_complete from utils
                from code_agent.cli.utils import operation_complete

                operation_complete(console, f"Agent '{getattr(agent_to_run, 'name', 'Unnamed Agent')}' loaded successfully.")

        except (ImportError, AttributeError, Exception) as e:
            operation_error(console, f"Error loading agent: {e}")
            logging.exception("Agent loading failed.")  # Log traceback
            console.print(f"[dim]Traceback: {traceback.format_exc()}[/dim]")
            console.print(f"[dim]Attempted to load from: {resolved_agent_path}[/dim]")
            raise typer.Exit(code=1) from e

        # --- Verbose Output ---
        if cfg.verbosity >= 2:  # Corresponds to VERBOSE or DEBUG
            console.print(f"[dim]Agent path: {resolved_agent_path_str}[/dim]")
            console.print(f"[dim]Provider: {cfg.llm.provider}[/dim]")
            console.print(f"[dim]Model: {cfg.llm.model}[/dim]")
            # Ensure agent_to_run is not None before accessing name
            agent_name = getattr(agent_to_run, "name", "Unnamed Agent") if agent_to_run else "Unknown"
            console.print(f"[dim]Agent name: {agent_name}[/dim]")
            console.print(f"[dim]Temperature: {cfg.llm.temperature}[/dim]")
            console.print(f"[dim]Max tokens: {cfg.llm.max_tokens}[/dim]")
            if session_id:
                console.print(f"[dim]Continuing session: {session_id}[/dim]")

        # --- Session Service ---
        # ADK check ensures InMemorySessionService is available
        session_service = InMemorySessionService()

        # --- Run Agent via run_cli ---
        app_name = "code_agent_cli"
        user_id = "cli_user"

        try:
            # Call the run_cli utility function
            run_cli(
                agent=agent_to_run,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                interactive=interactive,
                show_timestamps=show_timestamps,
                session_service=session_service,
                initial_instruction=instruction,
            )
        except (Exception, typer.Exit) as e:  # Catch typer.Exit here too
            # run_cli should handle its own errors, but catch unexpected ones
            if not isinstance(e, typer.Exit):  # Don't double-print Exit messages
                operation_error(console, f"Error during agent execution: {e}")
                logging.exception("Unhandled exception during run_cli call.")
            raise  # Re-raise to exit

    except typer.Exit:
        # Let Typer's exit exceptions propagate cleanly
        raise
    except Exception as e:
        # Catch-all for unexpected errors during setup (e.g., config loading)
        operation_error(console, f"Unhandled exception in run command: {e}")
        logging.exception("Unhandled exception in run command.")
        raise typer.Exit(code=1) from e
