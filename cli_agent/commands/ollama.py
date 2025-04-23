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
    url: str = typer.Option("http://localhost:11434", help="Ollama API URL"),
    json_format: bool = typer.Option(False, "--json", help="Output in JSON format"),
    test_mode: bool = typer.Option(False, "--test", help="Run in test mode without making API calls"),
):
    """List available Ollama models.

    In test mode (--test), displays sample data without connecting to Ollama.
    """
    try:
        if test_mode:
            console.print("[bold yellow]Running in test mode[/bold yellow]")
            console.print(f"[bold]URL:[/bold] {url}")

            # Sample test data
            test_models = [
                {"name": "llama2:latest", "details": {"parameter_size": "7B", "family": "Llama", "format": "GGUF", "quantization_level": "Q4_0"}},
                {"name": "mistral:latest", "details": {"parameter_size": "7B", "family": "Mistral", "format": "GGUF", "quantization_level": "Q4_0"}},
            ]

            if json_format:
                console.print(json.dumps({"models": test_models}, indent=2))
            else:
                table = Table(title="Ollama Models (Test Mode)")
                table.add_column("Name")
                table.add_column("Parameter Size")
                table.add_column("Family")
                table.add_column("Format")
                table.add_column("Quantization")

                for model in test_models:
                    details = model.get("details", {})
                    table.add_row(
                        model["name"],
                        details.get("parameter_size", "N/A"),
                        details.get("family", "N/A"),
                        details.get("format", "N/A"),
                        details.get("quantization_level", "N/A"),
                    )

                console.print(table)
            return

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
    test_mode: bool = typer.Option(False, "--test", help="Run in test mode without making API calls"),
):
    """Run a single prompt and get a response from an Ollama model.

    In test mode (--test), displays input parameters and returns a sample response
    without making actual API calls to Ollama.
    """
    try:
        if test_mode:
            console.print("[bold yellow]Running in test mode[/bold yellow]")
            console.print(f"[bold]Model:[/bold] {model}")
            console.print(f"[bold]Prompt:[/bold] {prompt}")
            if system:
                console.print(f"[bold]System:[/bold] {system}")
            console.print(f"[bold]Temperature:[/bold] {temperature}")
            console.print(f"[bold]URL:[/bold] {url}")

            test_response = {"message": {"content": "This is a test response. No actual API call was made to Ollama.", "role": "assistant"}, "model": model}
            console.print("[bold green]Response:[/bold green]")
            content = test_response.get("message", {}).get("content", "No response content")
            console.print(Markdown(content))
            return

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
    test_mode: bool = typer.Option(False, "--test", help="Run in test mode without making API calls"),
):
    """Chat with an Ollama model.

    In test mode (--test), displays input parameters and returns a sample response
    without making actual API calls to Ollama.
    """
    try:
        if test_mode:
            console.print("[bold yellow]Running in test mode[/bold yellow]")
            console.print(f"[bold]Model:[/bold] {model}")
            console.print(f"[bold]Prompt:[/bold] {prompt}")
            if system:
                console.print(f"[bold]System:[/bold] {system}")
            console.print(f"[bold]Temperature:[/bold] {temperature}")
            console.print(f"[bold]URL:[/bold] {url}")

            test_response = {"message": {"content": "This is a test response. No actual API call was made to Ollama.", "role": "assistant"}, "model": model}
            console.print("[bold green]Response:[/bold green]")
            console.print(test_response.get("message", {}).get("content", "No response content"))
            return

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
