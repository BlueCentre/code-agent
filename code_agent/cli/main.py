import logging
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from typing_extensions import Annotated

# Local application imports
from code_agent import __version__ as agent_version
from code_agent.cli.commands.api_server import api_server_command
from code_agent.cli.commands.config import config_app

# Import command functions
from code_agent.cli.commands.create import create_command
from code_agent.cli.commands.deploy import deploy_app
from code_agent.cli.commands.eval import eval_command
from code_agent.cli.commands.provider import provider_app

# Import command functions and apps from submodules
from code_agent.cli.commands.run import run_command
from code_agent.cli.commands.session import history as history_command
from code_agent.cli.commands.session import sessions as sessions_command
from code_agent.cli.commands.web import web_command
from code_agent.config import get_config, initialize_config

# Load environment variables first (e.g., from .env)
load_dotenv()

# --- ADK Version Check (Keep simplified version) ---
ADK_INSTALLED = False
try:
    import google.adk  # Just check if base exists

    adk_version = getattr(google.adk, "__version__", "unknown")
    ADK_INSTALLED = True
except ImportError:
    adk_version = "Google ADK not installed"

# --- Typer App Definition ---
app = typer.Typer(
    name="code-agent",
    help="Code Agent CLI - Enhanced with ADK capabilities.",
    add_completion=True,
)

# --- Register Commands ---

# Register the run command
# Need to explicitly add it using app.command() decorator on the imported function
# This is slightly different from add_typer
app.command("run")(run_command)

# Register session commands
app.command("history")(history_command)
app.command("sessions")(sessions_command)

# Register commands with ADK compatibility
app.command("create")(create_command)
app.command("eval")(eval_command)
app.command("web")(web_command)
app.command("api_server")(api_server_command)

# Register sub-apps
app.add_typer(config_app, name="config")
app.add_typer(provider_app, name="providers")
app.add_typer(deploy_app, name="deploy")


# --- Version Callback ---
def _version_callback(value: bool):
    """Prints the version of the application and ADK, then exits."""
    if value:
        console = Console()
        console.print(f"Code Agent version: {agent_version}")
        console.print(f"Google ADK version: {adk_version}")
        raise typer.Exit()


# --- Main Callback --- (Handles global setup)
# BUG: Running `code-agent` without any subcommands or arguments does not show help.
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,  # Process this before other options/commands
            help="Show the application version and exit.",
        ),
    ] = None,  # Default value for the option
    # Note: Global options like --verbose, --log-level are handled within each command
    # that needs them (like 'run') during their specific config initialization.
    # We keep the main callback simple for initial setup.
):
    """
    Code Agent CLI: Your AI assistant for coding tasks.

    Use 'code-agent [COMMAND] --help' for more information on a specific command.
    Example: 'code-agent run --help'
    """
    # 1. Initialize configuration (without CLI overrides initially)
    #    This loads defaults, file, and environment variables.
    #    CLI overrides are handled per-command where applicable.
    #    Suppress warnings during this initial load.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        initialize_config(validate=False)  # Initial load, validation happens later if needed

    initial_cfg = get_config()

    # Logging setup is now handled within individual commands (like 'run')
    # after they process their specific CLI arguments.
    # setup_logging(initial_cfg.verbosity)
    # logging.debug(f"Initial logging setup complete. Level: {logging.getLevelName(logging.getLogger().getEffectiveLevel())}")

    # 3. Store the initial config in the context (optional, commands can call get_config())
    ctx.ensure_object(dict)
    ctx.obj["config"] = initial_cfg
    logging.debug("Initial config stored in context object.")

    # 4. If no command is given, show help (Typer default behavior with invoke_without_command=True)
    if ctx.invoked_subcommand is None:
        # Typer automatically shows help here, no need for explicit print
        logging.debug("No subcommand invoked, Typer will show help.")
        # We don't raise Exit here, Typer handles it.
        pass
    else:
        logging.debug(f"Invoked subcommand: {ctx.invoked_subcommand}")


# --- Entry Point ---
if __name__ == "__main__":
    app()
