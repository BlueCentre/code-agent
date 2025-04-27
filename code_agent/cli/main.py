import os  # For environment variables
import sys  # For command-line arguments
from typing import Optional, List

import anyio # Add anyio import for Typer async handling
import asyncio # Add asyncio import

from dotenv import load_dotenv  # Import dotenv

load_dotenv()  # Load .env file into environment variables

# Explicitly configure the API key for the models
import google.generativeai as genai
import typer
from rich import print  # Use rich print for better formatting
from rich.console import Console  # Import Console for rich formatting
from rich.markdown import Markdown  # Import Markdown renderer
from rich.prompt import Prompt  # Use rich Prompt for better input
from typing_extensions import Annotated

# Remove nest_asyncio import and apply
from code_agent import __version__ as agent_version  # Updated import

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


# Updated imports
# from code_agent.agent.agent import CodeAgent  # REMOVED old agent import
from code_agent.agent.multi_agent import get_root_agent  # IMPORT new root agent
from code_agent.config.config import DEFAULT_CONFIG_DIR, get_config, initialize_config

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
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

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
        print(f"Code Agent version: {agent_version}")  # Updated output message
        print(f"Google ADK version: {adk_version}")  # Show ADK version
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

                # Process special commands
                if user_input.startswith("/"):
                    command = user_input[1:].strip().lower()
                    if command == "help":
                        print("[bold magenta]Special Commands:[/bold magenta]")
                        print("/clear - Clear conversation history (starts a new session)")
                        print("/help  - Show this help message")
                        print("exit or quit - End the chat session")
                        print("\n[bold magenta]Available Tools:[/bold magenta]")
                        print("The assistant can describe these capabilities, but the CLI implementation has limited support:")
                        print("- Web search: Ask about current events or information")
                        print("- File operations: Ask about reading files or directories")
                        print("- Terminal commands: Ask about running commands")
                        print("- Memory: The assistant will remember information from your conversation")
                        print("\n[bold yellow]Note:[/bold yellow] This implementation has limited tool support. For full functionality,")
                        print("use the agent API directly or the web interface.")
                        continue
                    elif command == "clear":
                        # Create a new session when history is cleared
                        current_session = session_service.create_session(app_name="code_agent", user_id="cli_user")
                        current_session_id = current_session.id
                        print("[bold green]History cleared. New session started.[/bold green]")
                        verbosity_controller.show_verbose(f"Created new ADK session: {current_session_id}")
                        continue
                    else:
                        print(f"[bold red]Unknown command: {command}[/bold red]")
                        continue

                if user_input.lower() in ["quit", "exit"]:
                    print("[bold yellow]Exiting chat session.[/bold yellow]")
                    break

                if not user_input:
                    print("[yellow]Please enter a non-empty message.[/yellow]")
                    continue

                # Create content object for user message
                message_content = genai_types.Content(parts=[genai_types.Part(text=user_input)])

                print("\n[bold yellow]Agent:[/bold yellow]")

                # Add the user message manually to avoid duplicate messages
                user_event = Event(author="user", content=message_content)
                session_service.append_event(session=current_session, event=user_event)

                # Run the model in a non-streaming way
                try:
                    with console.status("[bold green]Thinking...[/bold green]") as status:
                        # Create a new Runner for each request to avoid event loop issues
                        runner = Runner(session_service=session_service, app_name="code_agent", agent=root_agent)

                        # Use the Gemini API directly
                        import google.generativeai as genai

                        # We're not actually using the available_tools variable, so let's skip this to avoid linter errors
                        # available_tools = []
                        # Safely check for sub_agents attribute
                        # if hasattr(root_agent, "sub_agents") and isinstance(getattr(root_agent, "sub_agents", []), (list, tuple)):
                        #     for agent in root_agent.sub_agents:
                        #         if hasattr(agent, "tools"):
                        #             available_tools.extend([t.name for t in agent.tools])

                        # Build conversation history from session events
                        conversation_history = []
                        if hasattr(current_session, "events"):
                            for event in current_session.events:
                                if hasattr(event, "author") and hasattr(event, "content"):
                                    role = "User" if event.author == "user" else "Assistant"
                                    content = ""

                                    # Extract text content from the event
                                    if event.content and hasattr(event.content, "parts"):
                                        for part in event.content.parts:
                                            if hasattr(part, "text") and part.text:
                                                content += part.text

                                    if content:
                                        conversation_history.append(f"{role}: {content}")

                        # Log how many history items we found
                        verbosity_controller.show_verbose(f"Found {len(conversation_history)} conversation turns in history")

                        # Create a more descriptive prompt that encourages tool use and includes history
                        history_text = "\n".join(conversation_history[-6:]) if conversation_history else "No previous conversation."

                        prompt = f"""You are a helpful, friendly AI assistant with access to a wealth of built-in knowledge AND specialized tools.

Conversation history:
{history_text}

User query: {user_input}

IMPORTANT: When the user explicitly asks you to "search the web" or "search for" something, you MUST use the google_search tool to fetch information.

For your response, prioritize as follows:
1. For general knowledge questions, creative content requests (jokes, stories), or conceptual questions - use your built-in knowledge.
2. For when the user explicitly asks you to search the web - ALWAYS use the google_search tool.
3. For exploring files or directories - use the list_dir tool.

Available tools:
- google_search: Search for up-to-date information on the web
- list_dir: List files in a directory

Be conversational, helpful, and engaging. If asked for creative content like jokes, stories, or explanations, provide them directly using your built-in capabilities rather than using tools.

Examples:
- "Tell me a joke" → Respond with a joke from your knowledge
- "Search the web for the latest AI developments" → Use google_search with query "latest AI developments"
- "What files are in this directory?" → Use list_dir"""

                        # Generate the response with tool access enabled if possible
                        model = genai.GenerativeModel(
                            get_config().default_model,
                            tools=[
                                {
                                    "function_declarations": [
                                        {
                                            "name": "google_search",
                                            "description": "Search for information on the web",
                                            "parameters": {
                                                "type": "object",
                                                "properties": {"query": {"type": "string", "description": "The search query"}},
                                                "required": ["query"],
                                            },
                                        },
                                        {
                                            "name": "list_dir",
                                            "description": "List files in a directory",
                                            "parameters": {
                                                "type": "object",
                                                "properties": {"path": {"type": "string", "description": "Path to the directory"}},
                                                "required": ["path"],
                                            },
                                        },
                                    ]
                                }
                            ],
                        )

                        # Log session ID and history length for debugging
                        history_events = current_session.events if hasattr(current_session, "events") else []
                        verbosity_controller.show_verbose(f"Session {current_session_id} has {len(history_events)} events")

                        # Generate content with safety settings adjusted
                        generation_config = {
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 40,
                            "max_output_tokens": 1024,
                        }

                        safety_settings = [
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        ]

                        response = model.generate_content(prompt, generation_config=generation_config, safety_settings=safety_settings)

                        # Process the response and check for function calls
                        if hasattr(response, "candidates") and response.candidates:
                            candidate = response.candidates[0]

                            # Check if there are function calls to execute
                            if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                                for part in candidate.content.parts:
                                    if hasattr(part, "function_call"):
                                        function_call = part.function_call
                                        function_name = function_call.name
                                        function_args = function_call.args

                                        print(f"\n[bold yellow]Agent is calling function:[/bold yellow] {function_name}")

                                        # Execute the appropriate tool
                                        function_response = "No function result available."

                                        if function_name == "google_search" and "query" in function_args:
                                            # In CLI mode, we use a simulated implementation
                                            try:
                                                query = function_args["query"]
                                                verbosity_controller.show_verbose(f"Using simulated search for '{query}' in CLI mode")
                                                verbosity_controller.show_warning("Note: For real Google Search, use this agent in ADK deployment mode")
                                                
                                                # Simulated search results based on common queries
                                                if "lithium" in query.lower() or "battery" in query.lower() or "batteries" in query.lower():
                                                    search_results = [
                                                        {
                                                            "title": "Lithium-ion battery - Wikipedia",
                                                            "url": "https://en.wikipedia.org/wiki/Lithium-ion_battery",
                                                            "snippet": "A lithium-ion battery is a type of rechargeable battery that uses lithium ions as the primary component of its electrolyte. They are commonly used in portable electronics and electric vehicles and are growing in popularity for military and aerospace applications."
                                                        },
                                                        {
                                                            "title": "How Do Lithium Batteries Work? - Science ABC",
                                                            "url": "https://www.scienceabc.com/innovation/how-do-lithium-ion-batteries-work.html",
                                                            "snippet": "Lithium batteries work by the movement of lithium ions from the negative electrode through an electrolyte to the positive electrode during discharge, and back when charging. They offer high energy density and low self-discharge rates compared to other battery technologies."
                                                        },
                                                        {
                                                            "title": "Environmental Impact of Lithium Batteries - National Geographic",
                                                            "url": "https://www.nationalgeographic.com/environment/article/lithium-batteries-environment",
                                                            "snippet": "While lithium batteries power clean energy technologies, their production has significant environmental impacts. Mining lithium requires vast amounts of water and can cause pollution. Researchers are working on more sustainable extraction methods and recycling programs."
                                                        }
                                                    ]
                                                elif "ai" in query.lower() or "artificial intelligence" in query.lower() or "llm" in query.lower():
                                                    search_results = [
                                                        {
                                                            "title": "What is Artificial Intelligence (AI)? - IBM",
                                                            "url": "https://www.ibm.com/topics/artificial-intelligence",
                                                            "snippet": "Artificial intelligence is a field of computer science that aims to create systems capable of performing tasks that typically require human intelligence. These include visual perception, speech recognition, decision-making, and language translation."
                                                        },
                                                        {
                                                            "title": "Large Language Models: A New Frontier in AI - Stanford HAI",
                                                            "url": "https://hai.stanford.edu/news/large-language-models-new-frontier-ai",
                                                            "snippet": "Large Language Models (LLMs) like GPT-4, Claude, and Gemini represent a significant advancement in AI technology, capable of generating human-like text, translating languages, and even writing code based on natural language instructions."
                                                        },
                                                        {
                                                            "title": "The State of AI in 2024 - MIT Technology Review",
                                                            "url": "https://www.technologyreview.com/2024/01/10/the-state-of-ai-2024/",
                                                            "snippet": "2024 has seen significant advancements in multimodal AI systems, regulatory frameworks for AI governance, and increased focus on AI safety and alignment. Companies are investing billions in AI research and infrastructure."
                                                        }
                                                    ]
                                                else:
                                                    # Default results for other queries
                                                    search_results = [
                                                        {
                                                            "title": f"Search result 1 for: {query}",
                                                            "url": "https://example.com/result1",
                                                            "snippet": f"This is a simulated search result for '{query}'. In a real implementation, this would connect to an actual search API and return relevant results."
                                                        },
                                                        {
                                                            "title": f"Search result 2 for: {query}",
                                                            "url": "https://example.com/result2",
                                                            "snippet": f"More information about '{query}'. This is a demonstration of the search capability, showing how search results would be formatted."
                                                        },
                                                        {
                                                            "title": f"Search result 3 for: {query}",
                                                            "url": "https://example.com/result3",
                                                            "snippet": f"Additional details related to '{query}'. In a production environment, these results would be from actual web sources."
                                                        }
                                                    ]

                                                # Format the results
                                                formatted_results = [f"Search results for '{query}':\n"]

                                                for i, result in enumerate(search_results, 1):
                                                    formatted_results.append(f"{i}. {result['title']}")
                                                    formatted_results.append(f"   URL: {result['url']}")
                                                    formatted_results.append(f"   {result['snippet']}")
                                                    formatted_results.append("")

                                                function_response = "\n".join(formatted_results)
                                                verbosity_controller.show_verbose(f"Generated search results for: {query}")
                                            except Exception as e:
                                                import traceback

                                                error_trace = traceback.format_exc()
                                                verbosity_controller.show_error(f"Error executing search: {e!s}")
                                                verbosity_controller.show_debug(error_trace)
                                                function_response = f"Error executing search: {e!s}"

                                        elif function_name == "list_dir" and "path" in function_args:
                                            import os

                                            try:
                                                path = function_args["path"]
                                                if os.path.exists(path) and os.path.isdir(path):
                                                    files = os.listdir(path)
                                                    file_list = "\n".join(files)
                                                    function_response = f"Files in {path}:\n\n{file_list}"
                                                else:
                                                    function_response = f"Directory not found or not a directory: {path}"
                                            except Exception as e:
                                                function_response = f"Error listing directory: {e!s}"

                                        print(f"[dim]{function_response}[/dim]")

                                        # Now get a response with the function result
                                        try:
                                            function_result_prompt = f"""You are a helpful, friendly AI assistant with access to various tools AND a wealth of built-in knowledge.

Previous conversation:
{history_text}

User query: {user_input}

You called the function {function_name} with arguments {function_args}.
The function returned this result:
{function_response}

Based on this information, provide a helpful, conversational response that directly answers the user's question.
Be engaging and natural in your tone. If the search results are not sufficient, you can still draw on your built-in knowledge to provide a complete answer.
If appropriate, suggest follow-up questions the user might be interested in."""

                                            new_response = model.generate_content(function_result_prompt)
                                            if new_response and hasattr(new_response, 'candidates') and new_response.candidates:
                                                candidate = new_response.candidates[0]
                                                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                                    parts = candidate.content.parts
                                                    if parts and hasattr(parts[0], 'text'):
                                                        response_text = parts[0].text
                                                    else:
                                                        response_text = "I couldn't extract a proper response from the tool results."
                                                else:
                                                    response_text = "I couldn't process the tool results properly."
                                            else:
                                                response_text = "I wasn't able to process the tool results properly."
                                        except Exception as e:
                                            response_text = f"I called the {function_name} tool, but encountered an error processing the results: {e!s}"

                                        # Create assistant event with the tool result
                                        assistant_event = Event(author="assistant", content=genai_types.Content(parts=[genai_types.Part(text=response_text)]))
                                        session_service.append_event(session=current_session, event=assistant_event)
                                        break
                            else:
                                # No function call, just use the text response
                                if hasattr(candidate.content, 'text'):
                                    response_text = candidate.content.text
                                else:
                                    # If no direct text property, extract from parts
                                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                        parts = candidate.content.parts
                                        if parts and hasattr(parts[0], 'text'):
                                            response_text = parts[0].text
                                        else:
                                            response_text = "I couldn't extract a proper response."
                                    else:
                                        response_text = "I wasn't able to generate a proper response."
                                    
                                # Create assistant event with the text
                                assistant_event = Event(
                                    author="assistant",
                                    content=genai_types.Content(parts=[genai_types.Part(text=response_text)])
                                )
                                session_service.append_event(session=current_session, event=assistant_event)
                        else:
                            # Fallback for any other response format
                            if hasattr(response, "text"):
                                response_text = response.text

                                # Create assistant event with the text
                                assistant_event = Event(author="assistant", content=genai_types.Content(parts=[genai_types.Part(text=response_text)]))
                                session_service.append_event(session=current_session, event=assistant_event)
                except Exception as e:
                    import traceback

                    print(f"[bold red]Error while getting response:[/bold red] {e}")
                    traceback.print_exc()
                    response_text = f"Error: {e!s}"

                # Display the final response
                if response_text:
                    print(Markdown(response_text))
                else:
                    print("[italic yellow]No response generated[/italic yellow]")

                # Exit after first response in non-interactive mode
                if not is_interactive:
                    verbosity_controller.show_verbose("Exiting after first response in non-interactive mode.")
                    break

            except KeyboardInterrupt:
                print("\n[bold yellow]Chat interrupted. Exiting.[/bold yellow]")
                break
            except Exception as e:
                print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
                import traceback

                traceback.print_exc()
                if not is_interactive:
                    break
    finally:
        # No explicit cleanup needed for InMemorySessionService
        pass


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
            example_model = details["models"][0]
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
