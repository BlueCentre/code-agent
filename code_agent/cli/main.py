import datetime  # For timestamping history files
import json  # For saving history
from typing import Dict, List, Optional

import typer
from rich import print  # Use rich print for better formatting
from rich.console import Console  # Import Console for rich formatting
from rich.markdown import Markdown  # Import Markdown renderer
from rich.prompt import Prompt  # Use rich Prompt for better input
from typing_extensions import Annotated

from code_agent import __version__ as agent_version  # Updated import

# Updated imports
# from code_agent.llm import get_llm_response # No longer needed here
from code_agent.agent.agent import CodeAgent  # Import the class
from code_agent.config.config import DEFAULT_CONFIG_DIR, get_config, initialize_config

# Import Ollama commands
try:
    from cli_agent.commands.ollama import app as ollama_app
except ImportError:
    ollama_app = None

app = typer.Typer(
    name="code-agent",  # Updated app name
    help="CLI agent for interacting with LLMs and local environment.",
    add_completion=True,
    no_args_is_help=True,  # Show help when no arguments are provided
)

# Add Ollama commands if available
if ollama_app:
    app.add_typer(ollama_app, name="ollama", help="Interact with Ollama models")


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
        typer.Option("--provider", "-p", help="LLM provider to use (e.g., openai, groq)."),
    ] = None,
    model: Annotated[Optional[str], typer.Option("--model", "-m", help="Specific LLM model to use.")] = None,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show agent version and exit.",
            callback=lambda v: _version_callback(v),
            is_eager=True,
        ),
    ] = None,
    auto_approve_edits: Annotated[
        Optional[bool],  # Optional so we know if the flag was explicitly set
        typer.Option(
            "--auto-approve-edits",
            help="Auto-approve file edits without confirmation. Use with caution!",
        ),
    ] = None,
    auto_approve_native_commands: Annotated[
        Optional[bool],
        typer.Option(
            "--auto-approve-native-commands",
            help="Auto-approve native command execution. Use with extreme caution!",
        ),
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
        cli_auto_approve_edits=auto_approve_edits,
        cli_auto_approve_native_commands=auto_approve_native_commands,
    )

    # Store CLI options in state for potential direct use (optional)
    # state.provider = provider
    # These might not be needed if get_config() is always used
    # state.model = model


# --- Helper Callbacks ---
def _version_callback(value: bool):
    if value:
        print(f"Code Agent version: {agent_version}")  # Updated output message
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
        return  # Don't save empty history
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        file_path = HISTORY_DIR / f"chat_{session_id}.json"
        with open(file_path, "w") as f:
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
            key=lambda f: f.stat().st_mtime,  # Sort by modification time
            reverse=True,  # Latest first
        )

        if not history_files:
            return []

        latest_file = history_files[0]
        print(f"[grey50]Loading history from {latest_file.name}...[/grey50]")
        with open(latest_file, "r") as f:
            loaded_history = json.load(f)
            # Basic validation
            if isinstance(loaded_history, list):
                # Further validation could check dict structure/keys
                return loaded_history
            else:
                print(f"[red]Error:[/red] Invalid format in history file " f"{latest_file.name}. Starting fresh.")
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
    print("Special commands: /help for assistance, /clear to clear history")

    # Initialize the agent once for the session
    print("[grey50]Initializing agent...[/grey50]")
    code_agent = CodeAgent()

    # Load latest history and assign it to the agent's history
    loaded_history = load_latest_history()
    if loaded_history:
        code_agent.history = loaded_history
        msg_count = len(loaded_history)
        print(f"[grey50]Loaded {msg_count} messages from previous session.[/grey50]")
    else:
        print("[grey50]Starting new chat session.[/grey50]")

    # Generate a new session ID for saving this session's history
    session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # print(f"[grey50]Current Session ID for saving: {session_id}[/grey50]")

    while True:
        try:
            # Use rich Prompt for input
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            # Handle special commands
            if user_input.startswith("/"):
                command = user_input.lower().strip()

                if command in ["/quit", "/exit"]:
                    print("[bold yellow]Exiting chat session.[/bold yellow]")
                    save_history(session_id, code_agent.history)  # Save agent's history
                    break

                elif command == "/help":
                    print("[bold yellow]Available commands:[/bold yellow]")
                    print("  /help - Show this help message")
                    print("  /clear - Clear conversation history")
                    print("  /exit or /quit - Exit the chat session")
                    print("  /test - Run test mode (for unit testing)")
                    continue

                elif command == "/clear":
                    code_agent.history = []
                    print("[bold yellow]History cleared.[/bold yellow]")
                    continue

                elif command == "/test":
                    print("TEST_SUCCESS")
                    break

                else:
                    print(f"[bold red]Unknown command: {command}[/bold red]")
                    print("Type /help for available commands")
                    continue

            if user_input.lower() in ["quit", "exit"]:
                print("[bold yellow]Exiting chat session.[/bold yellow]")
                save_history(session_id, code_agent.history)  # Save agent's history
                break

            if not user_input:
                print("[yellow]Please enter a non-empty message.[/yellow]")
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
            save_history(session_id, code_agent.history)  # Save history on interrupt
            break
        except Exception as e:
            print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
            save_history(session_id, code_agent.history)  # Attempt to save history on error
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
    print("[bold magenta]Current Effective Configuration " "(CLI > Env > File > Defaults):[/bold magenta]")
    print(config.model_dump_json(indent=2))


