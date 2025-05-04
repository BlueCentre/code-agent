import asyncio
import datetime
import logging
import signal
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import typer  # For typer.Exit
import yaml

# Import Runner at top level for easier patching
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types as genai_types
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

# Assuming CodeAgentSettings is defined in code_agent.config.settings_based_config
# Adjust the import path if necessary
from code_agent.config import CodeAgentSettings


# --- Path Resolution ---
def _resolve_agent_path_str(agent_path_cli: Optional[Path], cfg: CodeAgentSettings) -> Optional[str]:
    """Resolves the agent path string from CLI argument or config."""
    resolved_path: Optional[Path] = None
    console = Console()  # Create console for printing messages

    if agent_path_cli:
        # Check existence later, after potential default resolution
        resolved_path = agent_path_cli
        logging.debug(f"Using agent path from CLI: {resolved_path}")
    elif cfg.default_agent_path:
        resolved_path = cfg.default_agent_path
        logging.debug(f"Using default agent path from config: {resolved_path}")
    else:
        # Default to current directory if neither CLI nor config provides a path
        console.print("[yellow]Warning:[/yellow] No agent path provided via CLI or config. Defaulting to current directory '.'")
        resolved_path = Path(".")
        logging.debug("Defaulting agent path to current directory '.'")

    # Perform existence check now
    if resolved_path:
        resolved_path = resolved_path.resolve()  # Make absolute
        if not resolved_path.exists():
            # Use operation_error for consistency
            operation_error(console, f"Resolved agent path does not exist: {resolved_path}")
            # Optionally, print how it was resolved (CLI or config)
            if agent_path_cli:
                operation_error(console, "(Path was provided via command line argument)")
            elif cfg.default_agent_path:
                operation_error(console, "(Path was provided by config's default_agent_path)")
            else:
                operation_error(console, "(Path defaulted to current directory)")
            return None
        else:
            # Validate if it's a directory or a .py file if needed by ADK downstream
            # ADK's _parse_path handles some of this, maybe keep it simple here
            logging.debug(f"Agent path exists: {resolved_path}")
            return str(resolved_path)
    else:
        # This case should ideally not be reached if defaulting works
        operation_error(console, "Could not determine agent path.")
        return None


# --- Yaml Loading/Saving Helpers (for config commands) ---


def load_config_data(config_path: Path) -> dict:
    """Loads YAML data from the config file."""
    config_data = {}
    console = Console()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                content = f.read()
                if not content.strip():  # Handle empty file case
                    logging.warning(f"Config file exists but is empty: {config_path}")
                    return {}
                config_data = yaml.safe_load(content) or {}  # Ensure dict even if null
        except yaml.YAMLError as e:
            console.print(f"[red]Error parsing config file YAML: {e}[/red]")
            # Explicitly chain the exception
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[red]Error reading config file: {e}[/red]")
            # Explicitly chain the exception
            raise typer.Exit(1) from e
    return config_data


def save_config_data(config_path: Path, config_data: dict):
    """Saves YAML data to the config file."""
    console = Console()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)  # Keep order
    except Exception as e:
        console.print(f"[red]Error writing config file: {e}[/red]")
        # Explicitly chain the exception
        raise typer.Exit(1) from e


# --- Logging Configuration ---
def setup_logging(verbosity_level: int):
    """Configures the root logger based on verbosity level."""
    level_map = {
        3: logging.DEBUG,  # Debug
        2: logging.INFO,  # Verbose
        1: logging.WARNING,  # Normal
        0: logging.ERROR,  # Quiet
    }
    # Default to WARNING if level is out of range or unexpected
    log_level = level_map.get(verbosity_level, logging.WARNING)

    logger = logging.getLogger()  # Get the root logger

    # Set the level on the root logger
    logger.setLevel(log_level)

    # Ensure at least one handler exists, and set levels on existing handlers
    if not logger.handlers:
        # If no handlers are configured, add a default StreamHandler
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        handler.setLevel(log_level)  # Set level on the new handler too
        logger.addHandler(handler)
        logging.debug("No handlers found, added default StreamHandler.")
    else:
        # If handlers exist, set their level too
        for handler in logger.handlers:
            handler.setLevel(log_level)

    # Example: Quieten noisy libraries if needed
    # logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.debug(f"Logging configured to level: {logging.getLevelName(log_level)} (Verbosity: {verbosity_level})")


