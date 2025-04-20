from typing import Dict, List, Optional

import litellm
from rich import print
from rich.status import Status

# Import tools as regular functions
from code_agent.config.config import SettingsConfig, get_config
from code_agent.tools.simple_tools import apply_edit, read_file, run_native_command


class CodeAgent:
    """Core class for the Code Agent, handling interaction loops and tool use."""

    def __init__(self):
        self.config: SettingsConfig = get_config()
        self.history: List[Dict[str, str]] = []

        # Prepare base instruction parts (can be refined later)
        self.base_instruction_parts = [
            "You are a helpful AI assistant specialized in coding tasks."
        ]
        if self.config.rules:
            self.base_instruction_parts.append("Follow these instructions:")
            self.base_instruction_parts.extend(
                [f"- {rule}" for rule in self.config.rules]
            )

        self.base_instruction_parts.append(
            "You have access to the following functions:"
        )
        self.base_instruction_parts.append(
            "- read_file(path): Reads the content of a specified file path."
        )
        self.base_instruction_parts.append(
            "- apply_edit(target_file, code_edit): Proposes changes to a file by providing the "
            "new content. It will show a diff and ask for user confirmation before applying."
        )
        self.base_instruction_parts.append(
            "- run_native_command(command): Executes a native terminal command after asking for "
            "user confirmation (unless auto-approved or on allowlist). Use cautiously."
        )
        self.base_instruction_parts.append(
            "Use these functions when necessary to fulfill the user's request."
        )

    def _get_model_string(self, provider: Optional[str], model: Optional[str]) -> str:
        """Determines the model string format expected by LiteLLM."""
        target_provider = provider or self.config.default_provider
        target_model_name = model or self.config.default_model

        if target_provider == "openai":
            return target_model_name
        elif target_provider == "ai_studio":
            # For Gemini API, use the name directly as LiteLLM will handle the formatting
            return target_model_name
        # Handle other providers
        return f"{target_provider}/{target_model_name}"

    def _get_api_base(self, provider: Optional[str]) -> Optional[str]:
        """Get the appropriate API base URL for the provider."""
        # All providers use their default API base URLs through LiteLLM
        return None

    def run_turn(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Runs a single turn using litellm with function calling."""

        model_string = self._get_model_string(provider, model)
        system_prompt = "\n".join(self.base_instruction_parts)

        print(
            f"[grey50]Initializing Agent (Model: {model_string}, Provider: {provider or self.config.default_provider})[/grey50]"
        )

        # Retrieve API key from config
        target_provider = provider or self.config.default_provider
        api_key = vars(self.config.api_keys).get(target_provider)

        if not api_key:
            print(
                f"[bold red]Error: No API key found for provider {target_provider}[/bold red]"
            )
            print("  - Please set the API key in one of the following ways:")
            print("  - Set environment variable"
                  f" ({target_provider.upper()}_API_KEY)")
            print("  - Add to config: ~/.config/code-agent/config.yaml")

            # Fallback to simple command handling for demo purposes
            print(
                "[yellow]Using fallback simple command handling for demonstration[/yellow]"
            )

            # Process a few basic commands without a real LLM
            if (
                "current directory" in prompt.lower()
                or "current working directory" in prompt.lower()
                or "pwd" in prompt.lower()
            ):
                result = run_native_command("pwd")
                self.history.append({"role": "user", "content": prompt})
                self.history.append(
                    {
                        "role": "assistant",
                        "content": f"The current working directory is:\n\n{result}",
                    }
                )
                return f"The current working directory is:\n\n{result}"

            elif "list files" in prompt.lower() or "ls" in prompt.lower():
                result = run_native_command("ls -la")
                self.history.append({"role": "user", "content": prompt})
                self.history.append(
                    {
                        "role": "assistant",
                        "content": f"Here are the files in the current directory:\n\n{result}",
                    }
                )
                return f"Here are the files in the current directory:\n\n{result}"

            elif "python files" in prompt.lower():
                result = run_native_command("find . -type f -name '*.py' | sort")
                self.history.append({"role": "user", "content": prompt})
                self.history.append(
                    {
                        "role": "assistant",
                        "content": f"Here are the Python files in the project:\n\n{result}",
                    }
                )
                return f"Here are the Python files in the project:\n\n{result}"

            else:
                return "Sorry, I need an API key to process general requests. For this demo, I can only handle basic commands like asking about the current directory or listing files."

        # Set up all the tool/function definitions for the LLM
        tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Reads the content of a specified file path",
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
                    "name": "apply_edit",
                    "description": "Proposes changes to a file and asks for confirmation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_file": {
                                "type": "string",
                                "description": "The path to the file to edit",
                            },
                            "code_edit": {
                                "type": "string",
                                "description": "The proposed content to apply to the file",
                            },
                        },
                        "required": ["target_file", "code_edit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_native_command",
                    "description": "Executes a native terminal command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The terminal command to execute",
                            }
                        },
                        "required": ["command"],
                    },
                },
            },
        ]

        # Build messages including history
        messages = []
        messages.append({"role": "system", "content": system_prompt})

        # Add previous conversation history
        for msg in self.history:
            messages.append(msg)

        # Add current user prompt
        messages.append({"role": "user", "content": prompt})

        # Prepare available tools for execution
        available_tools = {
            "read_file": read_file,
            "apply_edit": apply_edit,
            "run_native_command": run_native_command,
        }

        try:
            with Status(
                "[bold green]Agent is thinking...[/bold green]", spinner="dots"
            ) as _:
                assistant_response = None

                # Keep track if we're in a tool calling loop
                tool_calls_pending = True
                max_tool_calls = 5  # Safety limit for tool call loops
                tool_call_count = 0

                while tool_calls_pending and tool_call_count < max_tool_calls:
                    # Add api_base parameter if it's set
                    completion_params = {
                        "model": model_string,
                        "messages": messages,
                        "tools": tool_definitions,
                        "tool_choice": "auto",
                        "api_key": api_key,
                    }

                    # For ai_studio (Gemini API), specify the provider explicitly
                    if (provider or self.config.default_provider) == "ai_studio":
                        completion_params["custom_llm_provider"] = "gemini"

                    response = litellm.completion(**completion_params)

                    # Extract the message from the completion response
                    assistant_message = response.choices[0].message

                    # If there are tool calls, execute them
                    if (
                        hasattr(assistant_message, "tool_calls")
                        and assistant_message.tool_calls
                    ):
                        tool_call_count += 1

                        # Add the assistant's message to our conversation
                        messages.append(
                            {
                                "role": "assistant",
                                "content": assistant_message.content,
                                "tool_calls": assistant_message.tool_calls,
                            }
                        )

                        # Process each tool call
                        for tool_call in assistant_message.tool_calls:
                            function_name = tool_call.function.name
                            function_args = tool_call.function.arguments

                            # Convert string arguments to Python dict
                            import json

                            try:
                                args_dict = json.loads(function_args)
                            except json.JSONDecodeError:
                                print(
                                    f"[red]Error parsing function arguments: {function_args}[/red]"
                                )
                                continue

                            # Execute the tool
                            if function_name in available_tools:
                                try:
                                    function_result = available_tools[function_name](
                                        **args_dict
                                    )

                                    # Add the tool response to messages
                                    messages.append(
                                        {
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "name": function_name,
                                            "content": function_result,
                                        }
                                    )
                                except Exception as e:
                                    error_msg = (
                                        f"Error executing {function_name}: {e!s}"
                                    )
                                    print(f"[red]{error_msg}[/red]")
                                    messages.append(
                                        {
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "name": function_name,
                                            "content": error_msg,
                                        }
                                    )

                        # Continue the conversation to get a final response after tool use
                        continue
                    else:
                        # No tool calls, we have our final answer
                        assistant_response = assistant_message.content
                        tool_calls_pending = False

                # If we maxed out tool calls, explain the situation
                if tool_call_count >= max_tool_calls:
                    print(
                        f"[yellow]Warning: Maximum tool call limit reached ({max_tool_calls})[/yellow]"
                    )

            # Store the conversation turns in history
            self.history.append({"role": "user", "content": prompt})

            # If we got a response, store it and return it
            if assistant_response:
                self.history.append(
                    {"role": "assistant", "content": assistant_response}
                )
                return assistant_response
            else:
                return "No clear response was generated after tool execution. Try asking again or simplifying your request."

        except Exception as e:
            # Error Handling
            error_type = type(e).__name__
            error_message = str(e)
            print(f"[bold red]Error during agent execution ({error_type}):[/bold red]")

            if "api key" in error_message.lower():
                print(
                     "  - Check API key config (config file or ENV vars)."
                )
            elif "model not found" in error_message.lower():
                print(f"  - Model '{model_string}' might be unavailable/misspelled.")
            elif "rate limit" in error_message.lower():
                print("  - API rate limit likely exceeded.")
            else:
                print(f"  - {error_message}")

            return None


# Example usage (updated)
if __name__ == "__main__":
    print("Initializing Code Agent...")
    code_agent = CodeAgent()

    test_prompt = "What is the current directory?"
    print(f'\nRunning agent turn with prompt: "{test_prompt}"')
    agent_response = code_agent.run_turn(test_prompt)

    if agent_response:
        print("\n[bold green]Agent Response:[/bold green]")
        print(agent_response)

        # Example of a follow-up turn
        follow_up_prompt = "List all Python files in this directory."
        print(f'\nRunning follow-up turn: "{follow_up_prompt}"')
        follow_up_response = code_agent.run_turn(follow_up_prompt)
        if follow_up_response:
            print("\n[bold green]Follow-up Response:[/bold green]")
            print(follow_up_response)
        else:
            print("\n[bold red]Failed to get follow-up agent response.[/bold red]")

    else:
        print("\n[bold red]Failed to get initial agent response.[/bold red]")
