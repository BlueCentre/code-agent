"""
This module contains the commands for the provider sub-app.
"""

import typer
from rich.console import Console

# Local application imports
from code_agent.config import get_api_key, get_config  # Assuming get_api_key is available

# --- Provider Sub-App ---
provider_app = typer.Typer(name="providers", help="List and manage LLM providers.")


@provider_app.command("list")
def providers_list():
    """
    List available/configured providers based on effective config.
    """
    config = get_config()
    console = Console()

    console.print("[bold cyan]Configured LLM Providers:[/bold cyan]")
    console.print("=" * 50)

    # Define provider details (Consider moving this to a shared location or config if it grows)
    providers_info = {
        "ai_studio": {
            "name": "Google AI Studio",
            "style": "blue",
            "config_cmd": "code-agent config aistudio",
            "models": ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest"],
            "env_var": "AI_STUDIO_API_KEY",
        },
        "openai": {
            "name": "OpenAI",
            "style": "green",
            "config_cmd": "code-agent config openai",
            "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "env_var": "OPENAI_API_KEY",
        },
        "groq": {
            "name": "Groq",
            "style": "magenta",
            "config_cmd": "code-agent config groq",
            "models": ["llama3-70b-8192", "mixtral-8x7b-32768"],
            "env_var": "GROQ_API_KEY",
        },
        "anthropic": {
            "name": "Anthropic",
            "style": "cyan",
            "config_cmd": "code-agent config anthropic",
            "models": [
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            "env_var": "ANTHROPIC_API_KEY",
        },
        "ollama": {
            "name": "Ollama (Local)",
            "style": "yellow",
            "config_cmd": "code-agent config ollama",
            "models": ["(local models: llama3, codellama, etc.)"],
            "env_var": None,  # No API key needed
        },
    }

    found_configured_cloud = False

    # Current default indicator
    console.print(f"[bold]Current Default Provider:[/bold] {config.llm.provider}")
    console.print(f"[bold]Current Default Model:[/bold]    {config.llm.model}")
    console.print()

    # List all providers with their status
    console.print("[bold]Available Providers:[/bold]")
    for provider_id, details in providers_info.items():
        api_key = None
        status = ""

        # Check configuration status
        if provider_id == "ollama":
            # Ollama doesn't need an API key, it's considered "configured" if available
            # We could add a check here to see if the ollama service is reachable
            status = "[cyan]✓ Available (Local)[/cyan]"
            # Check if Ollama URL is default or custom
            ollama_url = config.ollama.url if config.ollama else "http://localhost:11434"
            if ollama_url != "http://localhost:11434":
                status += f" (URL: {ollama_url})"

        else:
            # Check API key for cloud providers
            api_key = get_api_key(provider_id)
            if api_key:
                status = "[bold green]✓ Configured (API Key Found)[/bold green]"
                found_configured_cloud = True
            else:
                env_var_name = details.get("env_var")
                env_var_status = f" (Set env var [yellow]{env_var_name}[/yellow])" if env_var_name else ""
                status = f"[yellow]✗ Not configured (No API key found{env_var_status})[/yellow]"

        name = details["name"]
        style = details["style"]

        # Is this the default?
        default_marker = ""
        if provider_id == config.llm.provider:
            default_marker = " [bold green](DEFAULT)[/bold green]"

        console.print(f"[bold {style}]{name}[/bold {style}]: {status}{default_marker}")

        # Show configuration command
        console.print(f"  Setup Info: [dim]{details['config_cmd']}[/dim]")

        # Show example model if it's configured (or for Ollama)
        if api_key or provider_id == "ollama":
            example_model = details["models"][0] if details["models"] else "(No example models)"
            # Adjust command example for run command
            if provider_id == "ollama":
                cmd_example = f'code-agent run "..." --provider {provider_id} --model <your_local_model>'  # e.g., llama3
            else:
                cmd_example = f'code-agent run "..." --provider {provider_id} --model {example_model}'

            console.print(f"  Example Model: [dim]{example_model}[/dim]")
            console.print(f"  Example Usage: [dim]{cmd_example}[/dim]")

        console.print()

    if not found_configured_cloud and config.llm.provider != "ollama":
        console.print("\n[bold yellow]Warning:[/bold yellow] No cloud providers seem to have configured API keys.")
        console.print("You may need to configure one unless you intend to use Ollama exclusively.")
        console.print("Run the relevant command to see setup instructions, e.g.:")
        console.print("  [dim]code-agent config openai[/dim]")
        console.print("  [dim]code-agent config aistudio[/dim]")

    # Usage tips section
    console.print("\n[bold]Quick Tips:[/bold]")
    console.print("- Use [dim]code-agent config show[/dim] to see the full effective configuration.")
    console.print("- Use [dim]code-agent config reset[/dim] to reset configuration to defaults.")
    console.print("- Override provider/model for a single run using [dim]--provider[/dim] and [dim]--model[/dim] flags.")