# --- Rich Console Helpers ---
@contextmanager
def thinking_indicator(console: Console, message: str):
    """Display a thinking indicator while processing."""
    try:
        console.print(f"[dim]{message}[/dim]", end="\r")
        yield
    finally:
        # Clear the line, also using single quotes for carriage return
        console.print(" " * len(message), end="\r")


def operation_complete(console: Console, message: str):
    """Display a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def operation_error(console: Console, message: str):
    """Display an error message."""
    console.print(f"[bold red]✗[/bold red] {message}")


def operation_warning(console: Console, message: str):
    """Display a warning message."""
    console.print(f"[bold yellow]![/bold yellow] {message}")


def step_progress(console: Console, message: str):
    """Display a step in progress."""
    console.print(f"[bold cyan]→[/bold cyan] {message}")


# --- Agent Execution Logic ---
def run_cli(
    agent,
    app_name,
    artifact_service=None,
    user_id="cli_user",
    session_id=None,
    interactive=False,
    show_timestamps=False,
    session=None,
    session_service=None,
    memory_service=None,
    initial_instruction=None,
):
    """
    Run an agent in CLI mode with interactive capabilities.

    Args:
        agent: The agent to run
        app_name: Name of the application
        user_id: User identifier for the session
        session_id: Optional session ID to continue an existing conversation
        interactive: Whether to continue conversation in interactive mode after initial query
        show_timestamps: Whether to show timestamps for messages
        session: Session object to use for the run
        session_service: Service for session management (creates InMemorySessionService if None)
        memory_service: Service for memory management (creates InMemorySessionService if None)
        initial_instruction: Initial instruction to give the agent (if None, will prompt for it)
    """
    # Suppress specific loggers that generate noise
    logging.getLogger("google.adk.tools.function_parameter_parse_util").setLevel(logging.ERROR)
    logging.getLogger("google_genai.types").setLevel(logging.ERROR)

    # Import Runner here to avoid circular dependency if utils is imported by runner's module
    # from google.adk.runners import Runner # Removed local import

    # Set up rich console for better output
    console = Console()
    # console.print("[bold cyan]Running agent[/bold cyan]")

    # Create session service if not provided
    if session_service is None:
        session_service = InMemorySessionService()

    # Create a Runner instance
    runner = Runner(session_service=session_service, app_name=app_name, agent=agent, memory_service=memory_service)

    # Set up interrupt handling
    interrupted = False
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def sigint_handler(sig, frame):
        nonlocal interrupted
        interrupted = True
        console.print("\n[bold yellow]Interrupt signal received. Exiting gracefully...")
        # Don't re-raise in interactive mode immediately, let the loop handle it
        if not interactive:
            # Restore handler and re-raise for non-interactive cleanup
            signal.signal(signal.SIGINT, original_sigint_handler)
            # Use raise_signal for proper signal handling behavior
            signal.raise_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, sigint_handler)

    # Process a single message through the agent asynchronously
    async def process_message_async(current_session_id, user_input, show_events=True):
        """Process a single message through the agent asynchronously and display results."""
        nonlocal interrupted, runner, console  # Add console here

        if interrupted:
            return None, False

        try:
            with thinking_indicator(console, "Processing..."):  # Pass console
                # Prepare the input message content
                message_content = genai_types.Content(role="user", parts=[genai_types.Part(text=user_input)])

                # Create or get session
                if not current_session_id:
                    session = session_service.create_session(app_name=app_name, user_id=user_id)
                    current_session_id = session.id
                    step_progress(console, f"[dim]Created new session: {current_session_id}[/dim]")  # Pass console

                # Run the agent asynchronously
                event_async_generator = runner.run_async(
                    user_id=user_id,
                    session_id=current_session_id,
                    new_message=message_content,
                )

                final_response_event = None
                last_content = ""

                # Process events
                try:
                    async for event in event_async_generator:
                        if interrupted:
                            console.print("[bold yellow]Processing interrupted by user.[/bold yellow]")
                            break

                        # Handle event display
                        author = event.author or "System"
                        content_text = ""
                        if hasattr(event, "content") and event.content and event.content.parts:
                            content_text = " ".join(p.text for p in event.content.parts if hasattr(p, "text") and p.text)

                        is_final = hasattr(event, "is_final_response") and event.is_final_response()

                        timestamp_str = ""
                        if show_timestamps and hasattr(event, "timestamp") and event.timestamp:
                            try:
                                timestamp = datetime.datetime.fromtimestamp(event.timestamp)
                                timestamp_str = f"[dim][{timestamp.strftime('%H:%M:%S')}][/dim] "
                            except (TypeError, ValueError, AttributeError):
                                timestamp_str = "[dim][unknown time][/dim] "

                        # Only show non-empty content, and avoid duplicates
                        if show_events and content_text and content_text != last_content:
                            if author == "user":
                                # Keep user output as plain text
                                console.print(f"{timestamp_str}[bold blue]👦🏻User:[/bold blue] {content_text}")
                            elif author == "assistant" or author == agent.name:  # Check agent name too
                                # Print prefix and then render content as Markdown
                                console.print(f"{timestamp_str}[bold yellow]🤖Agent:[/bold yellow]")
                                console.print(Markdown(content_text))
                                # Update last content to avoid duplicates
                                last_content = content_text
                            # Optionally handle other authors like 'tool' or 'system' if needed

                        if is_final:
                            final_response_event = event
                            operation_complete(console, "[dim]Agent finished processing.[/dim]")  # Pass console

                except Exception as e:
                    # Allow KeyboardInterrupt and SystemExit to propagate
                    if isinstance(e, (KeyboardInterrupt, SystemExit)):
                        raise
                    # Handle other runtime errors during event processing
                    operation_error(console, f"Error processing event: {e}")  # Pass console, clarify scope
                    # Log the full traceback for debugging
                    logging.exception("Error during event processing loop")

                # Display final response separately if needed and wasn't already shown
                if not interrupted and final_response_event:
                    final_text = ""
                    if hasattr(final_response_event, "content") and final_response_event.content and final_response_event.content.parts:
                        final_text = " ".join(p.text for p in final_response_event.content.parts if hasattr(p, "text") and p.text)

                    # Print final response if it's different from the last printed content
                    if final_text and final_text != last_content:
                        # Use a slightly different prefix for clarity
                        console.print(f"{timestamp_str}[bold green]Final Agent Response:[/bold green]")
                        # Render final response as Markdown
                        console.print(Markdown(final_text))

                return current_session_id, not interrupted

        except Exception as e:
            # Handle errors during the entire process_message_async call
            if not interrupted:
                operation_error(console, f"An error occurred during agent execution: {e}")  # Pass console
                logging.exception("Error in process_message_async")  # Log traceback
            # Indicate failure
            return current_session_id, False
        finally:
            # Ensure the thinking indicator line is cleared even if there's an error
            # Use single quotes for carriage return
            console.print(" " * len("Processing..."), end="\r")

    # Interactive mode function
    async def run_interactively_async(initial_session_id):
        """Run the agent in interactive mode after initial query."""
        nonlocal interrupted, console  # Add console

        console.print("\n[bold green]Continuing conversation...[/bold green]")
        console.print("Type 'exit', 'quit', or press Ctrl+C to end the session.\n")

        current_session_id = initial_session_id
        while not interrupted:
            try:
                # Use rich.prompt for better handling of Ctrl+C within the prompt
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

                if user_input.lower() in ["exit", "quit"]:
                    console.print("[bold green]Exiting conversation mode.[/bold green]")
                    break

                if not user_input.strip():
                    console.print("[yellow]Please enter a message or 'exit'/'quit'.[/yellow]")
                    continue

                new_session_id, success = await process_message_async(current_session_id, user_input)

                if interrupted:  # Check interrupt flag again after async call
                    console.print("[bold yellow]Interactive session interrupted.[/bold yellow]")
                    break
                if not success:
                    operation_warning(console, "Previous message failed to process. Try again or type 'exit'.")  # Pass console
                    # Optionally decide whether to keep the same session ID or reset
                    # current_session_id = None # Reset session on error?

                # Update session ID only if the processing was successful and returned a new ID
                if success and new_session_id and new_session_id != current_session_id:
                    current_session_id = new_session_id
                    step_progress(console, f"Session updated: {current_session_id}")  # Pass console
                elif success and not new_session_id:
                    # This case shouldn't happen if process_message_async always returns an ID
                    operation_warning(console, "Process message returned success but no session ID.")

            except (KeyboardInterrupt, EOFError):  # Catch EOFError for cases like pipe closure
                console.print("\n[bold yellow]Exiting conversation mode.[/bold yellow]")
                interrupted = True  # Set interrupt flag
                break  # Exit the loop cleanly

        return current_session_id

    # Main execution logic for run_cli
    current_session_id = session_id
    try:
        # Determine the initial instruction
        instruction = initial_instruction

        # If no initial instruction provided, prompt the user
        if instruction is None:
            # Check if running interactively from the start without instruction
            if interactive:
                console.print("[yellow]Starting in interactive mode without an initial instruction.[/yellow]")
                # Directly jump to interactive loop without initial processing
                final_session_id = asyncio.run(run_interactively_async(current_session_id))
                if final_session_id:
                    current_session_id = final_session_id
                # Skip the rest of the initial processing block
                instruction = ""  # Set instruction to empty to avoid processing it later
            else:
                # Not interactive, needs an instruction
                instruction = Prompt.ask("[bold cyan]You (Initial Instruction)[/bold cyan]")
                if not instruction:
                    operation_error(console, "Initial instruction cannot be empty in non-interactive mode.")
                    raise typer.Exit(code=1)

        else:
            console.print(f"[bold cyan]User (Initial Instruction):[/bold cyan] {instruction}")

        # Process the initial instruction only if it's not empty
        if instruction:
            # Run the initial processing using asyncio.run
            session_id_result, success = asyncio.run(process_message_async(current_session_id, instruction))

            # Check for interruption or failure
            if interrupted:
                console.print("[bold yellow]Initial processing interrupted.[/bold yellow]")
            elif not success:
                operation_error(console, "Initial instruction failed to process.")
                # Decide if we should exit or allow interactive mode attempt
                if not interactive:
                    raise typer.Exit(code=1)
                else:
                    operation_warning(console, "Attempting to enter interactive mode despite initial failure.")
                    # We might want to reset session_id_result here
                    session_id_result = current_session_id  # Keep original or reset?

            # Update session ID from the result if successful
            if success and session_id_result:
                current_session_id = session_id_result

            # Continue with interactive mode if requested AND initial step didn't fail/wasn't interrupted
            if interactive and not interrupted and success:
                # Run interactive mode starting with the session ID from the initial step
                final_session_id = asyncio.run(run_interactively_async(current_session_id))
                # Update the main session ID if the interactive part returned one
                if final_session_id:
                    current_session_id = final_session_id
            elif interactive and (interrupted or not success):
                console.print("[yellow]Skipping interactive mode due to interruption or initial failure.[/yellow]")

    except (Exception, typer.Exit) as e:  # Catch typer.Exit as well
        if not interrupted:  # Avoid double logging if interrupted
            operation_error(console, f"An error occurred: {e}")
            logging.exception("Error in run_cli main logic")  # Log traceback
        # Re-raise the exception to stop execution properly
        raise
    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_sigint_handler)

    # Final output
    if interrupted:
        console.print("[bold yellow]Session terminated by user.[/bold yellow]")

    # Always print the session ID at the end for reference
    if current_session_id:
        console.print(f"[dim]Session ID: [bold cyan]{current_session_id}[/bold cyan][/dim]")
    else:
        console.print("[dim]No active session ID to display.[/dim]")

    return current_session_id
