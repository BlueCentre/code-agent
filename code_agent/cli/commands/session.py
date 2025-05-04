import logging
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from code_agent.cli.utils import operation_error
from code_agent.config import get_config

# Create a Typer app for session commands (if needed, or register directly)
# session_app = typer.Typer(help="Manage and view conversation sessions.")

# --- Constants ---
SESSION_ID_HELP = "The session ID to view history for."
SESSION_ID_ARG = typer.Argument(help=SESSION_ID_HELP)
HISTORY_SESSION_ID_ARG = typer.Argument(..., help="The ID of the session whose history you want to view.")

# --- Session Commands ---


def history(
    session_id: Annotated[
        str,
        HISTORY_SESSION_ID_ARG,
    ],
    count: Annotated[
        Optional[int],
        typer.Option("--count", "-n", help="Number of most recent messages to show (default: all)."),
    ] = None,
    show_timestamps: Annotated[
        bool,
        typer.Option("--timestamps", "-t", help="Show timestamps for each message"),
    ] = False,
):
    """
    View the history of a previous conversation session.

    Note: Due to limitations of InMemorySessionService, this command can only
    show sessions from the current process. Sessions do not persist between
    CLI restarts with the current implementation.
    """
    console = Console()
    console.print(f"[bold cyan]Session History:[/bold cyan] Retrieving history for session {session_id}")

    # TODO: Implement actual history retrieval if a persistent SessionService is used.
    # For now, display the limitations message.

    console.print("[yellow]Note: InMemorySessionService only retains sessions for the current process.[/yellow]")
    console.print("[dim]Session does not exist or was created in a different process.[/dim]")
    console.print("[dim]To continue a session, use the session ID with the run command:[/dim]")
    # Make sure the example command uses the actual command structure
    console.print(f'[dim]code-agent run "your question" --session-id {session_id}[/dim]')

    # Display information about persistent session storage
    console.print("\n[bold]For session persistence between CLI runs:[/bold]")
    console.print("1. [dim]Use --session-id with the run command to specify a known session ID[/dim]")
    console.print("2. [dim]Implement a database-backed session service for true persistence[/dim]")

    # Explain the issue more technically
    console.print("\n[dim]Technical note: The InMemorySessionService stores sessions in memory only,[/dim]")
    console.print("[dim]so sessions are lost when the process ends. Persistence would require:[/dim]")
    console.print("[dim]- SQL database session storage[/dim]")
    console.print("[dim]- Cloud-based session service[/dim]")
    console.print("[dim]- Custom file-based session implementation[/dim]")


def sessions() -> None:
    """
    List available saved conversation sessions.
    """
    console = Console()
    try:
        # 1. Initialize and get configuration
        # Suppress warnings during this specific initialization if needed
        # initialize_config(validate=False) # Validation might not be strictly needed here
        cfg = get_config()  # Assume config is initialized by main callback

        # 2. Get sessions directory from config
        sessions_dir = cfg.sessions_dir

        # 3. Check if sessions_dir is configured
        if not sessions_dir:
            operation_error(console, "Session directory is not configured. Cannot list sessions.")
            raise typer.Exit(code=1)

        # 4. Check if the directory exists
        if not sessions_dir.is_dir():
            console.print(f"[yellow]Sessions directory not found:[/yellow] {sessions_dir}")
            console.print("No sessions saved yet or directory is misconfigured.")
            raise typer.Exit(code=0)  # Not an error if dir just doesn't exist yet

        # 5. Find session files
        try:
            session_files = sorted(list(sessions_dir.glob("*.session.json")), key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError as e:
            operation_error(console, f"Error accessing sessions directory '{sessions_dir}': {e}")
            raise typer.Exit(code=1) from e

        # 6. Print the list
        if not session_files:
            console.print(f"No saved sessions found in: {sessions_dir}")
        else:
            console.print(f"[bold cyan]Available Sessions (in {sessions_dir}):[/bold cyan]")
            for file_path in session_files:
                # Extract session ID from filename stem
                session_id = file_path.stem.replace(".session", "")
                console.print(f"- {session_id}")

    except typer.Exit:
        raise  # Let Typer exits pass through
    except Exception as e:
        operation_error(console, f"An unexpected error occurred while listing sessions: {e}")
        logging.exception("Error listing sessions")  # Log the full traceback
        raise typer.Exit(code=1) from e
