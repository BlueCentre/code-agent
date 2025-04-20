import datetime  # For timestamping history files
import json  # For saving history
from typing import Dict, List, Optional

import typer
from rich import print  # Use rich print for better formatting
from rich.markdown import Markdown  # Import Markdown renderer
from rich.prompt import Prompt  # Use rich Prompt for better input
from typing_extensions import Annotated

from code_agent import __version__ as agent_version  # Updated import

# Updated imports
# from myagent.llm import get_llm_response # No longer needed here
from code_agent.agent.agent import CodeAgent # Import the class
from code_agent.config.config import DEFAULT_CONFIG_DIR, get_config, initialize_config

app = typer.Typer(
    name="code-agent", # Updated app name
    help="CLI agent for interacting with LLMs and local environment.",
    add_completion=False
)

# --- Global Options/State ---
class GlobalState:
    def __init__(self):
        self.provider: Optional[str] = None
        self.model: Optional[str] = None

state = GlobalState()

@app.callback()
def main(
    ctx: typer.Context,
    provider: Annotated[
        Optional[str],
        typer.Option("--provider", "-p", help="LLM provider to use (e.g., openai, groq).")
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Specific LLM model to use.")
    ] = None,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", "-v",
            help="Show agent version and exit.",
            callback=lambda v: _version_callback(v),
            is_eager=True
        )
    ] = None,
    auto_approve_edits: Annotated[
        Optional[bool], # Optional so we know if the flag was explicitly set
        typer.Option(
            "--auto-approve-edits",
            help="Auto-approve file edits without confirmation. Use with caution!"
        )
    ] = None,
    auto_approve_native_commands: Annotated[
        Optional[bool],
        typer.Option(
            "--auto-approve-native-commands",
            help="Auto-approve native command execution. Use with extreme caution!"
        )
    ] = None,
    # Add other CLI options corresponding to config overrides if needed
    # e.g., auto_approve_edit: bool = typer.Option(False, "--auto-approve-edit")
):
    """
    Code-Agent: Interact with AI models and your local environment.
    """
    # Ensure config directory exists before trying to load/initialize
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize configuration singleton, applying CLI overrides
    initialize_config(
        cli_provider=provider,
        cli_model=model,
        cli_auto_approve_edits=auto_approve_edits, # Pass CLI flag value
        cli_auto_approve_native_commands=auto_approve_native_commands, # Pass CLI flag value
    )

    # Store CLI options in state for potential direct use (optional)
    # state.provider = provider # These might not be needed if get_config() is always used
    # state.model = model

# --- Helper Callbacks ---
def _version_callback(value: bool):
    if value:
        print(f"Code Agent version: {agent_version}") # Updated output message
        raise typer.Exit()

# --- Placeholder Commands ---
@app.command()
def run(prompt: Annotated[str, typer.Argument(help="The prompt to send to the LLM.")]):
    """
    Run a single prompt and get a response using the ADK agent.
    """
    print(f"[bold blue]Prompt:[/bold blue] {prompt}")

    # Instantiate CodeAgent (gets config internally)
    code_agent = CodeAgent()
    response = code_agent.run_turn(prompt=prompt)

    if response:
        # Render response as Markdown
        print("\n[bold green]Response:[/bold green]")
        print(Markdown(response))
    else:
        print("[bold red]Failed to get response.[/bold red]")

# --- History Saving/Loading Logic ---
HISTORY_DIR = DEFAULT_CONFIG_DIR / "history"

def save_history(session_id: str, history: List[Dict[str, str]]):
    """Saves chat history to a JSON file."""
    if not history:
        return # Don't save empty history
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        file_path = HISTORY_DIR / f"chat_{session_id}.json"
        with open(file_path, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"[grey50]Chat history saved to {file_path}[/grey50]")
    except Exception as e:
        print(f"[red]Error saving chat history:[/red] {e}")

