"""
Command for creating a new agent project.
Creates an ADK-compatible agent project structure using templates.
"""

import os
import subprocess
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from code_agent.templates import get_template_manager

# Messages
_GOOGLE_API_MSG = """
Don't have API Key? Create one in AI Studio: https://aistudio.google.com/apikey
"""

_GOOGLE_CLOUD_SETUP_MSG = """
You need an existing Google Cloud account and project, check out this link for details:
https://google.github.io/adk-docs/get-started/quickstart/#gemini---google-cloud-vertex-ai
"""

_OLLAMA_SETUP_MSG = """
You need Ollama installed and running locally, check out this link for details:
https://ollama.ai/download

Ensure you have the model you want to use already pulled:
    ollama pull llama3
    ollama pull codellama:13b
"""

# Console for rich output
console = Console()


def _get_gcp_project_from_gcloud() -> str:
    """Uses gcloud to get default project."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _get_gcp_region_from_gcloud() -> str:
    """Uses gcloud to get default region."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "compute/region"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _prompt_str(
    prompt_prefix: str,
    *,
    prior_msg: Optional[str] = None,
    default_value: Optional[str] = None,
) -> str:
    """Interactive string prompt with optional prior message and default value."""
    if prior_msg:
        console.print(prior_msg, style="green")

    while True:
        # Use typer's prompt
        value = typer.prompt(prompt_prefix, default=default_value or "", show_default=True if default_value else False)
        if value and value.strip():
            return value.strip()


def _prompt_for_google_cloud(google_cloud_project: Optional[str]) -> str:
    """Prompts user for Google Cloud project ID."""
    google_cloud_project = google_cloud_project or os.environ.get("GOOGLE_CLOUD_PROJECT", None) or _get_gcp_project_from_gcloud()

    google_cloud_project = _prompt_str("Enter Google Cloud project ID", default_value=google_cloud_project)

    return google_cloud_project


def _prompt_for_google_cloud_region(google_cloud_region: Optional[str]) -> str:
    """Prompts user for Google Cloud region."""
    google_cloud_region = google_cloud_region or os.environ.get("GOOGLE_CLOUD_LOCATION", None) or _get_gcp_region_from_gcloud()

    google_cloud_region = _prompt_str(
        "Enter Google Cloud region",
        default_value=google_cloud_region or "us-central1",
    )
    return google_cloud_region


def _prompt_for_google_api_key(google_api_key: Optional[str]) -> str:
    """Prompts user for Google API key."""
    google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY", None)

    google_api_key = _prompt_str(
        "Enter Google API key",
        prior_msg=_GOOGLE_API_MSG,
        default_value=google_api_key,
    )
    return google_api_key


def _prompt_for_ollama_url(ollama_url: Optional[str] = None) -> str:
    """Prompts user for Ollama URL."""
    default_url = ollama_url or "http://localhost:11434"

    return _prompt_str("Enter Ollama API URL", default_value=default_url)


def _prompt_for_ollama_model(ollama_model: Optional[str] = None) -> str:
    """Prompts user for Ollama model."""
    default_model = ollama_model or "llama3"

    return _prompt_str("Enter Ollama model name (must be already pulled)", default_value=default_model)


def _prompt_for_api_key(provider: str, key_env_var: str, api_key: Optional[str] = None) -> str:
    """Prompts user for an API key for a provider."""
    api_key = api_key or os.environ.get(key_env_var, None)

    return _prompt_str(f"Enter {provider} API key", default_value=api_key)


def _prompt_for_model(default_model: str) -> str:
    """Prompts the user for a model name or accepts the default."""
    return _prompt_str("Enter model name", default_value=default_model)


def _display_template_list(templates: List[Dict[str, Any]]) -> None:
    """Display a table of available templates."""
    table = Table(title="Available Agent Templates")

    table.add_column("#", justify="right", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="blue")
    table.add_column("Default Model", style="magenta")

    for idx, template in enumerate(templates, 1):
        table.add_row(str(idx), template["name"], template["description"], template["default_model"] or "(None)")

    console.print(table)


