import asyncio
import json  # Added for tool call argument parsing
from typing import Any, Dict, List, Optional

# Import Google GenAI libraries for AI Studio direct integration
import google.generativeai as genai

# ruff: noqa: E501
import litellm

# Updated ADK imports for v0.3.0
from google.adk.events.event import Event

# SessionId, EventType removed
from google.genai import types as genai_types  # Added
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from rich import print

# Service/Manager imports remain
from code_agent.adk import CodeAgentADKSessionManager, get_adk_session_service, get_memory_service

# Import memory tools
# from code_agent.tools.memory_tools import load_memory # Old import
from code_agent.adk.tools import load_memory  # New import

# Import tools as regular functions
from code_agent.config import CodeAgentSettings, get_config  # Changed

# Import agent configuration tools
from code_agent.tools.agent_config_tools import set_verbosity
from code_agent.tools.error_utils import format_api_error, format_tool_error

# Import run_native_command from native_tools
from code_agent.tools.native_tools import run_native_command
from code_agent.tools.progress_indicators import thinking_indicator

# Import simple tools except run_native_command
from code_agent.tools.simple_tools import apply_edit, read_file

# Import verbosity controller
from code_agent.verbosity import VerbosityLevel, get_controller

# Maximum number of tool calls allowed in a single turn
MAX_TOOL_CALLS = 10