@config_app.command("reset")
def config_reset():
    """
    Reset configuration to defaults by copying the template file.
    """
    from code_agent.config.config import (
        DEFAULT_CONFIG_PATH,
        create_default_config_file,
    )

    if DEFAULT_CONFIG_PATH.exists():
        backup_path = DEFAULT_CONFIG_PATH.with_suffix(".yaml.bak")
        try:
            # Create a backup of the existing config
            import shutil

            shutil.copy2(DEFAULT_CONFIG_PATH, backup_path)
            print(f"[yellow]Created backup of existing config at {backup_path}[/yellow]")
        except Exception as e:
            print(f"[red]Warning: Could not create backup: {e}[/red]")

    # Create default config file from template
    create_default_config_file(DEFAULT_CONFIG_PATH)
    print(f"[bold green]Configuration reset to defaults at " f"{DEFAULT_CONFIG_PATH}[/bold green]")
    print("Edit this file to add your API keys or set appropriate environment variables.")


@config_app.command("aistudio")
def config_aistudio():
    """
    Show information about using Google AI Studio as a provider.
    """
    config = get_config()
    api_key = vars(config.api_keys).get("ai_studio")

    console = Console()
    console.print("[bold]Google AI Studio Configuration[/bold]", style="blue")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "ai_studio":
        console.print("✅ AI Studio is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ AI Studio is [yellow]NOT[/yellow] the default provider " f"(currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ AI Studio API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No AI Studio API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://ai.google.dev/[/link] to access Google AI Studio")
    console.print("2. Create an account or sign in")
    console.print("3. Navigate to the API keys section and create a new key")
    console.print("4. Your API key will start with 'aip-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export AI_STUDIO_API_KEY=aip-your-key-here")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print("  Edit ~/.config/code-agent/config.yaml and add:")
    console.print("  api_keys:")
    console.print('    ai_studio: "aip-your-key-here"')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- [bold]gemini-2.0-flash[/bold]: Fast, efficient responses (default)")
    console.print("- [bold]gemini-2.0-pro[/bold]: More capable, better for complex tasks")
    console.print("- [bold]gemini-1.5-flash[/bold]: Previous generation fast model")
    console.print("- [bold]gemini-1.5-pro[/bold]: Previous generation capable model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use AI Studio (default)")
    console.print('code-agent run "What\'s the current Python version?"')

    console.print("\n# Specify a different AI Studio model")
    console.print('code-agent --model gemini-2.0-pro run "Explain quantum computing"')

    # Add usage examples for AI Studio
    console.print("\n# Switch to a different provider")
    console.print("code-agent --provider openai --model gpt-4o run " '"Compare Python and JavaScript"')

    # Show documentation links for AI Studio
    console.print("\n[italic]For more information, see " "https://ai.google.dev/docs[/italic]")


