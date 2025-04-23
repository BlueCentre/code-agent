import json
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from cli_agent.providers.ollama import OllamaProvider
from code_agent.tools.progress_indicators import thinking_indicator

app = typer.Typer(help="Interact with Ollama models")
console = Console()


@app.command("list")
def list_models(
    url: str = typer.Option("http://localhost:11434", help="Ollama API URL"), json_format: bool = typer.Option(False, "--json", help="Output in JSON format")
):
    """List available Ollama models."""
    try:
        provider = OllamaProvider(url)
        models = provider.list_models()

        if json_format:
            console.print(json.dumps(models, indent=2))
        else:
            table = Table(title="Ollama Models")
            table.add_column("Name")
            table.add_column("Parameter Size")
            table.add_column("Family")
            table.add_column("Format")
            table.add_column("Quantization")

            for model in models:
                details = model.get("details", {})
                table.add_row(
                    model["name"],
                    details.get("parameter_size", "N/A"),
                    details.get("family", "N/A"),
                    details.get("format", "N/A"),
                    details.get("quantization_level", "N/A"),
                )

            console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")


@app.command("run")
def run_prompt(
    model: str = typer.Argument(..., help="Model name to use"),
    prompt: str = typer.Argument(..., help="Prompt to send to the model"),
    system: Optional[str] = typer.Option(None, help="System prompt"),
    temperature: float = typer.Option(0.7, help="Temperature for generation"),
    url: str = typer.Option("http://localhost:11434", help="Ollama API URL"),
):
    """Run a single prompt and get a response from an Ollama model."""
    try:
        provider = OllamaProvider(url)
        messages = [{"role": "user", "content": prompt}]

        if system:
            messages.insert(0, {"role": "system", "content": system})

        with thinking_indicator(f"Running {model} on your prompt..."):
            response = provider.chat_completion(model, messages, temperature=temperature)

        console.print("[bold green]Response:[/bold green]")
        content = response.get("message", {}).get("content", "No response content")
        console.print(Markdown(content))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")


@app.command("chat")
def chat_with_model(
    model: str = typer.Argument(..., help="Model name to use"),
    prompt: str = typer.Argument(..., help="Prompt to send to the model"),
    system: Optional[str] = typer.Option(None, help="System prompt"),
    temperature: float = typer.Option(0.7, help="Temperature for generation"),
    url: str = typer.Option("http://localhost:11434", help="Ollama API URL"),
):
    """Chat with an Ollama model."""
    try:
        provider = OllamaProvider(url)
        messages = [{"role": "user", "content": prompt}]

        if system:
            messages.insert(0, {"role": "system", "content": system})

        with thinking_indicator(f"Chatting with {model}..."):
            response = provider.chat_completion(model, messages, temperature=temperature)

        console.print("[bold green]Response:[/bold green]")
        console.print(response.get("message", {}).get("content", "No response content"))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e!s}")