class CodeAgent:
    """Core class for the Code Agent, handling interaction loops and tool use using ADK sessions."""

    def __init__(self):
        self.config: CodeAgentSettings = get_config()  # Changed from initialize_config().agent_settings
        self.session_id: Optional[str] = None  # SessionId -> str
        self.session_manager: Optional[CodeAgentADKSessionManager] = None
        self.auth_token: Optional[str] = None  # Add auth token for session access
        self.verbosity: int = 1  # Default verbosity level
        self._initialized: bool = False  # Flag to track async initialization

        # Initialize verbosity controller with config setting
        verbosity_controller = get_controller()
        verbosity_level = VerbosityLevel.NORMAL  # Default

        # Map config verbosity value to enum
        try:
            for level in VerbosityLevel:
                if level.value == self.config.verbosity:
                    verbosity_level = level
                    break
        except (AttributeError, ValueError):
            # In case of any error, use default
            pass

        # Set the verbosity level
        verbosity_controller.set_level(verbosity_level)

        # Show startup message based on verbosity
        verbosity_controller.show_verbose(f"Agent verbosity set to {verbosity_level.name}")

        # Prepare base instruction parts (can be refined later)
        self.base_instruction_parts = ["You are an autonomous AI software engineer assistant."]
        self.base_instruction_parts.append("Your primary goal is to complete user requests by proactively using your available tools.")
        self.base_instruction_parts.append("Think step-by-step to break down complex requests into smaller, manageable tasks.")
        self.base_instruction_parts.append("Before attempting code modifications or answering questions about the codebase, **always** gather context first:")
        self.base_instruction_parts.append("  - Use `read_file` to examine relevant files carefully.")
        self.base_instruction_parts.append(
            "  - Use `run_native_command` (like `pwd`, `ls -la`, `find . -name '...' | cat`, `git status | cat`) to understand the project structure and state."
        )
        self.base_instruction_parts.append("  - Use `load_memory` to check if you have discussed relevant information in previous conversations.")
        self.base_instruction_parts.append("When planning to use `apply_edit`, ensure you have read the relevant file or section first using `read_file`.")
        self.base_instruction_parts.append(
            "If a tool execution fails or doesn't provide the needed information, try alternative commands or approaches before giving up."
        )
        self.base_instruction_parts.append(
            "**Only ask the user for clarification if you are completely stuck after exhausting all possibilities with your tools.**"
        )

        if self.config.rules:
            self.base_instruction_parts.append("Follow these additional user-defined instructions:")
            self.base_instruction_parts.extend([f"- {rule}" for rule in self.config.rules])

        self.base_instruction_parts.append("You have access to the following functions:")
        self.base_instruction_parts.append("- read_file(path): Reads the content of a specified file path.")
        self.base_instruction_parts.append(
            "- apply_edit(target_file, code_edit): Creates a new file or edits an existing file by providing the "
            "complete content. It can create and modify files including documentation, code, or any text files. "
            "It will show a diff and ask for user confirmation before applying unless auto_approve_edits is enabled."
        )
        self.base_instruction_parts.append(
            "- run_native_command(command): Executes a native terminal command after asking for "
            "user confirmation (unless auto-approved or on allowlist). Use cautiously."
        )
        self.base_instruction_parts.append(
            "- google_search(query): Searches the web for information using Google Search. Use when local files or commands don't provide the answer."
        )
        self.base_instruction_parts.append(
            "- load_memory(query): Searches the agent's long-term memory for information from previous conversations. "
            "Use when you need to recall past discussions or information shared by the user."
        )

        # Add specific guidance for file listing
        self.base_instruction_parts.append("When asked to list files, especially Python files in directories:")
        self.base_instruction_parts.append(
            "- For listing Python files recursively in a directory, use: run_native_command(command=\"find directory_path -type f -name '*.py' | sort\")"
        )
        self.base_instruction_parts.append("- Never use simple 'ls' commands with wildcards like 'ls *.py' as they don't search recursively.")

        self.base_instruction_parts.append("When asked to create or update documentation:")
        self.base_instruction_parts.append("- Use apply_edit to create or modify documentation files directly in the appropriate directory.")
        self.base_instruction_parts.append(
            "- For user requests about documenting features or improvements, create a relevant markdown file in the 'docs/' directory."
        )

        self.base_instruction_parts.append("Use these functions when necessary to fulfill the user's request.")

    # Rename to async_init and make public
    async def async_init(self):
        """Initializes the ADK session service and creates a new session if needed."""
        if not self._initialized:
            session_service = await get_adk_session_service()
            self.session_manager = CodeAgentADKSessionManager(session_service)
            # Use create_session from the manager now
            session_id, auth_token = self.session_manager.create_session()  # create_session is sync now in manager
            self.session_id = session_id
            self.auth_token = auth_token  # Store the auth token for future use
            self._initialized = True

    async def _ensure_initialized(self):
        """Ensures the agent's async components are initialized."""
        if not self._initialized:
            # Call the public async init method
            await self.async_init()
        if self.session_manager is None or self.session_id is None:
            # This should ideally not happen if _initialize_session worked
            raise RuntimeError("Session manager or session ID not initialized.")

    async def add_user_message(self, message: str) -> None:
        """Add a user message to the history."""
        await self._ensure_initialized()
        # Generate an ID if called outside run_turn, though typically not expected
        invocation_id = Event.new_id()
        await self.session_manager.add_user_message(session_id=self.session_id, content=message, invocation_id=invocation_id)

    async def add_system_message(self, message: str) -> None:
        """Add a system message to the history."""
        await self._ensure_initialized()
        invocation_id = Event.new_id()
        await self.session_manager.add_system_message(session_id=self.session_id, content=message, invocation_id=invocation_id)

    async def add_assistant_message(self, message: str, tool_calls: Optional[List[genai_types.FunctionCall]] = None) -> None:
        """Add an assistant message to the history."""
        await self._ensure_initialized()
        invocation_id = Event.new_id()
        await self.session_manager.add_assistant_message(session_id=self.session_id, content=message, tool_calls=tool_calls, invocation_id=invocation_id)

    async def clear_messages(self) -> None:
        """Clear all messages from the history."""
        await self._ensure_initialized()  # Ensures manager exists, but might not re-init
        # Explicitly reset initialization flag to force re-creation of session
        self._initialized = False
        # Re-initialize to get a fresh session, effectively clearing InMemory history
        await self.async_init()  # Call the renamed public init method
        # If a different session service is used, a specific clear method might be needed
        # await self.session_manager.clear_history(self.session_id)

    def _get_model_string(self, provider: Optional[str], model: Optional[str]) -> str:
        """Determines the model string format expected by LiteLLM."""
        target_provider = provider or self.config.default_provider
        target_model_name = model or self.config.default_model

        if target_provider == "openai":
            return target_model_name
        elif target_provider == "ai_studio":
            # For Google AI Studio, use the format 'google/model-name'
            # to ensure LiteLLM routes correctly
            return f"google/{target_model_name}"
        # Handle other providers
        return f"{target_provider}/{target_model_name}"

    def _get_api_base(self, provider: Optional[str]) -> Optional[str]:
        """Get the appropriate API base URL for the provider."""
        if provider == "ai_studio":
            # For Gemini API, use the base URL only, without any API path
            # This prevents LiteLLM from treating "streamGenerateContent" as a port
            # LiteLLM will handle constructing the full endpoint
            return "https://generativelanguage.googleapis.com"
        elif provider == "openai":
            return "https://api.openai.com/v1"
        elif provider == "groq":
            return "https://api.groq.com/openai/v1"
        elif provider == "anthropic":
            return "https://api.anthropic.com"
        elif provider == "ollama":
            # Get from config or use default
            return self.config.ollama.get("url", "http://localhost:11434")
        # For None or unhandled providers, use OpenAI's endpoint as fallback
        # This prevents errors when provider is None or unknown
        return "https://api.openai.com/v1"

    def _handle_model_not_found_error(self, model_string: str) -> str:
        """Handle model not found errors by listing available models and offering to fix the config."""
        from pathlib import Path

        import yaml

        print(f"[bold red]Error:[/bold red] Model '{model_string}' not found.")
        print("[yellow]Checking for available models...[/yellow]")

        try:
            # Try to use Google's GenerativeAI library to list models
            try:
                import google.generativeai as genai

                # Get API key
                provider = self.config.default_provider
                api_key = vars(self.config.api_keys).get(provider)

                if not api_key:
                    return "Could not find API key to check available models. Please check your configuration."

                # Configure the client
                genai.configure(api_key=api_key)

                # List available models
                models = genai.list_models()

                # Filter for relevant models
                suggested_models = []
                for model in models:
                    if "gemini" in model.name.lower():
                        model_name = model.name.split("/")[-1]  # Extract model name from path
                        # Check if the model name is similar to the requested one
                        if model_string.replace(".", "-") in model_name or model_name in model_string.replace(".", "-"):
                            suggested_models.append(model_name)

                if not suggested_models:
                    # If no similar models found, suggest a few standard ones
                    for model in models:
                        if "gemini" in model.name.lower():
                            model_name = model.name.split("/")[-1]
                            if "pro" in model_string.lower() and "pro" in model_name.lower():
                                suggested_models.append(model_name)
                            elif "flash" in model_string.lower() and "flash" in model_name.lower():
                                suggested_models.append(model_name)

                # Display suggestions
                if suggested_models:
                    print("\n[bold green]Available models that might work:[/bold green]")
                    for i, model_name in enumerate(suggested_models[:5], 1):  # Show top 5
                        print(f"  {i}. {model_name}")

                    # Offer to update config
                    from rich.prompt import Confirm, IntPrompt

                    if Confirm.ask(
                        "\nWould you like to update your configuration to use one of these models?",
                        default=True,
                    ):
                        # Ask which model to use
                        choice = 1  # Default to the first suggestion
                        if len(suggested_models) > 1:
                            choice = IntPrompt.ask(
                                "Enter the number of the model you want to use",
                                default=1,
                                show_choices=False,
                                show_default=True,
                            )
                            # Ensure valid range
                            choice = max(1, min(choice, len(suggested_models)))

                        # Get the selected model
                        selected_model = suggested_models[choice - 1]

                        # Update config file
                        config_path = Path.home() / ".config" / "code-agent" / "config.yaml"
                        if config_path.exists():
                            try:
                                # Read the current config
                                with open(config_path, "r") as f:
                                    config_data = yaml.safe_load(f) or {}

                                # Update the model
                                old_model = config_data.get("default_model", "")
                                config_data["default_model"] = selected_model

                                # Write the updated config
                                with open(config_path, "w") as f:
                                    yaml.dump(config_data, f, default_flow_style=False)

                                print(f"[bold green]✓ Configuration updated:[/bold green] Changed default_model from '{old_model}' to '{selected_model}'")
                                return f"Configuration updated to use model '{selected_model}'. Please try your request again."
                            except Exception as e:
                                print(f"[bold red]Error updating config:[/bold red] {e}")
                        else:
                            print(f"[bold yellow]Warning:[/bold yellow] Config file not found at {config_path}")

                    return f"Available models: {', '.join(suggested_models[:5])}. Please update your configuration to use one of these models."
                else:
                    print("[yellow]No similar models found for your provider.[/yellow]")
                    return "Could not find similar models. Please check your API key and provider configuration."

            except ImportError:
                print("[yellow]Google GenerativeAI package not installed. Cannot check for available models.[/yellow]")
                return "Cannot list available models. Try installing google-generativeai package."

        except Exception as e:
            print(f"[bold red]Error checking for available models:[/bold red] {e}")
            return f"Error checking for available models: {e!s}. Please verify your configuration."

    async def run_turn(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        quiet: bool = False,
    ) -> Optional[str]:
        """Run a single turn of the conversation.

        Args:
            prompt: The user prompt to process
            provider: Optional provider override (default: use config)
            model: Optional model override (default: use config)
            quiet: Whether to suppress output

        Returns:
            The response text, or None if error
        """
        await self._ensure_initialized()

        # Get effective provider/model from args or config
        provider = provider or self.config.default_provider
        model = model or self.config.default_model

        verbosity_controller = get_controller()
        verbosity_controller.show_verbose(f"Provider: {provider}, Model: {model}")

        # Generate session ID if not set
        if not self.session_id:
            sid, _ = self.session_manager.create_session()
            self.session_id = sid
            verbosity_controller.show_verbose(f"Created new session: {sid}")

        # Generate invocation ID for this turn
        invocation_id = Event.new_id()

        # Show session info in debug mode
        verbosity_controller.show_debug(f"Initializing Agent (Model: {model}, Provider: {provider}, Session: {self.session_id}, Invocation: {invocation_id})")

        # Add the user message to history
        await self.session_manager.add_user_message(session_id=self.session_id, content=prompt, invocation_id=invocation_id)

        # Build default system prompt if needed
        system_prompt = "\n".join(self.base_instruction_parts)

        # Special handling for the Ollama with ADK via LiteLLM wrapper
        if provider == "__ollama_adk__":
            from code_agent.adk.models import OllamaLlm

            # Get Ollama URL from config
            base_url = self.config.ollama.get("url", "http://localhost:11434")

            try:
                # Create an OllamaLlm instance for ADK
                ollama_model = OllamaLlm(
                    model_name=model,
                    base_url=base_url,
                    temperature=self.config.temperature or 0.7,
                    max_tokens=self.config.max_tokens,
                    timeout=60,  # Higher timeout for local models
                )

                # Create an ADK agent inline (minimalist approach)
                from google.adk.agents import LlmAgent

                # Define available tools as ADK FunctionTools
                from code_agent.adk.tools import (
                    create_apply_edit_tool,
                    create_run_terminal_cmd_tool,
                    read_file,
                )

                # Map our native tools to ADK tools
                apply_edit_tool = create_apply_edit_tool()
                run_cmd_tool = create_run_terminal_cmd_tool()

                # Create a minimal LlmAgent with the Ollama model
                adk_agent = LlmAgent(
                    model=ollama_model,
                    name="ollama_agent",
                    instruction=system_prompt,
                    tools=[read_file, apply_edit_tool, run_cmd_tool],
                    # No need for full session setup in this basic implementation
                )

                # Run the agent with the prompt
                verbosity_controller.show_verbose(f"Running ADK LlmAgent with Ollama model: {model}")
                result = await adk_agent.invoke(prompt)

                # Extract the response from the ADK result - normally this would be more complex with tool handling
                response_text = result.response.value

                # Add the assistant response to our session history
                await self.session_manager.add_assistant_message(
                    session_id=self.session_id,
                    content=response_text,
                    invocation_id=invocation_id,
                )

                return response_text

            except Exception as e:
                error_msg = f"Error using Ollama with ADK: {e!s}"
                verbosity_controller.show_error(error_msg)

                # Add error to session
                await self.session_manager.add_error_event(session_id=self.session_id, error_message=error_msg, invocation_id=invocation_id)

                return f"Error: {error_msg}"

        # Google AI Studio (Gemini API)
        elif provider == "ai_studio":
            return await self._run_turn_google_ai_studio(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                invocation_id=invocation_id,
                quiet=quiet,
            )

        # LiteLLM-supported providers
        else:
            return await self._run_turn_litellm(
                prompt=prompt,
                provider=provider,
                model=model,
                system_prompt=system_prompt,
                invocation_id=invocation_id,
                quiet=quiet,
            )

    def _convert_adk_events_to_litellm(self, events: List[Event]) -> List[Dict[str, Any]]:
        """Convert ADK Event objects to LiteLLM message format."""
        messages = []

        for event in events:
            # Skip events without content
            if event.event_data is None:
                continue

            event_type = event.event_type

            # Handle different event types
            if event_type == "user":
                # User messages are simple
                messages.append({"role": "user", "content": event.event_data.get("content", "")})
            elif event_type == "assistant":
                # For assistant messages, we need to handle both text and tool calls
                content = event.event_data.get("content", "")
                tool_calls = event.event_data.get("tool_calls", [])

                # Create the base message
                assistant_message = {"role": "assistant", "content": content}

                # Add tool calls if present
                if tool_calls:
                    # Convert the tool calls to the right format
                    litellm_tool_calls = []

                    for tool_call in tool_calls:
                        litellm_tool_call = {
                            "id": tool_call.get("id", f"call_{len(litellm_tool_calls)}"),
                            "type": "function",
                            "function": {"name": tool_call.get("name", ""), "arguments": json.dumps(tool_call.get("args", {}))},
                        }
                        litellm_tool_calls.append(litellm_tool_call)

                    assistant_message["tool_calls"] = litellm_tool_calls

                messages.append(assistant_message)
            elif event_type == "tool":
                # Tool events become tool response messages
                tool_id = event.event_data.get("id", "unknown_tool")
                content = event.event_data.get("result", "")

                messages.append({"role": "tool", "tool_call_id": tool_id, "content": content})
            elif event_type == "system":
                # System messages set up the context
                messages.append({"role": "system", "content": event.event_data.get("content", "")})

        return messages

    # Add a helper to run async methods for sync callers if needed, e.g., CLI
    def run_turn_sync(self, *args, **kwargs) -> Optional[str]:
        """Synchronous wrapper for run_turn."""
        # Ensure an event loop is running or create one
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: Cannot run the event loop while another loop is running'
            # Or 'RuntimeError: There is no current event loop...'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running (e.g., in Jupyter), create a task
            # This might require careful handling depending on the environment
            # For simple scripts/CLI, loop.run_until_complete is usually fine
            # Using loop.create_task might be better in some async frameworks
            # return asyncio.run_coroutine_threadsafe(self.run_turn(*args, **kwargs), loop).result() # Complex
            # Let's try a simpler approach first:
            future = asyncio.run_coroutine_threadsafe(self.run_turn(*args, **kwargs), loop)
            return future.result()  # This blocks until the coroutine is done
        else:
            return loop.run_until_complete(self.run_turn(*args, **kwargs))

    async def get_history_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for getting history in the old format for compatibility."""
        await self._ensure_initialized()
        events = await self.session_manager.get_history(self.session_id)
        old_format_history = []
        for event in events:
            # Skip partial and error events for simplified sync view
            if event.partial or event.error_message:
                continue

            role = None
            content = None
            if event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                if text_parts:
                    content = "\n".join(text_parts)

            if event.author == "user":
                role = "user"
            elif event.author == "assistant":
                role = "assistant"
            elif event.author == "system":
                role = "system"
            # Skipping tool calls/results in this view

            if role and content is not None:
                old_format_history.append({"role": role, "content": content})
        return old_format_history

    # Add other necessary methods or adjust existing ones

    async def _run_turn_google_ai_studio(
        self,
        prompt: str,
        model: str,
        system_prompt: str,
        invocation_id: str,
        quiet: bool = False,
    ) -> Optional[str]:
        """Runs a turn using Google's GenAI library directly for Google AI Studio models."""
        response_text = ""
        # Initialize current_assistant_event_id to avoid UnboundLocalError if exceptions occur
        current_assistant_event_id = None

        try:
            # Get API key for Google AI Studio
            api_key = vars(self.config.api_keys).get("ai_studio")

            # Check for missing API key
            if not api_key:
                error_message = "API key for Google AI Studio is invalid or missing."
                if not quiet:
                    print(f"[bold red]Error:[/bold red] {error_message}")

                # Add error message to session history
                await self.session_manager.add_assistant_message(session_id=self.session_id, content=error_message, invocation_id=invocation_id)
                return error_message

            # Configure genai with API key
            genai.configure(api_key=api_key)

            # Set up the model
            generation_config = {
                "temperature": self.config.temperature,
                "top_p": 0.95,
                "top_k": 0,
                "max_output_tokens": 8192,
            }

            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # Create model
            model_obj = genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )

            # Define our tool schemas - Updated format compatible with Google GenerativeAI API
            # Structure includes separate entries for native tools and function declarations
            tools = [
                {"google_search": {}},  # Enable native Google Search
                {
                    "function_declarations": [
                        # Keep existing custom function declarations here
                        {
                            "name": "read_file",
                            "description": "Reads a file from the filesystem",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "filename": {
                                        "type": "STRING",
                                        "description": "The file to read",
                                    },
                                    "line_start": {
                                        "type": "INTEGER",
                                        "description": "Start line (0-indexed)",
                                    },
                                    "line_count": {
                                        "type": "INTEGER",
                                        "description": "Number of lines to read",
                                    },
                                },
                                "required": ["filename"],
                            },
                        },
                        {
                            "name": "load_memory",
                            "description": "Retrieves information from long-term memory based on a search query",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "query": {
                                        "type": "STRING",
                                        "description": "The search query to find relevant information",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "apply_edit",
                            "description": "Applies an edit to a file",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "filename": {
                                        "type": "STRING",
                                        "description": "The file to edit",
                                    },
                                    "edit_instruction": {
                                        "type": "STRING",
                                        "description": "A natural language instruction for how to edit the file",
                                    },
                                    "edit": {
                                        "type": "STRING",
                                        "description": "The full contents to write to the file, or a description of the change to make",
                                    },
                                },
                                "required": ["filename", "edit"],
                            },
                        },
                        {
                            "name": "run_native_command",
                            "description": "Runs a native command on the system",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "command": {
                                        "type": "STRING",
                                        "description": "The native command to run",
                                    },
                                },
                                "required": ["command"],
                            },
                        },
                        # google_search declaration removed from here
                        {
                            "name": "set_verbosity",
                            "description": "Sets the verbosity level for the agent's output",
                            "parameters": {
                                "type": "OBJECT",
                                "properties": {
                                    "level": {
                                        "type": "STRING",
                                        "description": "The verbosity level, possible values are: QUIET, NORMAL, VERBOSE, DEBUG",
                                    },
                                },
                                "required": ["level"],
                            },
                        },
                    ]
                },
            ]

            # Define available tools with their functions (DOES NOT include google_search)
            available_tools = {
                "read_file": read_file,
                "apply_edit": apply_edit,
                "run_native_command": run_native_command,
                "load_memory": load_memory,
                "set_verbosity": set_verbosity,
            }

            # If we got a quota error, provide a fallback response
            try:
                # Get history from ADK session for context
                history_events = await self.session_manager.get_history(self.session_id)

                # Convert ADK events to Google's format
                chat_history = []
                for event in history_events:
                    # Skip the current user message since we're adding it separately
                    if event.author == "user" and event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                        if text_parts and event.content.role == "user":
                            # Only add previous user messages (not the current one we're processing)
                            if text_parts[0] != prompt:
                                chat_history.append({"role": "user", "parts": [{"text": text_parts[0]}]})

                    elif event.author == "assistant" and event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                        if text_parts and event.content.role == "assistant":
                            chat_history.append({"role": "model", "parts": [{"text": text_parts[0]}]})

                # Add system message
                messages = [
                    {"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "I understand and will follow these instructions."}]},
                ]

                # Add chat history
                messages.extend(chat_history)

                # Add current user message
                messages.append({"role": "user", "parts": [{"text": prompt}]})

                with thinking_indicator("Agent is thinking...") as indicator:
                    try:
                        # Generate the response
                        response = model_obj.generate_content(messages, stream=True, tools=tools)

                        # Process the streaming response
                        accumulated_text = ""
                        current_assistant_event_id = None

                        for chunk in response:
                            # Check for tool calls
                            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                                part = chunk.candidates[0].content.parts[0]

                                if hasattr(part, "text") and part.text:
                                    # Handle text response
                                    accumulated_text += part.text
                                    if not quiet:
                                        print(part.text, end="", flush=True)

                                    # Add/update partial assistant message
                                    if current_assistant_event_id is None:
                                        current_assistant_event_id = await self.session_manager.add_assistant_message(
                                            session_id=self.session_id,
                                            content=accumulated_text,
                                            partial=True,
                                            invocation_id=invocation_id,
                                        )

                                # Check for function calls
                                if hasattr(part, "function_call"):
                                    # Skip empty tool calls
                                    if part.function_call.name == "":
                                        verbosity_controller = get_controller()
                                        verbosity_controller.show_debug("Empty tool call received, skipping")
                                        continue

                                    # Normal tool call processing
                                    function_name = part.function_call.name

                                    # Convert function_args from MapComposite to dictionary
                                    # to ensure it's JSON serializable
                                    try:
                                        if hasattr(part.function_call.args, "__dict__"):
                                            # If it's an object with __dict__, convert to dict
                                            function_args = dict(part.function_call.args)
                                        elif hasattr(part.function_call.args, "items"):
                                            # If it has items() method like a dict-like object
                                            function_args = {k: v for k, v in part.function_call.args.items()}
                                        else:
                                            # Fallback to string representation and try to parse as JSON
                                            function_args_str = str(part.function_call.args)
                                            try:
                                                function_args = json.loads(function_args_str)
                                            except json.JSONDecodeError:
                                                function_args = {"raw_args": function_args_str}
                                    except Exception as args_err:
                                        print(f"[bold red]Error parsing function args:[/bold red] {args_err}")
                                        function_args = {}  # Empty dict as fallback

                                    if not quiet:
                                        print(f"\n[grey50]🔧 Tool call: {function_name}[/grey50]")

                                    # Execute the tool
                                    if function_name in available_tools:
                                        tool_call_id = Event.new_id()

                                        # Add assistant tool call message
                                        await self.session_manager.add_assistant_message(
                                            session_id=self.session_id,
                                            content=accumulated_text if accumulated_text else None,
                                            tool_calls=[genai_types.FunctionCall(name=function_name, args=function_args)],
                                            invocation_id=invocation_id,
                                            partial=False,
                                        )

                                        # Execute the tool
                                        try:
                                            if not quiet:
                                                print(f"[grey50]↪ Calling tool: {function_name}({json.dumps(function_args)})[/grey50]")
                                            tool_func = available_tools[function_name]
                                            tool_output = await asyncio.to_thread(tool_func, **function_args)
                                            result_content = tool_output  # Store successful result
                                            if not quiet:
                                                print(f"[grey50]↩ Tool response ({function_name}): {tool_output}[/grey50]")
                                            # Add tool result to session
                                            await self.session_manager.add_tool_result(
                                                session_id=self.session_id,
                                                tool_call_id=tool_call_id,
                                                tool_name=function_name,
                                                content=result_content,
                                                invocation_id=invocation_id,
                                            )
                                            # We've successfully used a tool, update the accumulated text
                                            # and return the response so far for a better user experience
                                            if accumulated_text:
                                                response_text = accumulated_text

                                                # Add a final message to indicate we're stopping due to quota limitations
                                                quota_warning = (
                                                    "\n\n[Note: Due to API quota limitations, the conversation will continue after the next user message.]"
                                                )
                                                if not quiet:
                                                    print(quota_warning)

                                                response_text += quota_warning

                                                # Add final message to session
                                                await self.session_manager.add_assistant_message(
                                                    session_id=self.session_id,
                                                    content=response_text,
                                                    invocation_id=invocation_id,
                                                    partial=False,
                                                )

                                                # If we finish the turn successfully, save to memory
                                                session = await self.session_manager.get_session(self.session_id)
                                                get_memory_service().add_session_to_memory(session)
                                                verbosity_controller.show_debug("Session added to long-term memory")

                                                return response_text
                                        except Exception as e:
                                            error_msg = format_tool_error(e, function_name, function_args)
                                            print(f"[bold red]Error:[/bold red] {error_msg}")

                                            # Add error to session
                                            await self.session_manager.add_tool_result(
                                                session_id=self.session_id,
                                                tool_call_id=tool_call_id,
                                                tool_name=function_name,
                                                content=error_msg,
                                                invocation_id=invocation_id,
                                            )

                                            # Return error as response to avoid quota issues
                                            response_text = f"Error executing tool {function_name}: {error_msg}"
                                            return response_text
                                    elif function_name == "google_search":
                                        # The GenAI API handles grounding internally.
                                        # The search results will be part of the next model response.
                                        # We acknowledge the tool call here but don't execute a local function.
                                        verbosity_controller.show_debug("Acknowledged google_search tool call. Expecting grounded response.")
                                        # We need to send *something* back to the model to continue the conversation
                                        # Send back an empty result for the search tool call
                                        tool_call_id = Event.new_id()  # Need an ID for the result
                                        await self.session_manager.add_tool_result(
                                            session_id=self.session_id,
                                            tool_call_id=tool_call_id,
                                            tool_name=function_name,
                                            content="",  # Sending empty result
                                            invocation_id=invocation_id,
                                        )
                                        # Unlike other tools, we don't return here, we let the loop continue
                                        # to get the final grounded response from the LLM after this tool acknowledgement.
                                    else:
                                        print(f"[bold red]Unknown tool:[/bold red] {function_name}")

                        # If we reach here, we got a complete response without tool calls
                        response_text = accumulated_text

                    except Exception as e:
                        # Handle quota or other generation exceptions
                        if "429" in str(e) or "Resource has been exhausted" in str(e):
                            quota_msg = "Google AI Studio API quota has been exhausted. Please try again later or use a different provider."
                            print(f"[bold yellow]Quota Error:[/bold yellow] {quota_msg}")
                            response_text = f"Hello! I received your message: '{prompt}'\n\n{quota_msg}"
                        else:
                            # Other general errors
                            import traceback

                            error_details = traceback.format_exc()
                            error_message = f"An error occurred with Google AI Studio: {e}"
                            print(f"[bold red]{error_message}[/bold red]")
                            print(f"[grey50]{error_details}[/grey50]")
                            response_text = f"Error: {error_message}"

            except Exception as e:
                # Handle any errors in history processing
                import traceback

                error_details = traceback.format_exc()
                error_message = f"Error preparing conversation for Google AI Studio: {e}"
                print(f"[bold red]{error_message}[/bold red]")
                print(f"[grey50]{error_details}[/grey50]")
                response_text = f"Error: {error_message}"

            # Add final message to session history if needed
            if response_text and current_assistant_event_id is None:
                await self.session_manager.add_assistant_message(
                    session_id=self.session_id,
                    content=response_text,
                    invocation_id=invocation_id,
                    partial=False,
                )

            return response_text

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            error_message = f"Error using Google AI Studio: {e}"
            print(f"[bold red]{error_message}[/bold red]")
            print(f"[grey50]{error_details}[/grey50]")

            # Add error to session
            try:
                await self.session_manager.add_error_event(
                    session_id=self.session_id, error_message=error_message, error_code="AI_STUDIO_ERROR", invocation_id=invocation_id
                )
            except Exception as log_err:
                print(f"[bold red]Failed to log error to session:[/bold red] {log_err}")

            # Fall back to a simple response if all else fails
            fallback_response = f"Hello! I received your message: '{prompt}'\n\nI'm having some technical difficulties connecting to Google AI Studio. Please try again later or use a different provider."

            # Add the fallback response to the session
            await self.session_manager.add_assistant_message(
                session_id=self.session_id,
                content=fallback_response,
                invocation_id=invocation_id,
                partial=False,
            )

            return fallback_response

    async def _run_turn_litellm(
        self,
        prompt: str,
        provider: str,
        model: str,
        system_prompt: str,
        invocation_id: str,
        quiet: bool = False,
    ) -> Optional[str]:
        """Runs a turn using litellm with streaming and function calling."""
        # Get model string in proper format for LiteLLM
        model_string = self._get_model_string(provider, model)
        api_base = self._get_api_base(provider)

        # Initialize current_assistant_event_id to avoid UnboundLocalError if exceptions occur
        current_assistant_event_id = None

        # Get API key for the provider
        api_key = vars(self.config.api_keys).get(provider)

        # Check for missing API key
        if not api_key:
            error_message = f"API key for {provider} is invalid or missing."
            if not quiet:
                print(f"[bold red]Error:[/bold red] {error_message}")

            # Add error message to session history
            await self.session_manager.add_assistant_message(session_id=self.session_id, content=error_message, invocation_id=invocation_id)
            return error_message

        # Define tool definitions for LiteLLM
        tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from the filesystem",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The path to the file to read",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "load_memory",
                    "description": "Retrieves information from long-term memory based on a search query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant information",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_edit",
                    "description": "Create a new file or modify an existing file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The path of the file to edit",
                            },
                            "content": {
                                "type": "string",
                                "description": "The full content to write to the file",
                            },
                            "show_diff": {
                                "type": "boolean",
                                "description": "Whether to show the diff before applying the edit",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "name": "run_native_command",
                "description": "Runs a native command on the system",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The native command to run",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "google_search",
                "description": "Searches the web for information using Google Search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "set_verbosity",
                "description": "Sets the verbosity level for the agent's output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "description": "The verbosity level, possible values are: QUIET, NORMAL, VERBOSE, DEBUG",
                        },
                    },
                    "required": ["level"],
                },
            },
        ]

        # Define available tools
        available_tools = {
            "read_file": read_file,
            "apply_edit": apply_edit,
            "run_native_command": run_native_command,
            "load_memory": load_memory,
            "set_verbosity": set_verbosity,
        }

        response_text = ""  # Store the final accumulated text response here
        loop_ended_naturally = True  # Flag to track if loop finished without break

        try:
            with thinking_indicator("Agent is thinking...") as indicator:
                tool_calls_pending = True
                tool_call_count = 0
                current_invocation_id = invocation_id  # Track current invocation
                last_assistant_event_id = None  # Track the ID of the last partial assistant event

                while tool_calls_pending and tool_call_count < self.config.max_tool_calls:
                    tool_calls_pending = False  # Assume no more tools unless requested
                    indicator.update(f"Agent is thinking... (Model Call {tool_call_count + 1})")

                    # Always get the latest history before a model call
                    history_events = await self.session_manager.get_history(self.session_id)
                    messages = self._convert_adk_events_to_litellm(history_events)

                    # Debug logging to check messages
                    verbosity_controller = get_controller()
                    verbosity_controller.show_debug(f"Messages count={len(messages)}")

                    # Ensure we have at least some messages before calling the model
                    if len(messages) == 0:
                        verbosity_controller.show_warning("No messages in history. Adding a default system message.")
                        # Add a default system message to avoid empty messages list
                        messages.append({"role": "system", "content": system_prompt})

                    # --- Start LLM Call ---
                    try:
                        # Only include api_base if it's not None and not empty
                        kwargs = {
                            "model": model_string,
                            "messages": messages,
                            "api_key": api_key,
                            "tools": tool_definitions,
                            "stream": True,
                            "temperature": self.config.temperature,
                        }

                        # Add api_base only if it's provided and non-empty
                        if api_base:
                            kwargs["api_base"] = api_base

                        stream = await litellm.acompletion(**kwargs)

                        # --- Stream Processing ---
                        collected_chunks = []
                        current_assistant_event_id = None  # Reset for this stream
                        current_tool_calls = []
                        this_stream_text = ""  # Accumulate text ONLY for this stream

                        async for chunk in stream:
                            collected_chunks.append(chunk)
                            delta = chunk.choices[0].delta

                            if delta.content:
                                this_stream_text += delta.content
                                if not quiet:
                                    print(delta.content, end="", flush=True)
                                # Add/Update partial event
                                if current_assistant_event_id is None:
                                    current_assistant_event_id = await self.session_manager.add_assistant_message(
                                        session_id=self.session_id,
                                        content=this_stream_text,
                                        partial=True,
                                        invocation_id=current_invocation_id,
                                    )
                                    last_assistant_event_id = current_assistant_event_id  # Track ID
                                else:
                                    # No update_event, so potentially create another partial event
                                    # Or just update the text buffer and only add final event?
                                    # Let's stick to adding partials for now, final clean up later.
                                    # We could potentially call add_assistant_message again with updated text
                                    pass  # Avoid calling update_event

                            if delta.tool_calls:
                                tool_calls_pending = True  # We have tool calls, so loop might continue
                                if not quiet and delta.content:  # Add newline if text was printed before tool indicator
                                    print()

                                for tc_delta in delta.tool_calls:
                                    if tc_delta.index is not None and tc_delta.index >= len(current_tool_calls):
                                        # Start of a new tool call
                                        current_tool_calls.append(
                                            {
                                                "id": tc_delta.id or Event.new_id(),  # Generate ID if missing
                                                "function": {"name": "", "arguments": ""},
                                                "type": "function",  # Assuming 'function' type
                                            }
                                        )
                                        if tc_delta.function and tc_delta.function.name:
                                            current_tool_calls[tc_delta.index]["function"]["name"] = tc_delta.function.name
                                            if not quiet:
                                                print(f"[grey50]🔧 Requesting tool: {tc_delta.function.name}[/grey50]")

                                    if tc_delta.function and tc_delta.function.arguments:
                                        # Append arguments as they stream
                                        current_tool_calls[tc_delta.index]["function"]["arguments"] += tc_delta.function.arguments

                        # --- End of Stream ---
                        if not quiet and this_stream_text and not tool_calls_pending:
                            print()  # Final newline

                        # Check if this stream resulted in the final response
                        if not tool_calls_pending:
                            response_text = this_stream_text  # Capture the final text
                            # Loop will terminate naturally

                        # --- Tool Execution ---
                        elif tool_calls_pending:
                            tool_call_count += len(current_tool_calls)

                            if tool_call_count >= self.config.max_tool_calls:
                                max_calls_msg = f"Reached maximum tool calls ({self.config.max_tool_calls})."
                                print(f"[bold yellow]Warning:[/bold yellow] {max_calls_msg}")
                                await self.session_manager.add_assistant_message(
                                    session_id=self.session_id,
                                    content=max_calls_msg,
                                    invocation_id=current_invocation_id,
                                    partial=False,
                                )
                                response_text = max_calls_msg
                                tool_calls_pending = False  # Ensure loop terminates
                                loop_ended_naturally = False  # Loop broken
                                break  # Exit the while loop immediately

                            # --- Add Assistant Message Requesting Tools (before execution) ---
                            adk_tool_calls_for_history = []
                            try:
                                for tc in current_tool_calls:
                                    adk_tool_calls_for_history.append(
                                        genai_types.FunctionCall(name=tc["function"]["name"], args=json.loads(tc["function"]["arguments"]))
                                    )
                            except json.JSONDecodeError as e:
                                print(f"[bold red]Internal Error:[/bold red] Failed to parse tool call arguments for history storage: {e}")

                            # Add a new event for the tool request
                            await self.session_manager.add_assistant_message(
                                session_id=self.session_id,
                                content=this_stream_text if this_stream_text else None,  # Include any preceding text
                                tool_calls=adk_tool_calls_for_history,
                                invocation_id=current_invocation_id,
                                partial=False,  # This request is final
                            )

                            # --- Execute Tools ---
                            for tool_call in current_tool_calls:
                                function_name = tool_call["function"]["name"]
                                tool_call_id = tool_call["id"]
                                arguments_str = tool_call["function"]["arguments"]
                                tool_input = None
                                result_content = ""  # Initialize result_content

                                # Tool processing
                                try:
                                    # Parse arguments
                                    try:
                                        tool_input = json.loads(arguments_str)
                                    except json.JSONDecodeError as json_err:
                                        error_msg = f"Error decoding arguments for tool '{function_name}': {json_err}. Raw args: '{arguments_str}'"
                                        print(f"[bold red]Error:[/bold red] {error_msg}")
                                        result_content = error_msg  # Assign error to result

                                    # Execute the tool if args parsed okay
                                    if not result_content:  # Only execute if no parsing error
                                        if function_name in available_tools:
                                            try:
                                                if not quiet:
                                                    print(f"[grey50]↪ Calling tool: {function_name}({json.dumps(tool_input)})[/grey50]")
                                                tool_func = available_tools[function_name]
                                                tool_output = await asyncio.to_thread(tool_func, **tool_input)
                                                result_content = tool_output  # Store successful result
                                                if not quiet:
                                                    print(f"[grey50]↩ Tool response ({function_name}): {tool_output}[/grey50]")
                                            except Exception as tool_exec_err:
                                                error_msg = format_tool_error(tool_exec_err, function_name, tool_input if tool_input else arguments_str)
                                                print(f"[bold red]Error:[/bold red] {error_msg}")
                                                result_content = error_msg
                                        else:
                                            error_msg = f"Unknown tool: {function_name}"
                                            print(f"[bold red]Error:[/bold red] {error_msg}")
                                            result_content = error_msg
                                except Exception as outer_tool_err:
                                    error_msg = f"Unexpected error processing tool '{function_name}': {outer_tool_err}"
                                    print(f"[bold red]Error:[/bold red] {error_msg}")
                                    result_content = error_msg

                                # Add tool result event (runs after try/except)
                                await self.session_manager.add_tool_result(
                                    session_id=self.session_id,
                                    tool_call_id=tool_call_id,
                                    tool_name=function_name,
                                    content=result_content,
                                    invocation_id=current_invocation_id,
                                )
                            # Tool execution finished, loop continues

                    except litellm.exceptions.BadRequestError as e:
                        error_message = f"Bad request to LLM provider: {format_api_error(e, provider, model)}"
                        print(f"[bold red]Error:[/bold red] {error_message}")
                        await self.session_manager.add_error_event(
                            session_id=self.session_id, error_message=error_message, error_code="BAD_REQUEST", invocation_id=current_invocation_id
                        )
                        response_text = f"Error: {error_message}"
                        loop_ended_naturally = False  # Loop broken
                        break

                    except litellm.exceptions.AuthenticationError as e:
                        error_message = f"Authentication error with provider {provider}: {format_api_error(e, provider, model)}"
                        print(f"[bold red]Error:[/bold red] {error_message}")
                        await self.session_manager.add_error_event(
                            session_id=self.session_id, error_message=error_message, error_code="AUTH_ERROR", invocation_id=current_invocation_id
                        )
                        response_text = f"Error: {error_message}"
                        loop_ended_naturally = False  # Loop broken
                        break

                    except Exception as e:
                        # This catches errors during the LLM call itself
                        import traceback

                        error_message = f"An unexpected error occurred during LLM call: {e}"
                        print(f"[bold red]{error_message}[/bold red]")
                        print(f"[grey50]{traceback.format_exc()}[/grey50]")
                        # Add error event to session
                        await self.session_manager.add_error_event(
                            session_id=self.session_id, error_message=error_message, error_code="UNEXPECTED_ERROR", invocation_id=current_invocation_id
                        )
                        response_text = f"Error: {error_message}"  # Final response is the error
                        tool_calls_pending = False  # Ensure loop termination
                        loop_ended_naturally = False  # Loop broken
                        break  # Exit the loop on unexpected error

                # --- End of While Loop ---
                # Add final non-partial assistant message IF loop finished naturally
                if loop_ended_naturally and response_text:
                    await self.session_manager.add_assistant_message(
                        session_id=self.session_id,
                        content=response_text,
                        partial=False,
                        invocation_id=current_invocation_id,
                    )

            # Save the completed session to memory for future reference
            if response_text and loop_ended_naturally:
                session = await self.session_manager.get_session(self.session_id)
                get_memory_service().add_session_to_memory(session)
                verbosity_controller.show_debug("Session added to long-term memory")

        except Exception as e:  # This catches errors OUTSIDE the while loop
            import traceback

            error_message = f"An unexpected error occurred outside the LLM loop: {e}"
            print(f"[bold red]{error_message}[/bold red]")
            print(f"[grey50]{traceback.format_exc()}[/grey50]")
            # Add error event to session if possible
            try:
                await self.session_manager.add_error_event(
                    session_id=self.session_id,
                    error_message=error_message,
                    error_code="AGENT_ERROR",
                    invocation_id=invocation_id,  # Use original invocation ID
                )
            except Exception as log_err:
                print(f"[bold red]Failed to log agent error to session:[/bold red] {log_err}")
            # Set response_text here as well before returning
            response_text = f"Error: {error_message}"

        return response_text


# Example of how to call async methods from sync code (like the CLI)
# agent = CodeAgent()
# result = asyncio.run(agent.run_turn("Your prompt here"))
# Or using the sync wrapper if needed:
# result = agent.run_turn_sync("Your prompt here")