@config_app.command("openai")
def config_openai():
    """
    Show information about using OpenAI as a provider.
    """
    config = get_config()
    api_key = vars(config.api_keys).get("openai")

    console = Console()
    console.print("[bold]OpenAI Configuration[/bold]", style="green")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "openai":
        console.print("✅ OpenAI is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ OpenAI is [yellow]NOT[/yellow] the default provider " f"(currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ OpenAI API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No OpenAI API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://platform.openai.com/api-keys[/link] " "to access OpenAI API keys")
    console.print("2. Create an account or sign in")
    console.print("3. Create a new API key with appropriate permissions")
    console.print("4. Your API key will start with 'sk-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export OPENAI_API_KEY=sk-your-key-here")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print("  Edit ~/.config/code-agent/config.yaml and add:")
    console.print("  api_keys:")
    console.print('    openai: "sk-your-key-here"')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- [bold]gpt-4o[/bold]: Latest advanced model with vision capabilities")
    console.print("- [bold]gpt-4-turbo[/bold]: High-performance model for complex tasks")
    console.print("- [bold]gpt-3.5-turbo[/bold]: Fast, cost-effective for simpler tasks")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use OpenAI as provider")
    console.print("code-agent --provider openai run " '"What\'s the current Python version?"')

    console.print("\n# Specify an OpenAI model")
    console.print("code-agent --provider openai --model gpt-4o run " '"Explain quantum computing"')

    console.print("\n# Set OpenAI as default provider in config.yaml:")
    console.print('default_provider: "openai"')
    console.print('default_model: "gpt-4o"')

    # Usage examples for other providers
    console.print("\n# Switch to a different provider")
    console.print("code-agent --provider openai --model gpt-4o run " '"Compare Python and JavaScript"')

    # Documentation links
    console.print("\n[italic]For more information, see " "https://platform.openai.com/docs/api-reference[/italic]")


@config_app.command("groq")
def config_groq():
    """
    Show information about using Groq as a provider.
    """
    config = get_config()
    api_key = vars(config.api_keys).get("groq")

    console = Console()
    console.print("[bold]Groq Configuration[/bold]", style="magenta")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "groq":
        console.print("✅ Groq is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ Groq is [yellow]NOT[/yellow] the default provider " f"(currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ Groq API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No Groq API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://console.groq.com/keys[/link] to access Groq API keys")
    console.print("2. Create an account or sign in")
    console.print("3. Create a new API key from the console")
    console.print("4. Your API key will start with 'gsk-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export GROQ_API_KEY=gsk-your-key-here")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print("  Edit ~/.config/code-agent/config.yaml and add:")
    console.print("  api_keys:")
    console.print('    groq: "gsk-your-key-here"')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- [bold]llama3-70b-8192[/bold]: Meta's Llama 3 70B model with 8K context")
    console.print("- [bold]llama3-8b-8192[/bold]: Lighter Llama 3 variant, faster response")
    console.print("- [bold]mixtral-8x7b-32768[/bold]: Mixtral model with 32K context window")
    console.print("- [bold]gemma-7b-it[/bold]: Google's Gemma model for instruction-following")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Groq as provider")
    console.print('code-agent --provider groq run "What\'s the current Python version?"')

    # Show examples for Groq
    console.print("\n# Specify a Groq model")
    console.print("code-agent --provider groq --model llama3-70b-8192 run " '"Explain quantum computing"')

    console.print("\n# Set Groq as default provider in config.yaml:")
    console.print('default_provider: "groq"')
    console.print('default_model: "llama3-70b-8192"')

    # Show documentation links
    console.print("\n[italic]For more information, see " "https://console.groq.com/docs/quickstart[/italic]")


