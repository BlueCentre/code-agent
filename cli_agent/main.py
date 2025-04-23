import typer

from cli_agent.commands.ollama import app as ollama_app

app = typer.Typer(
    name="cli-agent",
    help="CLI agent for interacting with local AI models.",
    add_completion=True,
    no_args_is_help=True,
)

# Add sub-commands
app.add_typer(ollama_app, name="ollama", help="Interact with Ollama models")

if __name__ == "__main__":
    app()
