import uuid
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

# --- Constants ---
SESSION_ID_HELP = "The session ID to view history for."
SESSION_ID_ARG = typer.Argument(help=SESSION_ID_HELP)

# --- Session Commands ---


def history(
    session_id: Annotated[
        str,
        SESSION_ID_ARG,
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


def sessions(
    count: Annotated[
        Optional[int],
        typer.Option("--count", "-n", help="Number of most recent sessions to show."),
    ] = 10,
    all_sessions: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all sessions instead of just the most recent ones."),
    ] = False,
):
    """
    List available chat sessions that can be continued.

    Note: Due to limitations of InMemorySessionService, this command can only show sessions
    created in the current process. For session persistence, use the --session-id flag with
    the run command to continue a session.
    """
    console = Console()
    console.print("[bold cyan]Available Sessions:[/bold cyan]")

    # TODO: Implement actual session listing if a persistent SessionService is used.
    # For now, display the limitations message.

    console.print("[yellow]Note: InMemorySessionService only retains sessions for the current process.[/yellow]")
    console.print("[dim]To continue a session from a previous run, you need to save the session ID.[/dim]")
    console.print('[dim]Example: code-agent run "your question" --session-id <your-saved-session-id>[/dim]')

    # Display a note about session persistence
    console.print("\n[bold]For persistent sessions, use one of these approaches:[/bold]")
    console.print("1. [dim]Save the session ID displayed at the end of each run command[/dim]")
    console.print("2. [dim]Use a database URL with a custom session service implementation[/dim]")

    # Let's give a sample session ID to demonstrate the format
    sample_id = str(uuid.uuid4())
    console.print("\n[bold]Sample usage:[/bold]")
    # Example needs agent path if no default is set
    console.print(f'[dim]code-agent run <agent_path> "your question" --session-id {sample_id}[/dim]')