@config_app.command("anthropic")
def config_anthropic():
    """
    Show information about using Anthropic as a provider.
    """
    config = get_config()
    api_key = vars(config.api_keys).get("anthropic")

    console = Console()
    console.print("[bold]Anthropic Configuration[/bold]", style="cyan")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "anthropic":
        console.print("✅ Anthropic is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ Anthropic is [yellow]NOT[/yellow] the default provider " f"(currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ Anthropic API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No Anthropic API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://console.anthropic.com/[/link] " "to access Anthropic's console")
    console.print("2. Create an account or sign in")
    console.print("3. Navigate to the API keys section and create a new key")
    console.print("4. Your API key will start with 'sk-ant-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export ANTHROPIC_API_KEY=sk-ant-your-key-here")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print("  Edit ~/.config/code-agent/config.yaml and add:")
    console.print("  api_keys:")
    console.print('    anthropic: "claude-api-key-here"')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- [bold]claude-3-5-sonnet[/bold]: Latest, most capable model")
    console.print("- [bold]claude-3-opus[/bold]: Most powerful model for complex tasks")
    console.print("- [bold]claude-3-sonnet[/bold]: Balanced performance and speed")
    console.print("- [bold]claude-3-haiku[/bold]: Fastest, most efficient model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Anthropic as provider")
    console.print('code-agent --provider anthropic run "What\'s the current Python version?"')

    # Show examples for Anthropic
    console.print("\n# Specify an Anthropic model")
    console.print("code-agent --provider anthropic --model claude-3-sonnet run " '"Explain quantum computing"')

    console.print("\n# Set Anthropic as default provider in config.yaml:")
    console.print('default_provider: "anthropic"')
    console.print('default_model: "claude-3-sonnet"')

    # Show documentation links for Anthropic
    console.print("\n[italic]For more information, see " "https://docs.anthropic.com/claude/reference/getting-started-with-the-api[/italic]")


@config_app.command("ollama")
def config_ollama():
    """
    Show information about using Ollama local models.
    """
    config = get_config()

    console = Console()
    console.print("[bold]Ollama Configuration[/bold]", style="cyan")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "ollama":
        console.print("✅ Ollama is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ Ollama is [yellow]NOT[/yellow] the default provider " f"(currently using: [bold]{config.default_provider}[/bold]).")

    console.print("i Ollama uses local models and doesn't require an API key.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Install Ollama from [link]https://ollama.ai/download[/link]")
    console.print("2. Start the Ollama service:")
    console.print("   [bold]ollama serve[/bold]")
    console.print("3. Pull models you want to use:")
    console.print("   [bold]ollama pull llama3[/bold] or [bold]ollama pull codellama:13b[/bold]")

    # Configuration options
    console.print("\n[bold]Connection Options:[/bold]")
    console.print("[bold yellow]Default:[/bold yellow] Local Ollama service")
    console.print("  Default URL: http://localhost:11434")
    console.print("  You can specify a custom URL when using Ollama commands:")
    console.print("  [bold]code-agent ollama list --url http://custom-host:11434[/bold]")

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- Models vary based on your local installation")
    console.print("- Common examples include:")
    console.print("  - [bold]llama3:latest[/bold]: Meta's Llama 3 model")
    console.print("  - [bold]codellama:13b[/bold]: Specialized for code tasks")
    console.print("  - [bold]gemma3:latest[/bold]: Google's Gemma model")

    # To see your available models, run:
    console.print("\n[bold]To see your available models:[/bold]")
    console.print("code-agent ollama list")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# List available models")
    console.print("code-agent ollama list")

    console.print("\n# Chat with a model")
    console.print('code-agent ollama chat llama3:latest "Explain quantum computing"')

    console.print("\n# Use a system prompt")
    console.print('code-agent ollama chat codellama:13b "Write a sort function" --system "You are a helpful coding assistant"')

    # Show documentation links
    console.print("\n[italic]For more information, see " "https://github.com/jmorganca/ollama/blob/main/docs/api.md[/italic]")
    console.print("[italic]Or see our documentation: docs/ollama_integration.md[/italic]")


