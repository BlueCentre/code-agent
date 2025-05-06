"""
Commands for deploying agents to cloud environments.
Uses our deploy_adapter to provide cloud deployment functionality.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

# Import our deploy adapter
from code_agent.adapters.deploy_adapter import deploy_to_cloud_run

# Create a Typer app for deploy commands
deploy_app = typer.Typer(name="deploy", help="Deploy agent to hosted environments.")

# Console for rich output
console = Console()


@deploy_app.callback()
def deploy_callback():
    """Deploy agents to cloud environments."""
    pass


@deploy_app.command("cloud_run")
def cloud_run_command(
    agent: Annotated[Path, typer.Argument(exists=True, dir_okay=True, file_okay=False, resolve_path=True, help="Path to the agent source code folder.")],
    project: Annotated[
        Optional[str], typer.Option(help="Required. Google Cloud project to deploy the agent. When absent, default project from gcloud config is used.")
    ] = None,
    region: Annotated[
        Optional[str], typer.Option(help="Required. Google Cloud region to deploy the agent. When absent, gcloud run deploy will prompt later.")
    ] = None,
    service_name: Annotated[str, typer.Option(help="Optional. The service name to use in Cloud Run.")] = "adk-default-service-name",
    app_name: Annotated[str, typer.Option(help="Optional. App name of the ADK API server (default: the folder name of the AGENT source code).")] = "",
    port: Annotated[int, typer.Option(help="Optional. The port of the ADK API server.")] = 8000,
    trace_to_cloud: Annotated[bool, typer.Option(help="Optional. Whether to enable Cloud Trace for cloud run.")] = False,
    with_ui: Annotated[bool, typer.Option(help="Optional. Deploy ADK Web UI if set. (default: deploy ADK API server only)")] = False,
    temp_folder: Annotated[str, typer.Option(help="Optional. Temp folder for the generated Cloud Run source files.")] = os.path.join(
        tempfile.gettempdir(),
        "cloud_run_deploy_src",
        datetime.now().strftime("%Y%m%d_%H%M%S"),
    ),
    verbosity: Annotated[str, typer.Option(help="Optional. Override the default verbosity level.")] = "WARNING",
    session_db_url: Annotated[
        str,
        typer.Option(
            help="""Optional. The database URL to store the session.
            
- Use 'agentengine://<agent_engine_resource_id>' to connect to Agent Engine sessions.
- Use 'sqlite://<path_to_sqlite_file>' to connect to a SQLite DB.
- See https://docs.sqlalchemy.org/en/20/core/engines.html#backend-specific-urls for more details on supported DB URLs."""
        ),
    ] = "",
):
    """
    Deploy an agent to Google Cloud Run.

    Example:
        code-agent deploy cloud_run path/to/my_agent
    """
    # Convert Path to string for compatibility with the existing function
    agent_str = str(agent)

    try:
        console.print(f"[bold blue]Deploying agent at {agent_str} to Cloud Run...[/bold blue]")
        deploy_to_cloud_run(
            agent=agent_str,
            project=project,
            region=region,
            service_name=service_name,
            app_name=app_name,
            temp_folder=temp_folder,
            port=port,
            trace_to_cloud=trace_to_cloud,
            with_ui=with_ui,
            verbosity=verbosity,
            session_db_url=session_db_url,
        )
        console.print("[bold green]Deployment complete![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Deployment failed: {e!s}[/bold red]")
        raise typer.Exit(code=1) from e
