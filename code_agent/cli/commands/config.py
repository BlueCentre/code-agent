"""
This module contains the commands for the config sub-app.
"""

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint  # Use rprint to avoid conflict with built-in print
from rich.console import Console
from typing_extensions import Annotated

from code_agent.cli.utils import load_config_data, save_config_data  # Import yaml helpers

# Local application imports
from code_agent.config import (
    get_api_key,
    get_config,
)

# Import specific paths from the settings_based_config module
from code_agent.config.settings_based_config import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_CONFIG_PATH,
    TEMPLATE_CONFIG_PATH,
)
from code_agent.verbosity import VerbosityLevel, get_controller

# --- Constants ---
LEVEL_HELP = "Verbosity level (0-3, QUIET, NORMAL, VERBOSE, DEBUG)."
LEVEL_ARG = typer.Argument(help=LEVEL_HELP)
PATH_HELP = "Path to the Python module containing the agent definition."

# --- Config Sub-App ---
config_app = typer.Typer(name="config", help="Manage configuration.")


@config_app.command("show")
def config_show():
    """
    Show the current effective configuration.
    """
    config = get_config()  # Assumes config is already initialized
    rprint("[bold magenta]Current Effective Configuration (CLI > Env > File > Defaults):[/bold magenta]")
    # Use model_dump_json for Pydantic v2
    rprint(config.model_dump_json(indent=2))


@config_app.command("reset")
def config_reset():
    """
    Reset configuration to defaults by copying the template file.
    """
    console = Console()
    # Ensure template exists
    if not TEMPLATE_CONFIG_PATH.exists():
        console.print(f"[bold red]Error:[/bold red] Template config file not found at {TEMPLATE_CONFIG_PATH}")
        raise typer.Exit(code=1)

    # Create a backup if the current config exists
    if DEFAULT_CONFIG_PATH.exists():
        backup_path = DEFAULT_CONFIG_PATH.with_suffix(".yaml.bak")
        try:
            shutil.copy2(DEFAULT_CONFIG_PATH, backup_path)
            console.print(f"[yellow]Created backup of existing config at {backup_path}[/yellow]")
        except Exception as e:
            console.print(f"[red]Warning: Could not create backup: {e}[/red]")

    # Copy template to the default config path
    try:
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE_CONFIG_PATH, DEFAULT_CONFIG_PATH)
        console.print(f"[bold green]Configuration reset to defaults at {DEFAULT_CONFIG_PATH}[/bold green]")
        console.print("Edit this file to add your API keys or set appropriate environment variables.")
    except Exception as e:
        console.print(f"[bold red]Error resetting configuration: {e}[/bold red]")
        raise typer.Exit(code=1) from e


