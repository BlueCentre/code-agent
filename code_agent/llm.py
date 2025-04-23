from typing import Dict, List, Optional

# ruff: noqa: E501
import litellm
from rich import print

from code_agent.config import get_api_key, get_config
from code_agent.tools.error_utils import format_api_error

# Configure LiteLLM settings if needed (e.g., logging)
# litellm.set_verbose = True


def get_llm_response(
    prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    # TODO: Add support for tools/function calling later
) -> Optional[str]:
    """Gets a response from the specified LLM provider and model."""
    config = get_config()

    target_provider = provider or config.default_provider
    target_model = model or config.default_model
    api_key = get_api_key(target_provider)

    if target_provider == "openai" and not api_key:
        print(f"[bold red]Error:[/bold red] OpenAI API key not found. Set OPENAI_API_KEY environment variable or add it to {config.DEFAULT_CONFIG_PATH}.")
        return None
    # Add similar checks for other providers requiring keys
    if target_provider == "groq" and not api_key:
        print(f"[bold red]Error:[/bold red] Groq API key not found. Set GROQ_API_KEY environment variable or add it to {config.DEFAULT_CONFIG_PATH}.")
        return None

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    try:
        print(f"[grey50]Calling LiteLLM (Provider: {target_provider}, Model: {target_model})...[/grey50]")
        response = litellm.completion(
            model=f"{target_provider}/{target_model}",  # LiteLLM uses provider/model format
            messages=messages,
            api_key=api_key,
            # Add other parameters like temperature, max_tokens if needed
        )

        # Extract the response content
        # Accessing choices[0].message.content based on LiteLLM response structure
        content = response.choices[0].message.content
        return content.strip() if content else None

    except Exception as e:
        # Enhanced error handling with detailed formatting
        formatted_error = format_api_error(e, target_provider, target_model)
        print("[bold red]Error calling LiteLLM:[/bold red]")
        print(f"[red]{formatted_error}[/red]")
        return None


# Example usage (can be removed later)
if __name__ == "__main__":
    # Ensure you have OPENAI_API_KEY or GROQ_API_KEY set in your env or config
    test_prompt = "Explain the concept of AI agents in one sentence."
    print(f"Sending prompt: {test_prompt}")
    response_content = get_llm_response(test_prompt)  # Uses defaults from config/env

    if response_content:
        print("\n[bold green]LLM Response:[/bold green]")
        print(response_content)
    else:
        print("\n[bold red]Failed to get LLM response.[/bold red]")