def load_latest_history() -> List[Dict[str, str]]:
    """Loads the most recent chat history file if available."""
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        history_files = sorted(
            HISTORY_DIR.glob("chat_*.json"),
            key=lambda f: f.stat().st_mtime, # Sort by modification time
            reverse=True # Latest first
        )

        if not history_files:
            return []

        latest_file = history_files[0]
        print(f"[grey50]Loading history from {latest_file.name}...[/grey50]")
        with open(latest_file, 'r') as f:
            loaded_history = json.load(f)
            # Basic validation
            if isinstance(loaded_history, list):
                # Further validation could check dict structure/keys
                return loaded_history
            else:
                print(
                    f"[red]Error:[/red] Invalid format in history file "
                    f"{latest_file.name}. Starting fresh."
                )
                return []
    except Exception as e:
        print(f"[red]Error loading chat history:[/red] {e}. Starting fresh.")
        return []

# --- CLI Commands ---
@app.command()
def chat():
    """
    Start an interactive chat session.
    """
    print("[bold green]Starting interactive chat session...[/bold green]")
    print("Type 'quit' or 'exit' to end the session.")

    # Initialize the agent once for the session
    print("[grey50]Initializing agent...[/grey50]")
    code_agent = CodeAgent()

    # Load latest history and assign it to the agent's history
    loaded_history = load_latest_history()
    if loaded_history:
        code_agent.history = loaded_history
        print(f"[grey50]Loaded {len(loaded_history)} messages from previous session.[/grey50]")
    else:
        print("[grey50]Starting new chat session.[/grey50]")

    # Generate a new session ID for saving this session's history
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # print(f"[grey50]Current Session ID for saving: {session_id}[/grey50]")

    while True:
        try:
            # Use rich Prompt for input
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            if user_input.lower() in ["quit", "exit"]:
                print("[bold yellow]Exiting chat session.[/bold yellow]")
                save_history(session_id, code_agent.history) # Save agent's history
                break

            if not user_input:
                continue

            # Run agent turn (history is managed internally by the agent)
            response = code_agent.run_turn(prompt=user_input)

            # Display response (agent's run_turn already handles history update)
            if response:
                # Render response as Markdown
                print("\n[bold yellow]Agent:[/bold yellow]")
                print(Markdown(response))
            else:
                print("[bold red]Failed to get response.[/bold red]")

        except KeyboardInterrupt:
            print("\n[bold yellow]Chat interrupted. Exiting.[/bold yellow]")
            save_history(session_id, code_agent.history) # Save history on interrupt
            break
        except Exception as e:
            print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
            save_history(session_id, code_agent.history) # Attempt to save history on error
            # Consider adding a traceback here for debugging
            # import traceback
            # traceback.print_exc()

# --- Config Commands ---
config_app = typer.Typer(name="config", help="Manage configuration.")
app.add_typer(config_app)

@config_app.command("show")
def config_show():
    """
    Show the current effective configuration.
    """
    # Get the already initialized config
    config = get_config()
    print(
        "[bold magenta]Current Effective Configuration "
        "(CLI > Env > File > Defaults):[/bold magenta]"
    )
    print(config.model_dump_json(indent=2))

# --- Provider Commands ---
provider_app = typer.Typer(name="providers", help="Manage providers.")
app.add_typer(provider_app)

@provider_app.command("list")
def providers_list():
    """
    List available/configured providers based on effective config.
    """
    config = get_config()
    print("[bold cyan]Configured Providers (based on effective API keys):[/bold cyan]")
    found = False
    for provider, key in config.api_keys.model_dump().items():
        if key: # Only list if a key is potentially configured (env var or file)
            print(f"- {provider}")
            found = True
    if not found:
        print("No providers found with configured API keys.")
    print(f"\nDefault Provider: {config.default_provider}")
    print(f"Default Model: {config.default_model}")

if __name__ == "__main__":
    app()
