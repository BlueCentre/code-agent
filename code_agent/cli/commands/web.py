"""
Command for running a web UI server for agents.
Uses our web_adapter to provide compatibility with ADK CLI web functionality.
"""

import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

# Console for rich output
console = Console()


def web_command(
    agents_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=True,
            file_okay=False,
            resolve_path=True,
            help="The directory of agents, where each sub-directory is a single agent.",
        ),
    ] = Path(os.getcwd()),
    session_db_url: Annotated[
        str,
        typer.Option(
            help="""Optional. The database URL to store the session.

- Use 'agentengine://<agent_engine_resource_id>' to connect to Agent Engine sessions.
- Use 'sqlite://<path_to_sqlite_file>' to connect to a SQLite DB.
- See https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls for more details on supported DB URLs."""
        ),
    ] = "",
    port: Annotated[int, typer.Option(help="Optional. The port of the server")] = 8000,
    allow_origins: Annotated[Optional[List[str]], typer.Option(help="Optional. Any additional origins to allow for CORS.")] = None,
    log_level: Annotated[
        str,
        typer.Option(
            help="Optional. Set the logging level",
            case_sensitive=False,
        ),
    ] = "INFO",
    log_to_tmp: Annotated[bool, typer.Option(help="Optional. Whether to log to system temp folder instead of console.")] = False,
    trace_to_cloud: Annotated[bool, typer.Option(help="Optional. Whether to enable cloud trace for telemetry.")] = False,
):
    """
    Runs a web UI for interacting with agents.

    Example:
        code-agent web path/to/agents_dir
    """
    # Set up logging
    if log_to_tmp:
        log_file = tempfile.NamedTemporaryFile(prefix="code_agent_web_", suffix=".log", delete=False, mode="w")
        logging.basicConfig(
            filename=log_file.name,
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        console.print(f"[bold blue]Logging to {log_file.name}[/bold blue]")
    else:
        logging.basicConfig(level=getattr(logging, log_level.upper()))

    # Create an async function to run the web server
    async def run_web_server():
        try:
            # Import our web adapter
            import uvicorn
            from fastapi import FastAPI

            from code_agent.adapters.web_adapter import create_web_app

            # Convert Path to string for compatibility
            agents_dir_str = str(agents_dir)

            # Create lifespan context manager
            @asynccontextmanager
            async def _lifespan(app: FastAPI):
                # Setup code (executed before server starts)
                console.print(f"[bold green]Starting web server for agents in {agents_dir_str}[/bold green]")
                console.print(f"[bold blue]Server will be available at http://localhost:{port}/[/bold blue]")
                console.print(f"[bold blue]Web UI will be available at http://localhost:{port}/static/[/bold blue]")

                yield  # Server is running during this yield

                # Cleanup code (executed after server stops)
                console.print("[bold yellow]Web server stopped[/bold yellow]")

            # Create the FastAPI app using our adapter
            app = create_web_app(
                agents_dir=agents_dir_str,
                session_db_url=session_db_url,
                allow_origins=allow_origins,
                lifespan=_lifespan,
                trace_to_cloud=trace_to_cloud,
            )

            # Configure and run the server
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=port,
                log_level=log_level.lower(),
            )
            server = uvicorn.Server(config)
            await server.serve()

        except Exception as e:
            console.print(f"[bold red]Error starting web server: {e!s}[/bold red]")
            raise typer.Exit(code=1) from e

    # Run the async function
    asyncio.run(run_web_server())
