import sys
from typing import Optional

import google.generativeai as genai
import typer
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.prompt import Prompt
from typing_extensions import Annotated

# Local application imports
from code_agent import __version__ as agent_version

# Updated imports
# from code_agent.agent.agent import CodeAgent  # REMOVED old agent import
from code_agent.agent.multi_agent import get_root_agent  # IMPORT new root agent
from code_agent.config import get_config, initialize_config

# from code_agent.config.config import DEFAULT_CONFIG_DIR, get_config, initialize_config

# Load environment variables first (e.g., from .env)
load_dotenv()

# Correct Imports (should already be here or moved)
# from code_agent.adk.client import ADKClient # Assumed correct import
# from code_agent.adk.models_v2 import create_model # Assumed correct import
# from code_agent.config import initialize_config, get_config # Assumed correct import
# from code_agent.config.settings_based_config import CodeAgentSettings # Assumed correct import
# from code_agent.agent.cli_runner import ADKWorkflowRunner # Assumed correct import
# from code_agent.agent.cli_agent import cli_agent # Assumed correct import
# from code_agent.adk.services import get_adk_session_manager # Assumed correct import
# from code_agent.verbosity import set_verbosity_level, get_verbosity_level # Assumed correct import
# from code_agent.utils import ( # Assumed correct import
#     print_panel,
#     display_session_history,
#     get_default_config_path,
#     load_yaml_config,
#     detect_environment,
# )

# Assuming these are the actual correct imports based on typical structure
# We rely on Ruff to have moved these correctly if possible, or verify later
# Explicitly configure the API key for the models

# Remove nest_asyncio import and apply

# Add ADK version import
try:
    import google.adk as adk
    from google.adk.events import Event
    from google.adk.runners import Runner
    from google.adk.sessions import BaseSessionService, InMemorySessionService

    # Import content types for creating events
    from google.genai import types as genai_types

    adk_version = adk.__version__
except ImportError:
    adk_version = "not installed"

    # Define dummy classes if ADK is not installed to avoid NameErrors later
    class Runner:
        pass

    class InMemorySessionService:
        pass

    class BaseSessionService:
        pass

    class Event:
        pass

    class genai_types:  # Dummy class
        class Content:
            pass

        class Part:
            pass

# Import Ollama commands
# try:
#     from cli_agent.commands.ollama import app as ollama_app
# except ImportError:
#     ollama_app = None

app = typer.Typer(
    name="code-agent",  # Updated app name
    help="CLI agent for interacting with LLMs and local environment.",
    add_completion=True,
    no_args_is_help=True,  # Show help when no arguments are provided
)

# Add Ollama commands if available
# if ollama_app:
#     app.add_typer(ollama_app, name="ollama", help="Interact with Ollama models")