@config_app.command("aistudio")
def config_aistudio():
    """
    Show information about using Google AI Studio as a provider.
    """
    config = get_config()
    # Use the helper function from config module

    api_key = get_api_key("ai_studio")

    console = Console()
    console.print("[bold]Google AI Studio Configuration[/bold]", style="blue")
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "ai_studio":  # Access nested llm config
        console.print("✅ AI Studio is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ AI Studio is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

    if api_key:
        console.print("✅ AI Studio API key is [bold green]configured[/bold green] (found via config or env)." + (" (masked)" if len(api_key) > 8 else ""))
    else:
        console.print("❌ No AI Studio API key [red]found[/red] in config or environment (AI_STUDIO_API_KEY).")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link=https://aistudio.google.com/app/apikey]https://aistudio.google.com/app/apikey[/link] to get an API key.")
    console.print("2. Create an account or sign in")
    console.print("3. Navigate to the API keys section and create a new key")
    console.print("4. Your API key will likely start with 'AIza...'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export AI_STUDIO_API_KEY=AIzaYourKeyHere")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print(f"  Edit [dim]{DEFAULT_CONFIG_PATH}[/dim] and add:")
    console.print("  api_keys:")
    console.print('    ai_studio: "AIzaYourKeyHere"')

    # Available models
    console.print("\n[bold]Available Models (Examples):[/bold]")
    console.print("- [bold]gemini-1.5-flash-latest[/bold]: Fast, efficient responses (default in template)")
    console.print("- [bold]gemini-1.5-pro-latest[/bold]: More capable, better for complex tasks")
    console.print("- [bold]gemini-1.0-pro[/bold]: Stable older version")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use AI Studio (if set as default in config/env)")
    console.print('code-agent run "Your instruction..."')

    console.print("\n# Override provider/model via CLI")
    console.print('code-agent run "Your instruction..." --provider ai_studio --model gemini-1.5-pro-latest')

    console.print("\n# Set as default in config.yaml:")
    console.print('default_provider: "ai_studio"')
    console.print('default_model: "gemini-1.5-flash-latest"')

    # Show documentation links for AI Studio
    console.print("\n[italic]For more information, see https://ai.google.dev/docs[/italic]")


@config_app.command("openai")
def config_openai():
    """
    Show information about using OpenAI as a provider.
    """
    config = get_config()

    api_key = get_api_key("openai")

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
        console.print("✅ OpenAI API key is [bold green]configured[/bold green] (found via config or env)." + (" (masked)" if len(api_key) > 8 else ""))
    else:
        console.print("❌ No OpenAI API key [red]found[/red] in config or environment (OPENAI_API_KEY).")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://platform.openai.com/api-keys[/link] to get an API key.")
    console.print("2. Create a new API key with appropriate permissions.")
    console.print("3. Your API key will start with 'sk-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export OPENAI_API_KEY=sk-YourKeyHere")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print(f"  Edit [dim]{DEFAULT_CONFIG_PATH}[/dim] and add:")
    console.print("  api_keys:")
    console.print('    openai: "sk-YourKeyHere"')

    # Available models
    console.print("\n[bold]Available Models (Examples):[/bold]")
    console.print("- [bold]gpt-4o[/bold]: Latest advanced model")
    console.print("- [bold]gpt-4-turbo[/bold]: High-performance model")
    console.print("- [bold]gpt-3.5-turbo[/bold]: Fast, cost-effective model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use OpenAI (if set as default in config/env)")
    console.print('code-agent run "Your instruction..."')

    console.print("\n# Override provider/model via CLI")
    console.print('code-agent run "Your instruction..." --provider openai --model gpt-4o')

    console.print("\n# Set as default in config.yaml:")
    console.print('default_provider: "openai"')
    console.print('default_model: "gpt-4o"')

    # Documentation links
    console.print("\n[italic]For more information, see https://platform.openai.com/docs/api-reference[/italic]")


@config_app.command("groq")
def config_groq():
    """
    Show information about using Groq as a provider.
    """
    config = get_config()

    api_key = get_api_key("groq")

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
        console.print("✅ Groq API key is [bold green]configured[/bold green] (found via config or env)." + (" (masked)" if len(api_key) > 8 else ""))
    else:
        console.print("❌ No Groq API key [red]found[/red] in config or environment (GROQ_API_KEY).")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://console.groq.com/keys[/link] to get an API key.")
    console.print("2. Create a new API key from the console.")
    console.print("3. Your API key will start with 'gsk-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export GROQ_API_KEY=gsk-YourKeyHere")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print(f"  Edit [dim]{DEFAULT_CONFIG_PATH}[/dim] and add:")
    console.print("  api_keys:")
    console.print('    groq: "gsk-YourKeyHere"')

    # Available models
    console.print("\n[bold]Available Models (Examples):[/bold]")
    console.print("- [bold]llama3-70b-8192[/bold]: Llama 3 70B model")
    console.print("- [bold]llama3-8b-8192[/bold]: Llama 3 8B model")
    console.print("- [bold]mixtral-8x7b-32768[/bold]: Mixtral MoE model")
    console.print("- [bold]gemma-7b-it[/bold]: Google's Gemma model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Groq (if set as default in config/env)")
    console.print('code-agent run "Your instruction..."')

    console.print("\n# Override provider/model via CLI")
    console.print('code-agent run "Your instruction..." --provider groq --model llama3-70b-8192')

    console.print("\n# Set as default in config.yaml:")
    console.print('default_provider: "groq"')
    console.print('default_model: "llama3-70b-8192"')

    # Show documentation links
    console.print("\n[italic]For more information, see https://console.groq.com/docs/quickstart[/italic]")


@config_app.command("anthropic")
def config_anthropic():
    """
    Show information about using Anthropic as a provider.
    """
    config = get_config()

    api_key = get_api_key("anthropic")

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
        console.print("✅ Anthropic API key is [bold green]configured[/bold green] (found via config or env)." + (" (masked)" if len(api_key) > 8 else ""))
    else:
        console.print("❌ No Anthropic API key [red]found[/red] in config or environment (ANTHROPIC_API_KEY).")

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Visit [link]https://console.anthropic.com/settings/keys[/link] to get an API key.")
    console.print("2. Create a new API key.")
    console.print("3. Your API key will start with 'sk-ant-'")

    # Configuration options
    console.print("\n[bold]Configuration Options:[/bold]")
    console.print("[bold yellow]Option 1:[/bold yellow] Set environment variable")
    console.print("  export ANTHROPIC_API_KEY=sk-ant-YourKeyHere")

    console.print("[bold yellow]Option 2:[/bold yellow] Add to config file")
    console.print(f"  Edit [dim]{DEFAULT_CONFIG_PATH}[/dim] and add:")
    console.print("  api_keys:")
    console.print('    anthropic: "sk-ant-YourKeyHere"')

    # Available models
    console.print("\n[bold]Available Models (Examples):[/bold]")
    console.print("- [bold]claude-3-5-sonnet-20240620[/bold]: Latest Sonnet model")
    console.print("- [bold]claude-3-opus-20240229[/bold]: Most powerful model")
    console.print("- [bold]claude-3-sonnet-20240229[/bold]: Balanced performance model")
    console.print("- [bold]claude-3-haiku-20240307[/bold]: Fastest model")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Anthropic (if set as default in config/env)")
    console.print('code-agent run "Your instruction..."')

    console.print("\n# Override provider/model via CLI")
    console.print('code-agent run "Your instruction..." --provider anthropic --model claude-3-5-sonnet-20240620')

    console.print("\n# Set as default in config.yaml:")
    console.print('default_provider: "anthropic"')
    console.print('default_model: "claude-3-opus-20240229"')

    # Show documentation links for Anthropic
    console.print("\n[italic]For more information, see https://docs.anthropic.com/claude/reference/getting-started-with-the-api[/italic]")


@config_app.command("ollama")
def config_ollama():
    """
    Show information about using Ollama local models.
    """
    config = get_config()
    console = Console()

    console.print("[bold]Ollama Configuration[/bold]", style="yellow")  # Changed style
    console.print("=" * 50)

    # Status information
    console.print("[bold]Current Status:[/bold]")
    if config.default_provider == "ollama":
        console.print("✅ Ollama is currently the [bold green]default provider[/bold green].")
    else:
        console.print(f"❌ Ollama is [yellow]NOT[/yellow] the default provider (currently using: [bold]{config.default_provider}[/bold]).")

    console.print("ℹ️ Ollama uses local models and doesn't require an API key.")  # noqa: RUF001

    # Setup instructions
    console.print("\n[bold]Setup Instructions:[/bold]")
    console.print("1. Install Ollama from [link]https://ollama.ai/download[/link]")
    console.print("2. Start the Ollama service (usually runs automatically after install)")
    console.print("   If needed, run: [bold]ollama serve[/bold]")
    console.print("3. Pull models you want to use:")
    console.print("   [bold]ollama pull llama3[/bold] (Example)")
    console.print("   [bold]ollama pull codellama:13b[/bold] (Example with tag)")

    # Configuration options
    console.print("\n[bold]Connection Options:[/bold]")
    # Access ollama specific config if defined, otherwise use defaults
    ollama_url = config.ollama.url if config.ollama else "http://localhost:11434"
    console.print(f"  Currently configured URL: [cyan]{ollama_url}[/cyan]")
    console.print("  Default URL: http://localhost:11434")
    console.print(f"  To customize, edit [dim]{DEFAULT_CONFIG_PATH}[/dim] and add/modify:")
    console.print("  ollama:")
    console.print('    url: "http://custom-host:11434" # Your custom URL')

    # Available models
    console.print("\n[bold]Available Models:[/bold]")
    console.print("- Models depend on your local Ollama installation.")
    console.print("- Common examples include:")
    console.print("  - [bold]llama3:latest[/bold]")
    console.print("  - [bold]codellama:13b[/bold]")
    console.print("  - [bold]phi3:medium[/bold]")
    console.print("  - [bold]gemma:latest[/bold]")
    console.print("\nRun [bold]ollama list[/bold] in your terminal to see installed models.")

    # Usage examples
    console.print("\n[bold]Usage Examples:[/bold]")
    console.print("# Use Ollama (if set as default in config/env)")
    console.print('code-agent run "Your instruction..."')

    console.print("\n# Override provider/model via CLI")
    console.print('code-agent run "Your instruction..." --provider ollama --model codellama:13b')

    console.print("\n# Set as default in config.yaml:")
    console.print('default_provider: "ollama"')
    console.print('default_model: "llama3:latest"')

    # Show documentation links
    console.print("\n[italic]For more information, see https://github.com/ollama/ollama/blob/main/docs/api.md[/italic]")
    # console.print("[italic]Or see our documentation: docs/feature_ollama_integration.md[/italic]") # If you have local docs


@config_app.command("validate")
def config_validate(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed validation results even if valid."),
    ] = False,
):
    """
    Validate the current configuration against defined rules.
    """
    console = Console()
    console.print("[bold cyan]Validating configuration...[/bold cyan]")
    config = get_config()

    # Call the validation utility from code_agent.config
    # Pass verbose flag to potentially show warnings/errors via rich print
    # The validate_dynamic method already handles printing based on verbose
    is_valid = config.validate_dynamic(verbose=True)

    if not is_valid:
        console.print("[bold red]Configuration validation failed.[/bold red]")
        raise typer.Exit(code=1)  # Exit with error code if invalid
    elif not verbose:  # Only print simple valid message if not verbose (validate_dynamic handles verbose case)
        console.print("✓ [bold green]Configuration is valid.[/bold green]")


