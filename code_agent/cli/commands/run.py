"""
This module contains the commands for the run sub-app.
"""

import asyncio
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
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.sessions.session import Session

    # Some modules might be missing in the current ADK version
    try:
        from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    except ImportError:
        InMemoryMemoryService = None

    # Adapt to available Content/Part classes
    try:
        from google.adk.genai.types import Content, Part
    except ImportError:
        # Alternative imports if genai module is not available
        try:
            from google.adk.models.types import Content, Part
        except ImportError:
            # Fallback to a minimal implementation if needed
            from dataclasses import dataclass

            @dataclass
            class Part:
                text: str = None

            @dataclass
            class Content:
                role: str = "user"
                parts: list = None

                def __post_init__(self):
                    if self.parts is None:
                        self.parts = []

    ADK_INSTALLED = True
except ImportError as e:
    # Set all to None if ANY import fails
    InMemoryArtifactService = None  # type: ignore
    InMemorySessionService = None  # type: ignore
    InMemoryMemoryService = None  # type: ignore
    Content = None  # type: ignore
    Part = None  # type: ignore
    Session = None  # type: ignore
    ADK_INSTALLED = False
    print(f"Failed to import ADK: {e}")

# Import pydantic for input file validation
from pydantic import BaseModel

from code_agent.cli.utils import (
    _resolve_agent_path_str,
    operation_complete,
    operation_error,
    run_cli,
    setup_logging,
    step_progress,
)

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


# Model for replaying a sequence of queries with initial state
class InputFile(BaseModel):
    state: dict[str, object]
    queries: list[str]


# Create module-level singletons for argument types to avoid B008
INSTRUCTION_ARG = typer.Argument(help=INSTRUCTION_HELP, default="")  # Default to empty string for interactive mode
# Use Optional[Path] and handle None/existence check in the command
AGENT_PATH_ARG = typer.Argument(
    help=AGENT_PATH_HELP,
    exists=False,
    file_okay=True,
    dir_okay=True,
    readable=True,
)


# Helper function to run the agent asynchronously
async def _run_agent_async(runner, user_id, session_id, content, console):
    """Run the agent asynchronously and print the output."""
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.content and event.content.parts:
            text = "".join(part.text or "" for part in event.content.parts)
            if text:
                console.print(f"[dim][{event.author}]:[/dim] {text}")