def _prompt_to_choose_template() -> str:
    """Prompts the user to choose a template from available ones."""
    # Get available templates
    manager = get_template_manager()
    templates = manager.get_available_templates()

    if not templates:
        console.print("[red]No templates found. Please check the template directory.[/red]")
        raise typer.Exit(1)

    # Display templates
    _display_template_list(templates)

    # Prompt for choice
    valid_choices = list(range(1, len(templates) + 1))
    choice = typer.prompt(
        "Select a template by number",
        type=int,
        default=1,
        show_default=True,
    )

    if choice not in valid_choices:
        console.print(f"[red]Invalid choice: {choice}. Please choose a number between 1 and {len(templates)}.[/red]")
        raise typer.Exit(1)

    # Return the template ID
    return templates[choice - 1]["id"]


def _collect_template_params(template_id: str, **kwargs) -> Dict[str, Any]:
    """Collect parameters needed for the chosen template."""
    # Get the template
    manager = get_template_manager()
    template = manager.get_template(template_id)

    if not template:
        console.print(f"[red]Template '{template_id}' not found.[/red]")
        raise typer.Exit(1)

    # Start with model parameter, always needed
    params = {"model_name": kwargs.get("model") or _prompt_for_model(template.get("default_model", "MODEL_PLACEHOLDER"))}

    # Process additional requirements
    if "requires" in template:
        for req in template["requires"]:
            for key, env_var in req.items():
                # Skip if parameter already provided
                if kwargs.get(key):
                    params[key] = kwargs[key]
                    continue

                # Handle known parameter types
                if key == "api_key":
                    provider_name = template["name"]
                    api_key = _prompt_for_api_key(provider_name, env_var, kwargs.get(key))
                    params[key] = api_key

                    # Add provider-specific keys to params for template formatting
                    if template_id == "gemini_api":
                        params["google_api_key"] = api_key
                elif key == "project":
                    params["google_cloud_project"] = _prompt_for_google_cloud(kwargs.get("project"))
                elif key == "region":
                    params["google_cloud_region"] = _prompt_for_google_cloud_region(kwargs.get("region"))
                elif key == "ollama_url":
                    params[key] = _prompt_for_ollama_url(kwargs.get("ollama_url"))
                elif key == "ollama_model":
                    params[key] = _prompt_for_ollama_model(kwargs.get("ollama_model"))
                else:
                    # Generic parameter
                    params[key] = _prompt_str(f"Enter {key}", default_value=kwargs.get(key))

    return params


def run_cmd(app_name: str, **kwargs):
    """Creates a new agent project using templates."""
    # Choose template
    template_id = kwargs.pop("template_id", None) or _prompt_to_choose_template()

    # Collect parameters for the template
    params = _collect_template_params(template_id, **kwargs)

    # Generate the agent
    manager = get_template_manager()
    success, message = manager.generate_agent(template_id, app_name, params)

    if success:
        console.print(message, style="green")
    else:
        console.print(f"[red]Error creating agent: {message}[/red]")
        raise typer.Exit(1)


def create_command(
    app_name: Annotated[Optional[str], typer.Argument(help="The folder of the agent source code.")] = None,
    template: Annotated[
        Optional[str],
        typer.Option(help="The template ID to use (e.g., gemini_api, vertex_ai, ollama)."),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(help="The model used for the root agent."),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option(help="The API Key needed to access the model."),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(help="The Google Cloud Project for using VertexAI as backend."),
    ] = None,
    region: Annotated[
        Optional[str],
        typer.Option(help="The Google Cloud Region for using VertexAI as backend."),
    ] = None,
    ollama_url: Annotated[
        Optional[str],
        typer.Option(help="The URL for your Ollama API server."),
    ] = None,
    ollama_model: Annotated[
        Optional[str],
        typer.Option(help="The Ollama model to use (must be already pulled)."),
    ] = None,
    list_templates: Annotated[
        bool,
        typer.Option("--list", help="List available templates and exit."),
    ] = False,
):
    """
    Creates a new app in the current folder with prepopulated agent template.

    Examples:

        # Interactive create with template selection
        code-agent create path/to/my_app

        # Create with specific template
        code-agent create path/to/my_app --template vertex_ai

        # List available templates
        code-agent create --list
    """
    if list_templates:
        manager = get_template_manager()
        templates = manager.get_available_templates()
        _display_template_list(templates)
        return

    if app_name is None:
        console.print("[red]Error: Missing argument 'APP_NAME'.[/red]")
        console.print("Use 'code-agent create --help' for help.")
        raise typer.Exit(1)

    run_cmd(
        app_name,
        template_id=template,
        model=model,
        api_key=api_key,
        project=project,
        region=region,
        ollama_url=ollama_url,
        ollama_model=ollama_model,
    )