@config_app.command("verbosity")
def config_verbosity(
    level: Annotated[
        Optional[str],
        LEVEL_ARG,  # Use the constant defined earlier
    ] = None,
):
    """
    Get or set the verbosity level in the configuration file.
    """
    config_data = load_config_data(DEFAULT_CONFIG_PATH)  # Pass path
    current_level_int = config_data.get("verbosity", 1)  # Default to 1 (NORMAL) if not set
    try:
        current_level_enum = VerbosityLevel(current_level_int)  # Get enum member from value
    except ValueError:
        current_level_enum = VerbosityLevel.NORMAL  # Fallback if invalid int in config
        current_level_int = current_level_enum.value

    if level is None:
        # Get current level
        rprint(f"Current verbosity level: {current_level_int} ({current_level_enum.name})")
        # Provide help on levels
        rprint("Levels:")
        for name, member in VerbosityLevel.__members__.items():
            rprint(f"  {member.value}: {name}")  # Removed description access
        rprint("\nUse 'code-agent config verbosity [LEVEL]' to set a new level.")
        return

    # Set new level
    new_level_int = -1
    new_level_enum = None

    try:
        # Try parsing as integer first
        new_level_int = int(level)
        if new_level_int not in [v.value for v in VerbosityLevel]:
            raise KeyError  # Raise error if int value is invalid
        new_level_enum = VerbosityLevel(new_level_int)  # Get enum from valid int
    except ValueError:
        # Try parsing as string name
        level_upper = level.upper()
        if level_upper in VerbosityLevel.__members__:
            new_level_enum = VerbosityLevel[level_upper]
            new_level_int = new_level_enum.value
        else:
            rprint(f"[bold red]Error:[/bold red] Invalid verbosity level '{level}'. Must be between 0 and 3.")
            rprint(LEVEL_HELP)
            raise typer.Exit(code=1) from None
    except KeyError:
        # Integer was out of range for the enum
        rprint(f"[bold red]Error:[/bold red] Invalid verbosity level '{level}'. Must be between 0 and 3.")
        rprint(LEVEL_HELP)
        raise typer.Exit(code=1) from None

    # Save the new level to the config file
    config_data["verbosity"] = new_level_int
    save_config_data(config_data, DEFAULT_CONFIG_PATH)  # Pass path

    rprint(f"Verbosity level set to {new_level_int} ({new_level_enum.name}) in config file.")

    # Update the *current session's* verbosity controller
    # This might print additional info based on the new level
    try:
        controller = get_controller()
        controller.level = new_level_enum  # Update controller with the Enum member
        rprint("(Verbosity updated for current session)")
    except Exception as e:
        rprint(f"[yellow]Warning:[/yellow] Could not update verbosity for current session: {e}")