# --- Run Command ---
def run_command(
    instruction: Annotated[
        str,  # Not optional
        typer.Argument(help=INSTRUCTION_HELP),
    ],
    # Agent path is a required positional argument, not optional
    agent_path: Annotated[
        Path,  # Not optional to avoid confusing typer
        typer.Argument(help=AGENT_PATH_HELP),
    ],
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
    save_session: Annotated[
        bool,
        typer.Option("--save-session", help="Save the conversation session to a file."),
    ] = False,
    replay: Annotated[
        Optional[Path],
        typer.Option(
            exists=True,
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="The json file that contains the initial state of the session and user queries. A new session will be created using this state. And user queries are run against the newly created session. Users cannot continue to interact with the agent.",
        ),
    ] = None,
    resume: Annotated[
        Optional[Path],
        typer.Option(
            exists=True,
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            help="The json file that contains a previously saved session (by --save-session option). The previous session will be re-displayed. And user can continue to interact with the agent.",
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

    This command lets you interact with an agent, either by starting a new conversation,
    replaying a recorded session, or resuming a previous session.

    Examples:
        code-agent run "Write a function to calculate the Fibonacci sequence" path/to/my_agent
        code-agent run "Say hello" path/to/my_agent --provider ollama
        code-agent run "-" path/to/my_agent --interactive  # Start directly in interactive mode with a dash placeholder
    """
    console = Console()

    if replay and resume:
        console.print("[bold red]Error:[/bold red] The --replay and --resume options cannot be used together.")
        raise typer.Exit(code=1)

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
            console.print("[bold red]Error:[/bold red] No agent path specified and no default agent_path in config.")
            console.print("Please specify an agent path: [yellow]code-agent run --help[/yellow]")
            raise typer.Exit(code=1)

        # Convert to Path object for easier handling
        resolved_agent_path = Path(resolved_agent_path_str)
        logging.debug(f"Resolved agent path: {resolved_agent_path}")

        # --- Agent Loading ---
        # This approach to dynamic loading allows the user to specify an agent.py
        # file directly or a module directory containing agent.py
        with step_progress(console, f"Loading agent from {resolved_agent_path}"):
            # Check if the path is a directory or file
            if resolved_agent_path.is_dir():
                agent_dir = resolved_agent_path
                agent_file = "agent.py"  # Default filename
                agent_module_path_str = str(agent_dir / agent_file)
                agent_name = agent_dir.name  # Use directory name as module name
            else:
                # Path is a file, assume it's a Python module
                agent_dir = resolved_agent_path.parent
                agent_file = resolved_agent_path.name
                agent_module_path_str = str(resolved_agent_path)
                agent_name = agent_dir.name  # Use parent directory name as module name

            # Add agent directory to path
            agent_parent_dir = str(agent_dir.parent)
            if agent_parent_dir not in sys.path:
                sys.path.append(agent_parent_dir)
                logging.debug(f"Added {agent_parent_dir} to sys.path")

            # Load agent module
            try:
                if agent_file == "agent.py":
                    # Standard case with agent.py in agent_dir
                    try:
                        # Try importing as a Python module
                        # Use the correct path for importing
                        if "." in agent_name or "-" in agent_name:
                            # For names with dots or dashes, use spec_from_file_location instead of import_module
                            agent_spec = importlib.util.spec_from_file_location(f"{agent_name}.agent", agent_module_path_str)
                            if not agent_spec or not agent_spec.loader:
                                raise ImportError(f"Failed to load agent module spec from {agent_module_path_str}")
                            agent_module = importlib.util.module_from_spec(agent_spec)
                            agent_spec.loader.exec_module(agent_module)
                            logging.debug(f"Successfully loaded {agent_module_path_str} from file path")
                        else:
                            # For regular module names, use import_module
                            agent_module = importlib.import_module(f"{agent_name}.agent")
                            logging.debug(f"Successfully imported {agent_name}.agent as a module")
                    except (ImportError, ModuleNotFoundError):
                        # Fall back to loading from file path
                        agent_spec = importlib.util.spec_from_file_location(f"{agent_name}.agent", agent_module_path_str)
                        if not agent_spec or not agent_spec.loader:
                            raise ImportError(f"Failed to load agent module spec from {agent_module_path_str}")
                        agent_module = importlib.util.module_from_spec(agent_spec)
                        agent_spec.loader.exec_module(agent_module)
                        logging.debug(f"Successfully loaded {agent_module_path_str} from file path")
                else:
                    # Custom file name case
                    agent_spec = importlib.util.spec_from_file_location(f"{agent_name}.custom", agent_module_path_str)
                    if not agent_spec or not agent_spec.loader:
                        raise ImportError(f"Failed to load agent module spec from {agent_module_path_str}")
                    agent_module = importlib.util.module_from_spec(agent_spec)
                    agent_spec.loader.exec_module(agent_module)
                    logging.debug(f"Successfully loaded custom file {agent_module_path_str}")

                # Check for root_agent in the module
                agent_to_run = getattr(agent_module, "root_agent", None)
                if not agent_to_run:
                    # Provide a more helpful error message
                    raise ImportError(f"No 'root_agent' found in {agent_module_path_str}. " f"Please ensure this file defines a variable named 'root_agent'.")

                operation_complete(
                    console, f"[dim]Agent '{getattr(agent_to_run, 'name', 'Unnamed Agent')}' loaded successfully from {resolved_agent_path.name}.[/dim]"
                )

            except (ImportError, AttributeError) as e:
                operation_error(console, f"Failed to load agent: {e}")
                # Show more detailed instructions for common errors
                if "No module named" in str(e) and agent_name in str(e):
                    operation_error(console, "Hint: Make sure your agent directory has an __init__.py file and proper Python module structure.")

                # Chain the original exception
                raise typer.Exit(code=1) from e
            except Exception as e:
                # Catch any other unexpected loading errors
                operation_error(console, f"An unexpected error occurred during agent loading: {e}")
                logger.error(traceback.format_exc())  # - Logger should be defined
                # Chain the original exception
                raise typer.Exit(code=1) from e

        # --- Instantiate Services ---
        # Session Service
        sessions_dir_path = Path(cfg.sessions_dir).expanduser()
        sessions_dir_str = str(sessions_dir_path)
        # Ensure directory exists
        try:
            sessions_dir_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            operation_error(console, f"Failed to create sessions directory {sessions_dir_str}: {e}")
            raise typer.Exit(code=1)

        logging.debug(f"Initializing session service. Sessions dir: {sessions_dir_str}")
        artifact_service = InMemoryArtifactService()
        session_service = InMemorySessionService()

        # Set app_name and user_id
        app_name = agent_name
        user_id = "user_id"  # Default user ID

        # Create an ADK runner to execute the agent
        from google.adk.runners import Runner

        runner = Runner(
            app_name=app_name,
            agent=agent_to_run,
            artifact_service=artifact_service,
            session_service=session_service,
        )

        # Create session based on CLI options
        if replay:
            # Replay mode - load initial state and queries from file
            console.print(f"[bold blue]Replaying session from {replay}[/bold blue]")
            try:
                with open(replay, "r", encoding="utf-8") as f:
                    input_file = InputFile.model_validate_json(f.read())

                from datetime import datetime

                # Add current time to state
                input_file.state["_time"] = datetime.now()

                # Create new session with the loaded state
                session = session_service.create_session(app_name=app_name, user_id=user_id, state=input_file.state)

                # Run the agent with each query
                for query in input_file.queries:
                    console.print(f"[dim][user]:[/dim] {query}")
                    content = Content(role="user", parts=[Part(text=query)])

                    # Run the agent and print output
                    asyncio.run(_run_agent_async(runner, session.user_id, session.id, content, console))

                # If the user wants interactive mode after replay, run interactively
                if interactive:
                    console.print("\n[bold blue]Entering interactive mode...[/bold blue]")
                    # Call run_cli with the existing session
                    run_cli(
                        agent=agent_to_run,
                        app_name=app_name,
                        artifact_service=artifact_service,
                        session_service=session_service,
                        session=session,
                        interactive=True,
                        show_timestamps=show_timestamps,
                    )

            except Exception as e:
                operation_error(console, f"Failed to replay session: {e}")
                raise typer.Exit(code=1) from e

        elif resume:
            # Resume mode - load previous session and continue interactively
            console.print(f"[bold blue]Resuming session from {resume}[/bold blue]")
            try:
                # Load the session from the file
                with open(resume, "r") as f:
                    loaded_session = Session.model_validate_json(f.read())

                # Create a new session
                session = session_service.create_session(app_name=app_name, user_id=user_id)

                # Replay the events in the loaded session
                for event in loaded_session.events:
                    session_service.append_event(session, event)
                    content = event.content
                    if not content or not content.parts or not content.parts[0].text:
                        continue
                    if event.author == "user":
                        console.print(f"[dim][user]:[/dim] {content.parts[0].text}")
                    else:
                        console.print(f"[dim][{event.author}]:[/dim] {content.parts[0].text}")

                # Continue interactively
                run_cli(
                    agent=agent_to_run,
                    app_name=app_name,
                    artifact_service=artifact_service,
                    session_service=session_service,
                    session=session,
                    interactive=True,
                    show_timestamps=show_timestamps,
                )
            except Exception as e:
                operation_error(console, f"Failed to resume session: {e}")
                raise typer.Exit(code=1) from e
        else:
            # Normal mode - create new session and run with the instruction
            logging.debug(f"Creating new session with app_name={app_name}, user_id={user_id}")
            session = session_service.create_session(app_name=app_name, user_id=user_id)

            # Check if instruction is empty or a dash placeholder for interactive mode
            if not instruction.strip() or instruction == "-":
                # When placeholder is used, treat it as interactive mode
                # even if --interactive flag wasn't explicitly set
                interactive = True
                console.print("\n[bold blue]Starting interactive session...[/bold blue]")
                run_cli(
                    agent=agent_to_run,
                    app_name=app_name,
                    artifact_service=artifact_service,
                    session_service=session_service,
                    session=session,
                    interactive=True,
                    show_timestamps=show_timestamps,
                )
            else:
                # Process the instruction normally
                console.print(f"[dim][user]:[/dim] {instruction}")
                content = Content(role="user", parts=[Part(text=instruction)])

                # Run the agent and print output
                asyncio.run(_run_agent_async(runner, session.user_id, session.id, content, console))

                # If interactive mode is enabled, continue interaction
                if interactive:
                    console.print("\n[bold blue]Entering interactive mode...[/bold blue]")
                    run_cli(
                        agent=agent_to_run,
                        app_name=app_name,
                        artifact_service=artifact_service,
                        session_service=session_service,
                        session=session,
                        interactive=True,
                        show_timestamps=show_timestamps,
                    )

        # Handle session saving if requested
        if save_session:
            final_session_id = session.id
            if not final_session_id:
                custom_session_id = typer.prompt("Enter a session ID to save")
                final_session_id = custom_session_id

            session_path = sessions_dir_path / f"{final_session_id}.session.json"

            # Fetch the session again to get all the details
            session = session_service.get_session(
                app_name=session.app_name,
                user_id=session.user_id,
                session_id=session.id,
            )

            with open(session_path, "w") as f:
                f.write(session.model_dump_json(indent=2, exclude_none=True))

            console.print(f"[bold green]Session saved to {session_path}[/bold green]")

    except Exception as e:
        # Catch any uncaught exceptions
        operation_error(console, f"An unexpected error occurred: {e}")
        logger.error(traceback.format_exc())
        raise typer.Exit(code=1) from e


# Note: Command registration happens in main.py