@config_app.command("validate")
def config_validate(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed validation results even if valid."),
    ] = False,
):
    """
    Validate the current configuration and show any errors or warnings.

    This checks for:
    - Model compatibility with selected provider
    - API key format and presence
    - Security of command allowlist patterns
    - Other security concerns and best practices
    """
    from code_agent.config.config import validate_config

    # Use the new validation function
    is_valid = validate_config(verbose=verbose)

    # Return exit code based on validation result
    if not is_valid:
        raise typer.Exit(code=1)


# --- Provider Commands ---
provider_app = typer.Typer(name="providers", help="Manage providers.")
app.add_typer(provider_app)


@provider_app.command("list")
def providers_list():
    """
    List available/configured providers based on effective config.
    """
    config = get_config()
    console = Console()

    console.print("[bold cyan]Configured LLM Providers:[/bold cyan]")
    console.print("=" * 50)

    # Define provider details
    providers = {
        "ai_studio": {
            "name": "Google AI Studio",
            "style": "blue",
            "config_cmd": "code-agent config aistudio",
            "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "key_prefix": "aip-",
            "env_var": "AI_STUDIO_API_KEY",
        },
        "openai": {
            "name": "OpenAI",
            "style": "green",
            "config_cmd": "code-agent config openai",
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "key_prefix": "sk-",
            "env_var": "OPENAI_API_KEY",
        },
        "groq": {
            "name": "Groq",
            "style": "magenta",
            "config_cmd": "code-agent config groq",
            "models": ["llama3-70b-8192", "mixtral-8x7b-32768"],
            "key_prefix": "gsk-",
            "env_var": "GROQ_API_KEY",
        },
        "anthropic": {
            "name": "Anthropic",
            "style": "cyan",
            "config_cmd": "code-agent config anthropic",
            "models": [
                "claude-3-5-sonnet",
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
            ],
            "key_prefix": "sk-ant-",
            "env_var": "ANTHROPIC_API_KEY",
        },
    }

    found_configured = False

    # Current default indicator
    console.print(f"[bold]Current Default:[/bold] " f"{config.default_provider} / {config.default_model}")
    console.print()

    # List all providers with their status
    console.print("[bold]Available Providers:[/bold]")
    for provider_id, details in providers.items():
        api_key = vars(config.api_keys).get(provider_id)  # Access directly through vars()
        name = details["name"]
        style = details["style"]

        if api_key:
            status = "[bold green]✓ Configured[/bold green]"
            found_configured = True
        else:
            status = "[yellow]✗ Not configured[/yellow]"

        # Is this the default?
        default_marker = ""
        if provider_id == config.default_provider:
            default_marker = " [bold green](DEFAULT)[/bold green]"

        console.print(f"[bold {style}]{name}[/bold {style}]: {status}{default_marker}")

        # Show configuration command
        console.print(f"  Setup command: [dim]{details['config_cmd']}[/dim]")

        # Show example model if it's configured
        if api_key and details["models"]:
            example_model = details["models"][0]
            cmd_example = f"code-agent --provider {provider_id} " f'--model {example_model} run "..."'
            console.print(f"  Example: [dim]{cmd_example}[/dim]")

        console.print()

    if not found_configured:
        console.print("\n[bold yellow]No providers found with configured API keys.[/bold yellow]")
        console.print("Run one of the following commands to set up a provider:")
        for _, details in providers.items():
            console.print(f"  [dim]{details['config_cmd']}[/dim]")

    # Usage tips section
    console.print("\n[bold]Quick Usage Tips:[/bold]")
    console.print("- Override provider for one command: " "[dim]--provider <provider> --model <model>[/dim]")
    console.print("- Set default provider in config: " "[dim]code-agent config show[/dim] to see current config")
    console.print("- Reset config to defaults: [dim]code-agent config reset[/dim]")


if __name__ == "__main__":
    app()