@config_app.command("get-agent-path")
def get_agent_path():
    """
    Show the current default agent path from the configuration file.
    """
    config = get_config()
    console = Console()

    console.print("[bold]Default Agent Path (from config file):[/bold]")
    if config.default_agent_path:
        # Convert string path from config to Path object
        path_obj = Path(config.default_agent_path)
        path_str = str(path_obj)  # Use the Path object for checks
        exists = path_obj.exists()
        status = "[green]✓ (Exists)[/green]" if exists else "[yellow]✗ (Does not exist)[/yellow]"
        console.print(f"[cyan]{path_str}[/cyan] {status}")
        if not exists:
            console.print("[yellow]Warning:[/yellow] The configured default path does not currently exist.")

        # Show example usage
        console.print("\n[bold]Example usage (when using default path):[/bold]")
        console.print('code-agent run "What files are in the repo?"')
    else:
        console.print("[yellow]No default agent path set in the configuration file.[/yellow]")
        console.print("\n[dim]The 'run' command will default to the current directory ('.') if no path is specified.")

    console.print("\n[bold]To set/change the default agent path in the config file:[/bold]")
    console.print('code-agent config set-agent-path "path/to/your/agent" ')
    console.print(f"(This will modify: [dim]{DEFAULT_CONFIG_PATH}[/dim])")


