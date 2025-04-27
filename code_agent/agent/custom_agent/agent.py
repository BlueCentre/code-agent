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

import logging # Add import

logger = logging.getLogger(__name__) # Get logger instance

# --- Tool Management --- # Added Section Header
# Assuming ToolManager exists and can be imported
try:
    from code_agent.tools import ToolManager # Use the correct path for ToolManager
except ImportError:
    # Define a placeholder if ToolManager is not available or refactored
    class ToolManager:
        def __init__(self, tools=None):
            self._tools = tools or []
        def get_tools(self): return self._tools
        async def execute_tool(self, name, **kwargs): return {"error": f"Tool '{name}' not found or ToolManager not fully implemented."}
        def get_tool_schema(self): return [] # Placeholder schema

# Define available tools (ensure imports are correct)
# These should match the tools intended for use with LiteLLM/ToolManager
# We might need to adjust this based on actual ToolManager implementation
AVAILABLE_TOOLS_LIST = [
    read_file,
    apply_edit,
    run_native_command,
    load_memory,
    set_verbosity,
    # Add other tools managed by ToolManager if necessary
]

class CodeAgent:
    """Core class for the Code Agent, handling interaction loops and tool use using ADK sessions."""

    def __init__(self):
        self.config: CodeAgentSettings = get_config()  # Changed from initialize_config().agent_settings
        self.session_id: Optional[str] = None  # SessionId -> str
        self.session_manager: Optional[CodeAgentADKSessionManager] = None
        self.auth_token: Optional[str] = None  # Add auth token for session access
        self.verbosity: int = 1  # Default verbosity level
        self._initialized: bool = False  # Flag to track async initialization

        # ---- Add Missing Attributes ----
        self.agent_name: str = "CodeAgent" # Added agent_name
        self.tool_manager = ToolManager(tools=AVAILABLE_TOOLS_LIST) # Added ToolManager instance
        self.streaming_callback: Optional[callable] = None # Added streaming_callback
        self.tool_call_ids: Dict[str, str] = {} # Added tool_call_ids mapping (func_name -> llm_tool_call_id)
        # ---- End Add Missing Attributes ----

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

        # Add rules directly, as self.config.rules is always a list
        # Explicitly check type just in case validation was bypassed
        if self.config.rules and isinstance(self.config.rules, list):
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
            # Ensure self.config.ollama exists and is a dict before accessing 'base_url'
            ollama_config = getattr(self.config, 'ollama', None)
            if isinstance(ollama_config, dict):
                # Check for 'base_url' key specifically
                return ollama_config.get("base_url", "http://localhost:11434")
            else:
                return "http://localhost:11434" # Default if config section is missing/invalid
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
        """Convert ADK Event objects to LiteLLM message format, ensuring correct roles and tool call linking."""
        messages = []
        # Store generated tool call IDs from assistant messages to match responses
        # Key: Event ID of the assistant request, Value: Dict[tool_name, tool_call_id]
        # Using Event ID assumes one assistant event generates related tool calls.
        request_to_tool_ids: Dict[str, Dict[str, str]] = {}

        for i, event in enumerate(events):
            # Skip events without content or parts
            if not event.content or not event.content.parts:
                continue

            author = event.author
            content_role = event.content.role # ADK role (e.g., 'user', 'model', 'function')
            parts = event.content.parts
            event_id = event.id

            # Extract data from parts
            text_content = " ".join([p.text for p in parts if hasattr(p, 'text') and p.text])
            function_calls = [p.function_call for p in parts if hasattr(p, 'function_call') and p.function_call]
            function_responses = [p.function_response for p in parts if hasattr(p, 'function_response') and p.function_response]

            litellm_role = None
            litellm_message = {}

            if author == "user":
                litellm_role = "user"
                litellm_message = {"role": litellm_role, "content": text_content}

            elif author == "system":
                litellm_role = "system"
                litellm_message = {"role": litellm_role, "content": text_content}

            elif author == "assistant":
                # ADK event from assistant. Could be a response, tool request, or tool result.
                if content_role == "function" and function_responses:
                    # ADK Tool Result event -> LiteLLM 'tool' role message
                    litellm_role = "tool"
                    for func_resp in function_responses:
                        tool_name = func_resp.name
                        tool_call_id_to_match = None

                        # Search backwards through previous assistant events for the request ID
                        for req_event_id, tool_map in reversed(request_to_tool_ids.items()):
                            if tool_name in tool_map:
                                tool_call_id_to_match = tool_map[tool_name]
                                # Optional: Remove from map once matched? Depends if IDs must be unique per run.
                                # del request_to_tool_ids[req_event_id][tool_name]
                                break

                        if tool_call_id_to_match:
                            result_content = ""
                            if isinstance(func_resp.response, dict):
                                result_content = func_resp.response.get("result", json.dumps(func_resp.response))
                            else:
                                result_content = str(func_resp.response)

                            # Append a separate message for each tool result
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id_to_match,
                                "content": result_content,
                                # "name": tool_name # LiteLLM doesn't typically use name here
                            })
                        else:
                            # If no matching request ID found, SKIP this tool result message
                            print(f"[Code Agent Warning] Skipping tool result for '{tool_name}' from event {event_id} - could not find matching request ID.")
                    continue # Skip adding a main message for this event if it only contained tool results

                else:
                    # ADK Assistant response/request -> LiteLLM 'assistant' role message
                    litellm_role = "assistant"
                    litellm_message = {"role": litellm_role, "content": text_content or None}

                    if function_calls:
                        litellm_tool_calls = []
                        tool_id_map = {}
                        for func_call in function_calls:
                            # Generate unique LiteLLM tool call ID
                            tool_call_id = f"call_{func_call.name}_{event_id}"
                            litellm_tool_call = {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": func_call.name,
                                    "arguments": json.dumps(func_call.args or {}),
                                },
                            }
                            litellm_tool_calls.append(litellm_tool_call)
                            # Store mapping for potential future results
                            tool_id_map[func_call.name] = tool_call_id

                        if tool_id_map:
                            request_to_tool_ids[event_id] = tool_id_map
                        litellm_message["tool_calls"] = litellm_tool_calls

                    # Ensure content is not empty string if no text content, should be None
                    if not litellm_message["content"] and not litellm_message.get("tool_calls"):
                         continue # Skip empty assistant messages
                    if not litellm_message["content"]:
                         litellm_message["content"] = None # Use None instead of empty string if only tool calls

            # Append the constructed message if a role was determined
            if litellm_role and litellm_message:
                 # Special case: If this is the *very last* event and it's from the user,
                 # ensure its role is 'user' for LiteLLM, even if ADK role differs.
                 # (This handles cases where the ADK might use a different role internally)
                 # However, based on current logic, author=='user' already sets role='user'.
                 # Let's ensure no empty content for user/system messages either.
                 if litellm_role in ["user", "system"] and not litellm_message["content"]:
                     continue # Skip empty user/system messages

                 messages.append(litellm_message)


        # Final check: Ensure the very last message has role 'user' if the turn started with a user prompt.
        # This might be too simplistic. The run_turn loop likely handles adding the final user prompt separately.
        # Let's rely on the per-event logic for now.

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
        initial_messages: Optional[List[Dict[str, Any]]] = None, # Accept initial messages
    ) -> Optional[str]:
        """Runs a turn using litellm with streaming and function calling."""
        # Get model string in proper format for LiteLLM
        model_string = self._get_model_string(provider, model)
        api_base = self._get_api_base(provider)

        # Initialize current_assistant_event_id to avoid UnboundLocalError if exceptions occur
        current_assistant_event_id = None

        # Get API key for the provider
        api_key = vars(self.config.api_keys).get(provider)

        # Check for missing API key, skip for providers like Ollama
        # Add other keyless providers here if needed
        if provider != "ollama" and not api_key:
            error_message = f"API key for {provider} is invalid or missing."
            if not quiet:
                # Use rich print for better formatting if available
                try:
                    from rich import print
                    print(f"[bold red]Error:[/bold red] {error_message}")
                except ImportError:
                    print(f"Error: {error_message}") # Fallback

            # Add error message to session history (as assistant message for context)
            # Consider adding a specific error event type if ADK supports it better
            await self.session_manager.add_assistant_message(session_id=self.session_id, content=error_message, invocation_id=invocation_id)
            # logger.error(error_message) # Log the error
            return error_message

        # Define tool definitions for LiteLLM
        tool_definitions = self._get_tool_definitions()

        # Define available tools (mapping names to actual functions/methods)
        # Use tool.__name__ to get the function name
        available_tools = {
            tool.__name__: getattr(self.tool_manager, tool.__name__)
            for tool in self.tool_manager.get_tools()
            if hasattr(self.tool_manager, tool.__name__) # Check attribute using function name
        }
        logger.debug(f"Available tools prepared for LLM: {list(available_tools.keys())}")


        response_text = ""  # Store the final accumulated text response here
        loop_ended_naturally = True  # Flag to track if loop finished without break

        # Use the passed initial_messages for the first iteration
        messages = initial_messages if initial_messages is not None else []
        # If initial_messages wasn't passed (e.g., direct call), construct it
        if not messages:
             history_events = await self.session_manager.get_history(self.session_id)
             converted_history = self._convert_adk_events_to_litellm(history_events)
             if system_prompt:
                 messages.append({"role": "system", "content": system_prompt})
             messages.extend(converted_history)
             # Explicitly add the current user prompt for this turn
             if prompt:
                 messages.append({"role": "user", "content": prompt})


        try:
            with thinking_indicator("Agent is thinking...") as indicator:
                tool_calls_pending = True # Start assuming a tool call might be needed, loop checks response
                tool_call_count = 0
                current_invocation_id = invocation_id  # Track current invocation
                last_assistant_event_id = None  # Track the ID of the last partial assistant event

                while tool_calls_pending and tool_call_count < self.config.max_tool_calls:
                    # Reset pending flag for this iteration. It will be set True if LLM requests tools.
                    tool_calls_pending = False
                    indicator.update(f"Agent is thinking... (Model Call {tool_call_count + 1})")

                    # If this is NOT the first call (i.e., we are processing tool results from previous iteration),
                    # rebuild the messages list based on the *updated* history
                    # which now includes the previous assistant request and tool results.
                    if tool_call_count > 0:
                        # 1. Get latest history events (includes previous tool results)
                        history_events = await self.session_manager.get_history(self.session_id)
                        # 2. Convert *all* relevant history events to LiteLLM format
                        #    This now includes user, assistant requests, AND tool results.
                        converted_history_and_results = self._convert_adk_events_to_litellm(history_events)
                        # 3. Construct the final messages list for LiteLLM for this iteration
                        messages = []
                        # Add system prompt first if it exists
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        # Add the converted historical messages (including latest tool results)
                        messages.extend(converted_history_and_results)
                        # DO NOT re-add the original user prompt here, it's in the history.
                    # Else (first call, tool_call_count == 0), 'messages' list is already prepared outside the loop


                    # Debug logging to check final messages sent to LLM
                    verbosity_controller = get_controller()
                    # Ensure messages is actually defined here before logging
                    if messages:
                        verbosity_controller.show_debug(f"Final messages sent to LLM: {json.dumps(messages, indent=2)}")
                    else:
                         verbosity_controller.show_debug("Messages list is unexpectedly empty before LLM call.")
                         logger.warning("Messages list is unexpectedly empty before LLM call.")

                    # ---- START DEBUG LOG ----
                    try:
                        # import json # Already imported at top level
                        logger.debug(f"Messages sent to LiteLLM:\n{json.dumps(messages, indent=2)}")
                    except Exception as log_e:
                        logger.error(f"Failed to log messages: {log_e}")
                    # ---- END DEBUG LOG ----

                    try:
                        # 4. Send the messages to LiteLLM for processing
                        # Determine if tools should be sent based on config/logic (e.g., allow disabling tools)
                        # For now, always send tool definitions if tools are registered.
                        # We will set tool_choice="none" later if needed based on config? No, let LLM decide.
                        send_tools = tool_definitions if self.tool_manager.get_tools() else None

                        # Prepare additional parameters, ensuring api_base and api_key are handled
                        # Ensure additional_params is a dict before copying
                        additional_litellm_params = {}
                        if isinstance(self.config.additional_params, dict):
                            additional_litellm_params = self.config.additional_params.copy()
                        else:
                            logger.warning(f"Config additional_params is not a dict, using empty. Type: {type(self.config.additional_params)}")

                        # additional_litellm_params = self.config.additional_params.copy()
                        if api_base:
                             additional_litellm_params["api_base"] = api_base
                        # Add api_key only if it's not None (Ollama case)
                        if api_key:
                             additional_litellm_params["api_key"] = api_key


                        response = await litellm.acompletion(
                            model=model_string,
                            messages=messages,
                            temperature=self.config.temperature,
                            max_tokens=self.config.max_tokens,
                            stream=True,
                            tools=send_tools, # Send tool definitions
                            tool_choice="auto", # Let the LLM decide if it needs tools
                            # Pass api_base and api_key within additional_params if needed
                            # **self.config.additional_params, # Original
                            **additional_litellm_params # Use potentially updated params
                        )
                        verbosity_controller.show_verbose(f"[{self.agent_name}] LiteLLM call initiated (streaming).")

                        response_text = ""
                        tool_calls = []
                        current_tool_calls: Dict[int, Dict[str, Any]] = {}  # Track partial tool calls by index

                        # Keep track of the first assistant message event to potentially update it later
                        first_chunk_received = False

                        async for chunk in response:
                            # print(f"CHUNK: {chunk}") # DEBUG
                            if not first_chunk_received:
                                # Add initial partial assistant message on first chunk
                                await self.session_manager.add_partial_assistant_message(
                                    session_id=self.session_id,
                                    content="",  # Start with empty content
                                    invocation_id=invocation_id,
                                )
                                first_chunk_received = True

                            # Process content delta
                            content_delta = chunk.choices[0].delta.content
                            if content_delta:
                                response_text += content_delta
                                # Stream intermediate text delta
                                if self.streaming_callback is not None:
                                    await self.streaming_callback(content_delta, is_final=False, metadata={"type": "content"})

                            # Process tool call deltas
                            tool_call_deltas = chunk.choices[0].delta.tool_calls
                            if tool_call_deltas:
                                for tool_call_chunk in tool_call_deltas:
                                    index = tool_call_chunk.index
                                    tool_id = tool_call_chunk.id
                                    function_name = tool_call_chunk.function.name
                                    function_args_delta = tool_call_chunk.function.arguments

                                    if index not in current_tool_calls:
                                        current_tool_calls[index] = {"id": tool_id, "function": {"name": function_name, "arguments": ""}}
                                    elif tool_id and current_tool_calls[index]["id"] is None: # Sometimes ID comes in a later chunk
                                        current_tool_calls[index]["id"] = tool_id

                                    if function_args_delta:
                                        current_tool_calls[index]["function"]["arguments"] += function_args_delta

                                    # Stream intermediate tool call delta (raw arguments)
                                    if self.streaming_callback is not None:
                                        # We might want to signal the start/progress/end of tool calls
                                         await self.streaming_callback(
                                            {"index": index, "id": tool_id, "function": {"name": function_name, "arguments_delta": function_args_delta}},
                                            is_final=False,
                                            metadata={"type": "tool_delta"}
                                        )


                            # --- End of chunk processing loop ---

                        # --- Finalize after loop ---
                        # Convert accumulated tool call dictionaries to FunctionCall objects
                        for index in sorted(current_tool_calls.keys()):
                            tool_data = current_tool_calls[index]
                            try:
                                # Attempt to parse the arguments JSON string
                                parsed_args = json.loads(tool_data["function"]["arguments"])
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool call arguments for {tool_data['function']['name']}: {tool_data['function']['arguments']}")
                                # Handle error: maybe skip this tool call or add an error message?
                                # For now, we'll add it with the raw string arguments
                                parsed_args = {"error": "Failed to parse arguments", "raw_arguments": tool_data["function"]["arguments"]}

                            tool_calls.append(
                                genai_types.FunctionCall(
                                    name=tool_data["function"]["name"],
                                    args=parsed_args,
                                    # id=tool_data.get("id") # ADK v0.3.0 FunctionCall might not have id
                                )
                            )
                            # Also include ID if available and needed (check FunctionCall definition)
                            # The ID is primarily used to match results back to calls. We'll store it separately.
                            self.tool_call_ids[tool_data["function"]["name"]] = tool_data.get("id") # Store ID mapping


                        # Add the final assistant message with full text and parsed tool calls
                        await self.session_manager.add_assistant_message(
                            session_id=self.session_id,
                            content=response_text if response_text else None, # Add None if empty
                            tool_calls=tool_calls if tool_calls else None, # Add None if empty
                            partial=False, # Mark as final
                            invocation_id=invocation_id,
                        )
                        # --- End Finalize ---


                        verbosity_controller.show_verbose(f"[{self.agent_name}] LiteLLM stream finished.")
                        logger.info(f"[{self.agent_name}] Assistant response received: {response_text}")
                        if tool_calls:
                            logger.info(f"[{self.agent_name}] Assistant requested tool calls: {[tc.name for tc in tool_calls]}")

                    # --- Correctly indented exception handlers for litellm.acompletion ---
                    except litellm.exceptions.APIConnectionError as e:
                        logger.error(f"[{self.agent_name}] API Connection Error: {e}", exc_info=True)
                        await self.session_manager.add_error_event(session_id=self.session_id, error_message=f"LLM API connection failed: {str(e)}", invocation_id=invocation_id)
                        return f"An error occurred connecting to the language model: {str(e)}" # Return error
                    except litellm.exceptions.APIError as e: # Catch other LiteLLM API errors
                        logger.error(f"[{self.agent_name}] LiteLLM API Error: {e}", exc_info=True)
                        await self.session_manager.add_error_event(session_id=self.session_id, error_message=f"LLM API call failed: {str(e)}", invocation_id=invocation_id)
                        return f"An API error occurred with the language model: {str(e)}" # Return error
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"[{self.agent_name}] Unexpected error during LiteLLM call/processing: {e}\n{error_details}", exc_info=False) # Log details manually
                        await self.session_manager.add_error_event(session_id=self.session_id, error_message=f"Unexpected error processing LLM response: {str(e)}", invocation_id=invocation_id)
                        return f"An unexpected error occurred while processing the language model response: {str(e)}" # Return error
                    # --- End of corrected exception handlers ---


                    # --- Execute Tool Calls ---
                    if tool_calls:
                        # Check limit BEFORE executing
                        if tool_call_count >= self.config.max_tool_calls:
                            warning_msg = f"Maximum tool call limit ({self.config.max_tool_calls}) reached. Skipping further tool execution."
                            logger.warning(warning_msg)
                            await self.session_manager.add_error_event(
                                session_id=self.session_id,
                                error_message=warning_msg,
                                author="agent",
                                invocation_id=invocation_id
                            )
                            tool_calls_pending = False # Stop loop
                            break # Exit while loop

                        # If limit not reached, proceed with execution
                        logger.info(f"[{self.agent_name}] Executing {len(tool_calls)} tool calls...")
                        tool_calls_pending = True # Signal that we need another LLM call after results
                        tool_call_count += 1 # Increment tool call counter

                        tool_results_for_next_turn = [] # Prepare results for the *next* LLM call

                        # Check tool_calls again *after* potential break from max_calls check
                        if tool_calls:
                            for tool_call in tool_calls:
                                tool_name = tool_call.name
                                tool_args = tool_call.args # Already parsed dict
                                tool_call_id = self.tool_call_ids.get(tool_name) # Retrieve the ID

                                logger.debug(f"Executing tool: {tool_name} with args: {tool_args}")

                                tool_output = None
                                tool_error = None
                                try:
                                    # Find and execute the tool (ensure await happens)
                                    result = await self.tool_manager.execute_tool(tool_name, **tool_args)
                                    logger.debug(f"Tool {tool_name} executed. Result keys: {result.keys()}")

                                    # Check for error key in result first
                                    if "error" in result and result["error"]:
                                        tool_error = str(result['error'])
                                        logger.error(f"Tool {tool_name} execution failed: {tool_error}")
                                        await self.session_manager.add_error_event(
                                            session_id=self.session_id,
                                            error_message=tool_error,
                                            author="tool", # Indicate error came from the tool
                                            invocation_id=invocation_id,
                                            # Consider adding tool_name/tool_call_id to metadata if possible
                                        )
                                    elif "output" in result:
                                        tool_output = result["output"]
                                        logger.info(f"Tool {tool_name} result: {str(tool_output)[:200]}...") # Log truncated output
                                        # Add tool result to ADK history
                                        await self.session_manager.add_tool_result(
                                            session_id=self.session_id,
                                            tool_call_id=tool_call_id, # Pass the ID
                                            tool_name=tool_name,
                                            content=tool_output, # Pass the output content
                                            invocation_id=invocation_id,
                                        )
                                    else:
                                        # Handle cases where tool produces neither output nor error
                                        tool_error = f"Tool {tool_name} produced no output or error."
                                        logger.warning(tool_error)
                                        await self.session_manager.add_error_event(
                                            session_id=self.session_id,
                                            error_message=tool_error,
                                            author="tool",
                                            invocation_id=invocation_id,
                                        )

                                except Exception as e:
                                    tool_error = f"Agent failed to execute tool {tool_name}: {str(e)}"
                                    logger.error(f"[{self.agent_name}] Error executing tool {tool_name}: {e}", exc_info=True)
                                    # Add error event to ADK history
                                    await self.session_manager.add_error_event(
                                        session_id=self.session_id,
                                        error_message=tool_error,
                                        author="agent", # Error occurred in agent logic calling tool
                                        invocation_id=invocation_id,
                                    )

                                # Add result/error to the list for the next LLM call
                                if tool_error:
                                    tool_results_for_next_turn.append({
                                        "tool_call_id": tool_call_id,
                                        "role": "tool",
                                        "name": tool_name,
                                        "content": json.dumps({"error": tool_error}) # Standardize error reporting
                                    })
                                else:
                                    tool_results_for_next_turn.append({
                                        "tool_call_id": tool_call_id,
                                        "role": "tool",
                                        "name": tool_name,
                                        "content": json.dumps(tool_output) if not isinstance(tool_output, str) else tool_output # Ensure content is string
                                    })
                                # --- End of tool execution loop ---

                        else: # No tool calls requested in the last response
                            tool_calls_pending = False # Stop the loop

                    else: # No tool calls requested in the last response
                        tool_calls_pending = False # Stop the loop

                    # --- Loop condition check ---
                    # The loop continues if tool_calls_pending is True AND tool_call_count < max_tool_calls

                # --- End of while tool_calls_pending loop ---

                # After the loop, check if max calls were reached
                if tool_call_count >= self.config.max_tool_calls:
                    warning_msg = f"Maximum tool call limit ({self.config.max_tool_calls}) reached. Returning last response."
                    logger.warning(warning_msg)
                    # Optionally add an error event to the session
                    await self.session_manager.add_error_event(
                        session_id=self.session_id,
                        error_message=warning_msg,
                        author="agent",
                        invocation_id=invocation_id
                    )
                    # Return the text generated *before* hitting the limit (which is already in response_text)
                    # The final assistant message was already added.

                # If loop ended naturally (no more tool calls requested)
                # The final assistant message (text and/or tool calls) was already added.
                # We just need to return the final response text.
                indicator.update(f"Agent finished: {response_text[:50]}...")
                return response_text # Return the final text response accumulated

            # End of 'with thinking_indicator(...)'
        except Exception as e:
            # Catch-all for errors outside the main LLM/tool loop (e.g., initial message conversion)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"[{self.agent_name}] Unexpected error in run_turn: {e}\n{error_details}", exc_info=False) # Use logger
            # Try to add an error event if session manager is available
            if hasattr(self, 'session_manager') and self.session_id:
                try:
                    await self.session_manager.add_error_event(session_id=self.session_id, error_message=f"Agent runtime error: {str(e)}", invocation_id=invocation_id if 'invocation_id' in locals() else None)
                except Exception as add_err:
                    logger.error(f"Failed to add error event to session after runtime error: {add_err}")
            return f"An unexpected error occurred in the agent: {str(e)}" # Return error message

    def _get_tool_definitions(self) -> Optional[List[Dict[str, Any]]]:
        """Returns the tool definitions in the format expected by LiteLLM."""
        # Assuming ToolManager provides a method to get schema in LiteLLM format
        # If not, this method needs to manually construct the schema.
        try:
            # Use the ToolManager instance created in __init__
            schema = self.tool_manager.get_tool_schema()
            if schema:
                # LiteLLM expects a list of dictionaries, each with 'type' and 'function' keys
                return [{"type": "function", "function": tool_def} for tool_def in schema]
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get tool definitions from ToolManager: {e}")
            return None # Return None if schema generation fails