# --- Global Options/State ---
class GlobalState:
    def __init__(self):
        self.provider: Optional[str] = None
        self.model: Optional[str] = None
        # Remove test_mode_agent as the old agent is gone
        # self.test_mode_agent: Optional[CodeAgent] = None


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
    verbosity: Annotated[
        Optional[int],
        typer.Option(
            "--verbosity",
            help="Set output verbosity (0=quiet, 1=normal, 2=verbose, 3=debug).",
        ),
    ] = None,
    quiet: Annotated[
        Optional[bool],
        typer.Option(
            "--quiet",
            "-q",
            help="Minimal output (equivalent to --verbosity=0).",
        ),
    ] = None,
    verbose: Annotated[
        Optional[bool],
        typer.Option(
            "--verbose",
            help="Increased output verbosity (equivalent to --verbosity=2).",
        ),
    ] = None,
    debug: Annotated[
        Optional[bool],
        typer.Option(
            "--debug",
            "-d",
            help="Debug output level (equivalent to --verbosity=3).",
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
    # DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Determine effective verbosity level from all options
    effective_verbosity = None
    if quiet:
        effective_verbosity = 0
    elif debug:
        effective_verbosity = 3
    elif verbose:
        effective_verbosity = 2
    elif verbosity is not None:
        effective_verbosity = max(0, min(3, verbosity))  # Clamp to 0-3 range

    # Initialize configuration singleton, applying CLI overrides
    initialize_config(
        cli_provider=provider,
        cli_model=model,
        cli_auto_approve_edits=auto_approve_edits,
        cli_auto_approve_native_commands=auto_approve_native_commands,
    )

    # Set verbosity level if specified
    if effective_verbosity is not None:
        from code_agent.verbosity import VerbosityLevel, get_controller

        controller = get_controller()

        # Map int to enum
        for level in VerbosityLevel:
            if level.value == effective_verbosity:
                controller.set_level(level)
                break

    # Store CLI options in state for potential direct use (optional)
    # state.provider = provider
    # These might not be needed if get_config() is always used
    # state.model = model

    # --- ADD API KEY CONFIGURATION LOGIC HERE --- #
    config = get_config()  # Get the fully processed config

    # Configure Google Generative AI based on the effective config
    # Try GOOGLE_API_KEY first, then AI_STUDIO_API_KEY
    # Access keys directly from the main config object, as dotenv loads them there
    google_api_key_val = config.google_api_key or config.ai_studio_api_key
    if google_api_key_val:
        # Determine which key was used for the message
        key_source = "GOOGLE_API_KEY" if config.google_api_key else "AI_STUDIO_API_KEY"
        print(f"Initializing Google Generative AI with API key from {key_source}")
        genai.configure(api_key=google_api_key_val)
    else:
        # Only warn if a Google provider is likely intended
        if config.default_provider in ["google", "ai_studio", "vertexai"]:
            print("WARNING: No Google API key found (GOOGLE_API_KEY or AI_STUDIO_API_KEY).")
            print("         Google models may not work without an API key or appropriate ADC.")
        # Note: Other providers (OpenAI, Anthropic, etc.) are configured via litellm


# --- Helper Callbacks ---
def _version_callback(value: bool):
    if value:
        console = Console()
        console.print(f"Code Agent version: {agent_version}")  # Updated output message
        console.print(f"Google ADK version: {adk_version}")  # Show ADK version
        raise typer.Exit()


# --- Commands ---
@app.command()
def chat(
    # Verbosity options are handled by the main callback now
    # No need to repeat them here unless specific overrides are needed for chat
):
    """
    Start an interactive chat session using the ADK multi-agent system.
    """
    # Get the verbosity controller
    from code_agent.verbosity import get_controller

    verbosity_controller = get_controller()

    if adk_version == "not installed":
        verbosity_controller.show_error("Google ADK is not installed. Please install it to use the chat feature.")
        raise typer.Exit(code=1)

    verbosity_controller.show_normal("[bold green]Starting ADK-based interactive chat session...[/bold green]")
    verbosity_controller.show_normal("Type 'quit' or 'exit' to end the session.")
    verbosity_controller.show_normal("Special commands: /help for assistance, /clear to clear history")

    # IMPORTANT NOTE: This is a simplified implementation that uses ADK's session management
    # but directly calls the model API instead of using the full ADK agent system.
    # We're doing this because the full ADK system has issues with asyncio operations in the CLI context.
    # A more comprehensive implementation would use the ADK Runner.run_async with proper async handling.

    # Initialize ADK components - use a fully synchronous approach
    verbosity_controller.show_verbose("Initializing ADK components...")
    session_service = InMemorySessionService()
    root_agent = get_root_agent()

    # Create a new session
    current_session = session_service.create_session(app_name="code_agent", user_id="cli_user")
    current_session_id = current_session.id
    verbosity_controller.show_verbose(f"Created ADK session: {current_session_id}")

    console = Console()

    # Check if stdin is a TTY
    is_interactive = sys.stdin.isatty()

    # Read all lines at once if not interactive
    non_interactive_lines = []
    if not is_interactive:
        non_interactive_lines = sys.stdin.readlines()
        if not non_interactive_lines:
            verbosity_controller.show_verbose("No input detected from stdin.")

    line_index = 0

    try:
        while True:
            try:
                if is_interactive:
                    # Interactive mode, prompt for input
                    user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                else:
                    # Non-interactive mode, read from stdin
                    if line_index < len(non_interactive_lines):
                        user_input = non_interactive_lines[line_index].strip()
                        line_index += 1
                        verbosity_controller.show_verbose(f"Processing input: {user_input}")
                    else:
                        # No more lines to process in non-interactive mode
                        break

                # Process command formatting for /help command
                if user_input.startswith("/"):
                    command = user_input[1:].strip().lower()
                    if command == "help":
                        console.print("[bold magenta]Available Commands:[/bold magenta]")
                        console.print("/clear - Clear conversation history (starts a new session)")
                        console.print("/help  - Show this help message")
                        console.print("/quit or /exit - End the chat session")
                        console.print("\n[bold magenta]Available Tools:[/bold magenta]")
                        console.print("The assistant can describe these capabilities, but the CLI implementation has limited support:")
                        console.print("- Web search: Ask about current events or information")
                        console.print("- File operations: Ask about reading files or directories")
                        console.print("- Terminal commands: Ask about running commands")
                        console.print("- Memory: The assistant will remember information from your conversation")
                        console.print("\n[bold yellow]Note:[/bold yellow] This implementation has limited tool support. For full functionality,")
                        console.print("use the agent API directly or the web interface.")
                        continue
                    elif command == "clear":
                        # Create a new session when history is cleared
                        current_session = session_service.create_session(app_name="code_agent", user_id="cli_user")
                        current_session_id = current_session.id
                        console.print("[bold green]History cleared. New session started.[/bold green]")
                        verbosity_controller.show_verbose(f"Created new ADK session: {current_session_id}")
                        continue
                    elif command in ["quit", "exit"]:
                        console.print("[bold green]Goodbye![/bold green]")
                        break
                    else:
                        console.print(f"[bold red]Unknown command: {command}[/bold red]")
                        continue

                if user_input.lower() in ["quit", "exit"]:
                    console.print("[bold green]Goodbye![/bold green]")
                    break

                if not user_input:
                    console.print("[yellow]Please enter a non-empty message.[/yellow]")
                    continue

                # Create content object for user message
                message_content = genai_types.Content(parts=[genai_types.Part(text=user_input)])

                print("\n[bold yellow]Agent:[/bold yellow]")

                # Add the user message manually to avoid duplicate messages
                user_event = Event(author="user", content=message_content)
                session_service.append_event(session=current_session, event=user_event)

                # Run the model in a non-streaming way
                try:
                    with console.status("[bold green]Thinking...[/bold green]"):
                        # Create a new Runner for each request to avoid event loop issues
                        runner = Runner(session_service=session_service, app_name="code_agent", agent=root_agent)
                        # Make sure we call run on the runner instance with required parameters
                        runner.run(user_id="cli_user", session_id=current_session_id, new_message=message_content)
                except Exception as e:
                    print(f"[bold red]Error while getting response:[/bold red] {e}")
                    import traceback

                    traceback.print_exc()
                    response_text = f"Error: {e!s}"

                    # Create a minimal error response to ensure the conversation can continue
                    assistant_event = Event(author="assistant", content=genai_types.Content(parts=[genai_types.Part(text=response_text)]))
                    session_service.append_event(session=current_session, event=assistant_event)
            except KeyboardInterrupt:
                # Graceful exit on Ctrl+C
                console.print("\n[bold yellow]Interrupted. Exiting chat session.[/bold yellow]")
                break

        # Always print goodbye message when exiting
        console.print("[bold green]Thank you for using the chat interface![/bold green]")

    except Exception as e:
        # Last-resort error handling
        verbosity_controller.show_error(f"Unexpected error: {e!s}")
        import traceback

        traceback.print_exc()
        raise typer.Exit(code=1) from e


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
    print("[bold magenta]Current Effective Configuration (CLI > Env > File > Defaults):[/bold magenta]")
    print(config.model_dump_json(indent=2))


@config_app.command("reset")
def config_reset():
    """
    Reset configuration to defaults by copying the template file.
    """
    from code_agent.config.config import (
        DEFAULT_CONFIG_DIR,
        DEFAULT_CONFIG_PATH,
        TEMPLATE_CONFIG_PATH,
    )

    # Copy template to config path
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
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Copy the template to the config path
    import shutil

    shutil.copy2(TEMPLATE_CONFIG_PATH, DEFAULT_CONFIG_PATH)
    print(f"[bold green]Configuration reset to defaults at {DEFAULT_CONFIG_PATH}[/bold green]")
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
        console.print(f"❌ AI Studio is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

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
    console.print("- [bold]gemini-1.5-flash-latest[/bold]: Fast, efficient responses (default)")
    console.print("- [bold]gemini-1.5-pro-latest[/bold]: More capable, better for complex tasks")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use AI Studio (default)")
    console.print("code-agent chat")  # Chat command is now interactive

    console.print("\n# Specify a different AI Studio model (via config or env var)")
    console.print("# Edit config.yaml: default_model: gemini-1.5-pro-latest")
    console.print("code-agent chat")

    # Add usage examples for AI Studio
    console.print("\n# Switch to a different provider (via config or env var)")
    console.print("# Edit config.yaml: default_provider: openai")
    console.print("code-agent chat")

    # Show documentation links for AI Studio
    console.print("\n[italic]For more information, see https://ai.google.dev/docs[/italic]")


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
        console.print(f"❌ OpenAI is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ OpenAI API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No OpenAI API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://platform.openai.com/api-keys[/link] to access OpenAI API keys")
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
    console.print("# Use OpenAI as provider (by setting default_provider in config)")
    console.print("code-agent chat")

    console.print("\n# Set OpenAI as default provider in config.yaml:")
    console.print('default_provider: "openai"')
    console.print('default_model: "gpt-4o"')
    console.print("code-agent chat")

    # Documentation links
    console.print("\n[italic]For more information, see https://platform.openai.com/docs/api-reference[/italic]")


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
        console.print(f"❌ Groq is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

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
    console.print("# Use Groq as provider (by setting default_provider in config)")
    console.print("code-agent chat")

    console.print("\n# Set Groq as default provider in config.yaml:")
    console.print('default_provider: "groq"')
    console.print('default_model: "llama3-70b-8192"')
    console.print("code-agent chat")

    # Show documentation links
    console.print("\n[italic]For more information, see https://console.groq.com/docs/quickstart[/italic]")


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
        console.print(f"❌ Anthropic is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ Anthropic API key is [bold green]configured[/bold green].")
    else:
        console.print("❌ No Anthropic API key [red]found[/red] in config or environment.")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://console.anthropic.com/[/link] to access Anthropic's console")
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
    console.print("- [bold]claude-3-5-sonnet-20240620[/bold]: Latest, most capable model")
    console.print("- [bold]claude-3-opus-20240229[/bold]: Most powerful model for complex tasks")
    console.print("- [bold]claude-3-sonnet-20240229[/bold]: Balanced performance and speed")
    console.print("- [bold]claude-3-haiku-20240307[/bold]: Fastest, most efficient model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Anthropic as provider (by setting default_provider in config)")
    console.print("code-agent chat")

    console.print("\n# Set Anthropic as default provider in config.yaml:")
    console.print('default_provider: "anthropic"')
    console.print('default_model: "claude-3-5-sonnet-20240620"')
    console.print("code-agent chat")

    # Show documentation links for Anthropic
    console.print("\n[italic]For more information, see https://docs.anthropic.com/claude/reference/getting-started-with-the-api[/italic]")


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
        console.print(f"❌ Ollama is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

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
    console.print("  You can configure a custom URL in config.yaml:")
    console.print("  ollama:")
    console.print('    url: "http://custom-host:11434"')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- Models vary based on your local installation")
    console.print("- Common examples include:")
    console.print("  - [bold]llama3:latest[/bold]: Meta's Llama 3 model")
    console.print("  - [bold]codellama:13b[/bold]: Specialized for code tasks")
    console.print("  - [bold]gemma3:latest[/bold]: Google's Gemma model")

    # To see your available models, run:
    console.print("\n[bold]To see your available models:[/bold]")
    console.print("ollama list")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Ollama (by setting default_provider in config)")
    console.print("code-agent chat")

    console.print("\n# Set Ollama as default provider in config.yaml:")
    console.print('default_provider: "ollama"')
    console.print('default_model: "llama3:latest"')
    console.print("code-agent chat")

    # Show documentation links
    console.print("\n[italic]For more information, see https://github.com/jmorganca/ollama/blob/main/docs/api.md[/italic]")
    console.print("[italic]Or see our documentation: docs/feature_ollama_integration.md[/italic]")


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


@config_app.command("verbosity")
def config_verbosity(
    level: Annotated[
        Optional[str],
        typer.Argument(
            help="Verbosity level to set (0-3, QUIET, NORMAL, VERBOSE, DEBUG). If not provided, shows current setting.",
        ),
    ] = None,
):
    """
    Set or display the output verbosity level.
    """
    from code_agent.verbosity import VerbosityLevel, get_controller

    controller = get_controller()
    config = get_config()

    if level is None:
        # Display current verbosity
        print(f"[bold]Current verbosity:[/bold] {controller.level_name} ({controller.level_value})")
        print("\n[bold]Available levels:[/bold]")
        for available_level in VerbosityLevel:
            current = "✓ " if controller.level == available_level else "  "
            print(f"{current}[bold]{available_level.name}[/bold] ({available_level.value}) - ", end="")

            if available_level == VerbosityLevel.QUIET:
                print("Only essential information and errors")
            elif available_level == VerbosityLevel.NORMAL:
                print("Standard information for users")
            elif available_level == VerbosityLevel.VERBOSE:
                print("Additional details and warnings")
            elif available_level == VerbosityLevel.DEBUG:
                print("Detailed diagnostic information")

        print("\n[bold]Usage examples:[/bold]")
        print("code-agent config verbosity VERBOSE   # Set to verbose mode")
        print("code-agent config verbosity 3         # Set to debug level (highest)")
        print("code-agent config verbosity 0         # Set to quiet mode (lowest)")
    else:
        # Set the verbosity level
        result = controller.set_level_from_string(level)

        # Update config for consistency
        config.verbosity = controller.level_value

        print(f"[bold green]{result}[/bold green]")

        # Show examples of what will be displayed at this level
        if controller.level == VerbosityLevel.QUIET:
            print("\n[bold yellow]At QUIET level:[/bold yellow]")
            print("• Only errors and essential information will be shown")
            print("• Most status messages and warnings will be hidden")
        elif controller.level == VerbosityLevel.NORMAL:
            print("\n[bold yellow]At NORMAL level:[/bold yellow]")
            print("• Standard user information will be shown")
            print("• Progress indicators and basic status messages")
            print("• Errors and important warnings")
        elif controller.level == VerbosityLevel.VERBOSE:
            print("\n[bold yellow]At VERBOSE level:[/bold yellow]")
            print("• Detailed information about operations")
            print("• All warnings and status messages")
            print("• Tool call details and responses")
        elif controller.level == VerbosityLevel.DEBUG:
            print("\n[bold yellow]At DEBUG level:[/bold yellow]")
            print("• All diagnostic information")
            print("• Internal state and detailed execution flow")
            print("• Timestamps and full message details")

        print("\n[bold green]Tip:[/bold green] You can also set verbosity using the tools in a chat session:")
        print('set_verbosity(level: "VERBOSE")   # From within a chat')


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
            "models": ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest"],  # Updated model names
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
                "claude-3-5-sonnet-20240620",  # Updated model name
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "key_prefix": "sk-ant-",
            "env_var": "ANTHROPIC_API_KEY",
        },
        "ollama": {  # Added Ollama to the list
            "name": "Ollama (Local)",
            "style": "yellow",
            "config_cmd": "code-agent config ollama",
            "models": ["(local models)", "llama3", "codellama"],
            "key_prefix": "N/A",
            "env_var": "N/A",
        },
    }

    found_configured = False

    # Current default indicator
    console.print(f"[bold]Current Default:[/bold] {config.default_provider} / {config.default_model}")
    console.print()

    # List all providers with their status
    console.print("[bold]Available Providers:[/bold]")
    for provider_id, details in providers.items():
        if provider_id == "ollama":
            # Ollama doesn't use API keys, check if it's the default
            api_key = True  # Treat as configured if Ollama is selected
        else:
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
            details["models"][0]
            # Adjust command example for interactive chat
            cmd_example = "# Set default provider/model in config and run: code-agent chat"
            console.print(f"  Example Usage: [dim]{cmd_example}[/dim]")

        console.print()

    if not found_configured and config.default_provider != "ollama":  # Check Ollama specifically
        console.print("\n[bold yellow]No cloud providers found with configured API keys.[/bold yellow]")
        console.print("Run one of the following commands to set up a provider:")
        for pid, details in providers.items():
            if pid != "ollama":
                console.print(f"  [dim]{details['config_cmd']}[/dim]")

    # Usage tips section
    console.print("\n[bold]Quick Usage Tips:[/bold]")
    console.print("- Set default provider/model in config: [dim]code-agent config show[/dim]")
    console.print("- Reset config to defaults: [dim]code-agent config reset[/dim]")
    console.print("- Start interactive chat: [dim]code-agent chat[/dim]")


if __name__ == "__main__":
    app()
