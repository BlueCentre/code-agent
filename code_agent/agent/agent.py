from typing import Dict, List, Optional

from google.adk.agents import Agent
from google.adk.runtime import phidata_runtime
from rich import print
from rich.status import Status

# Consider importing specific exceptions if ADK/LiteLLM provide them
# from litellm import exceptions as litellm_exceptions
from code_agent.config import get_config
from code_agent.tools.file_tools import apply_edit, read_file
from code_agent.tools.native_tools import run_native_command

# Using phidata_runtime as specified in ADK examples
runtime = phidata_runtime.Runtime()

def run_agent_turn(
    prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    # TODO: Add tools later
) -> Optional[str]:
    """Runs a single turn using a basic ADK Agent."""
    config = get_config()

    # Determine model string for ADK (includes provider)
    # LiteLLM uses provider/model, ADK examples often use gemini-1.5-flash etc directly
    # We need to map our config to the ADK model/provider expectation.
    # For now, let's assume ADK can handle litellm format OR specific names if provider matches
    # This might need refinement based on how ADK interacts with LiteLLM integration.
    target_provider = provider or config.default_provider
    target_model_name = model or config.default_model

    # Heuristic: If provider is google/gemini, use model name directly.
    # Otherwise, try litellm format. ADK might need specific config for LiteLLM.
    if target_provider.startswith("google") or target_provider == "gemini":
         adk_model_string = target_model_name
    elif target_provider == "openai":
         # ADK might have specific OpenAI integration or rely on LiteLLM's handling
         adk_model_string = f"litellm/{target_provider}/{target_model_name}" # Guessing LiteLLM integration
    elif target_provider == "groq":
         # Guessing LiteLLM integration
         adk_model_string = f"litellm/{target_provider}/{target_model_name}" 
    else:
        # Default to LiteLLM format, ADK needs to support this
        adk_model_string = f"litellm/{target_provider}/{target_model_name}"

    # Construct the base instruction including configured rules
    rules = config.rules
    instruction_parts = [
        "You are a helpful AI assistant."
    ]
    if rules:
        instruction_parts.append("Follow these instructions:")
        instruction_parts.extend([f"- {rule}" for rule in rules])

    instruction_parts.append("You have access to the following tools:")
    instruction_parts.append("- 'read_file': Reads the content of a specified file path.")
    instruction_parts.append(
        "- 'apply_edit': Proposes changes to a file path by providing the FULL new content. "
        "It will show a diff and ask for user confirmation before applying."
    )
    instruction_parts.append(
        "- 'run_native_command': Executes a native terminal command after asking for user "
        "confirmation (unless auto-approved or on allowlist). Use cautiously."
    )
    instruction_parts.append("Use tools when necessary to fulfill the user's request.")

    base_instruction = "\n".join(instruction_parts)

    print(
        f"[grey50]Initializing ADK Agent (Model: {adk_model_string}) "
        f"with tools...[/grey50]"
    )
    # Optional: Print the full instruction being used
    # print(f"[grey50]Agent Instruction:\n{base_instruction}[/grey50]")

    try:
        # Define the agent, now including all tools
        agent = Agent(
            model=adk_model_string,
            instruction=base_instruction,
            tools=[read_file, apply_edit, run_native_command]
            # debug_mode=True
        )

        # ADK's agent.run() likely handles history internally if passed correctly.
        # The exact mechanism might depend on the agent type and runtime.
        # For a basic Agent, we might need to manage history externally and pass
        # the full context in the prompt or use a specific ADK feature if available.

        # Let's assume for now `agent.run` takes the latest prompt and we manage history
        # externally. We'll need a different approach if using ADK's memory features.

        # If ADK agent.run handles history implicitly (needs verification):
        # response = runtime.run_sync(agent.run(prompt, history=history)) # Hypothetical

        # --- Current History Approach ---
        # Pass the full message list as input.
        # WARNING: It's unclear if the base ADK Agent correctly handles this list
        #          as conversational history for maintaining context across turns.
        #          It might just process the last message or concatenate content.
        # TODO: Investigate using ADK's built-in Memory modules or specific
        #       Agent types designed for conversation for robust history management.
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        # ADK's agent.run() might take messages directly, or we might need
        # to use a different method/agent type for conversational context.
        # Let's try passing the full message list as input, assuming run can handle it.
        # The runtime should handle the tool execution loop automatically.

        # Add a status indicator
        with Status("[bold green]Agent is thinking...[/bold green]", spinner="dots") as _:
            response = runtime.run_sync(agent.run(messages))

        # Extract the final response content (might vary based on ADK version/structure)
        # Assuming the final output is the direct response string for a simple case.
        if isinstance(response, str):
            return response.strip()
        else:
            # Handle more complex response structures if needed (e.g., dicts, lists)
            print(
                f"[yellow]Warning:[/yellow] Unexpected agent response type: "
                f"{type(response)}"
            )
            print(response)
            # Attempt to find a meaningful string representation
            if hasattr(response, 'content'):
                return str(response.content).strip()
            return str(response).strip()

    except Exception as e:
        # Improve error reporting
        error_type = type(e).__name__
        error_message = str(e)
        print(f"[bold red]Error during agent execution ({error_type}):[/bold red]")

        # Attempt to provide more specific feedback based on common errors
        # (These checks might need adjustment based on actual exception types/messages)
        if "api key" in error_message.lower():
             print("  - Please check your API key configuration for the selected provider.")
             print(
                 "  - Ensure the key is set in ~/.code-agent/config.yaml or the "
                 "corresponding environment variable (e.g., OPENAI_API_KEY)."
             )
        elif "model not found" in error_message.lower():
             print(
                 f"  - The requested model '{adk_model_string}' might not be available "
                 f"for the provider or could be misspelled."
             )
             print("  - Check available models for your provider or try a different model.")
        elif "rate limit" in error_message.lower():
             print(
                 "  - You may have exceeded the API rate limit for your key. "
                 "Please wait and try again or check your provider's limits."
             )
        elif isinstance(e, ImportError) and "litellm" in error_message:
             print(
                 "  - LiteLLM integration might be missing required dependencies "
                 "for the specific provider."
             )
        else:
             # Generic error message
             print(f"  - {error_message}")

        # For debugging, you might want to print the full traceback
        # import traceback
        # print("[grey50]Full Traceback:[/grey50]")
        # traceback.print_exc()

        return None

# Example usage (can be removed later)
if __name__ == "__main__":
    # Ensure API keys are set
    test_prompt = "What is the main benefit of using the Agent Development Kit?"
    print(f"Running agent turn with prompt: {test_prompt}")
    agent_response = run_agent_turn(test_prompt)

    if agent_response:
        print("\n[bold green]Agent Response:[/bold green]")
        print(agent_response)
    else:
        print("\n[bold red]Failed to get agent response.[/bold red]")