@config_app.command("set-agent-path")
def set_agent_path(
    path: Annotated[
        str,  # Take path as string initially
        typer.Argument(help=PATH_HELP + " (e.g., path/to/agent.py or path/to/agent_dir)"),
    ],
):
    """
    Set the default agent path in the configuration file.
    """
    console = Console()
    path_obj = Path(path)

    # Basic validation on the input path string
    if not path.strip():
        console.print("[bold red]Error:[/bold red] Agent path cannot be empty.")
        raise typer.Exit(code=1)

    # Check if the provided path exists before saving
    if not path_obj.exists():  # Check original path object directly
        console.print(f"[bold red]Error:[/bold red] Path not found: {path_obj}")
        console.print("Please provide a valid path to an agent Python file or directory.")
        raise typer.Exit(code=1)
    else:
        # Path exists, resolve it to store the absolute path
        try:
            resolved_path = path_obj.resolve()
            path_to_save = str(resolved_path)
            console.print(f"[green]Path exists:[/green] {path_to_save}")
        except Exception as e:
            console.print(f"[bold red]Error resolving path {path_obj}: {e}[/bold red]")
            raise typer.Exit(code=1)  # noqa: B904

    # Load existing config data
    config_data = load_config_data(DEFAULT_CONFIG_PATH)  # Pass path

    # Update the config data
    config_data["default_agent_path"] = path_to_save

    # Write the updated config back to file
    save_config_data(config_data, DEFAULT_CONFIG_PATH)  # Pass path

    console.print(f"[bold green]Default agent path set to:[/bold green] [cyan]{path_to_save}[/cyan] in [dim]{DEFAULT_CONFIG_PATH}[/dim]")
    console.print("\n[bold]Effective on next run:[/bold]")
    console.print('code-agent run "Your instruction..." # Will now use this default path')
