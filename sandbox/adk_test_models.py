#!/usr/bin/env python
"""
Command-line utility for testing ADK model implementations.

This script allows testing different model providers and configurations
directly from the command line, without requiring the full agent.

Examples:
    # Use a specific provider
    uv run python sandbox/adk_test_models.py --provider ai_studio

    # Test with Google AI Studio models
    uv run python sandbox/adk_test_models.py --provider ai_studio --model gemini-1.5-flash

    # Test with OpenAI models
    uv run python sandbox/adk_test_models.py --provider openai --model gpt-3.5-turbo

    # Test with Ollama models
    uv run python sandbox/adk_test_models.py --provider ollama --model llama3

    # Test fallback behavior
    uv run python sandbox/adk_test_models.py --provider invalid --fallback-provider openai

    # List available providers
    uv run python sandbox/adk_test_models.py --list-providers

    # Use a specific prompt
    uv run python sandbox/adk_test_models.py --prompt "Explain quantum computing in simple terms"
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

# Add the project root to the Python path to allow importing from code_agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Simulate functions from the original models module if needed, or define statically
def get_model_providers() -> list[str]:
    # Based on the original code_agent/adk/models.py
    return ["ai_studio", "openai", "anthropic", "groq", "ollama"]


def get_default_models_by_provider() -> Dict[str, str]:
    # Based on the original code_agent/adk/models.py
    return {
        "ai_studio": "gemini-1.5-flash",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-haiku",
        "groq": "llama3-70b-8192",
        "ollama": "llama3.2:latest",
    }


async def test_model(
    provider: str,
    model_name: Optional[str] = None,
    prompt: Optional[str] = None,
    temperature: Optional[float] = 0.7,
    max_tokens: Optional[int] = None,
    verbose: bool = False,
) -> None:
    """
    Test a model with the given configuration.

    Args:
        provider: The model provider (ai_studio, openai, etc.)
        model_name: Specific model to use (defaults to provider's default)
        prompt: Custom prompt (defaults to a standard test prompt)
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        verbose: Whether to display detailed information
    """
    # Get default model for provider if not specified
    if not model_name:
        default_models = get_default_models_by_provider()
        model_name = default_models.get(provider)
        if not model_name:
            print(f"ERROR: Could not determine default model for provider '{provider}'.")
            sys.exit(1)

    # Set default prompt if not provided
    if not prompt:
        prompts_by_provider = {
            "ai_studio": "Write a haiku about Python programming.",
            "openai": "What is the capital of France?",
            "anthropic": "Tell me about machine learning in one sentence.",
            "groq": "Explain quantum computing briefly.",
            "ollama": "List three programming languages.",
        }
        prompt = prompts_by_provider.get(provider, "Hello! Please introduce yourself briefly.")

    # Construct the model identifier string for LlmAgent
    # For ai_studio and Vertex endpoints, it's usually just the model name/resource string
    # For LiteLLM-based providers, we might need to adjust this if LlmAgent doesn't use LiteLlm directly
    # Assuming LlmAgent handles 'gemini-*' for ai_studio/Vertex and maybe others via registry
    adk_model_identifier = model_name
    if provider == "ai_studio":  # ADK registry handles gemini-* directly
        adk_model_identifier = model_name
    # Add logic here if other providers need specific formatting for LlmAgent
    # or if we need to use the LiteLlm wrapper class explicitly
    elif provider in ["openai", "anthropic", "groq", "ollama"]:
        print(f"Warning: Provider '{provider}' might require explicit LiteLlm wrapper.")
        # For now, we'll try passing the plain model name, but this might fail
        # or need adjustment based on how LlmAgent/registry works with non-Google models.
        adk_model_identifier = model_name

    print(f"\n{'=' * 80}")
    print(f"Testing with LlmAgent: {adk_model_identifier} (Provider hint: {provider})")
    print(f"Prompt: {prompt}")
    print(f"{'=' * 80}\n")

    try:
        # --- Use LlmAgent and Runner ---
        # 1. Configure Generation Settings
        gen_config_params = {}
        if temperature is not None:
            gen_config_params["temperature"] = temperature
        if max_tokens is not None:
            gen_config_params["max_output_tokens"] = max_tokens
        # Use types.GenerationConfig from google.genai
        generate_config = types.GenerateContentConfig(**gen_config_params) if gen_config_params else None

        # 2. Create the LlmAgent
        agent = LlmAgent(
            model=adk_model_identifier,  # Pass the model string
            name=f"{provider}_test_agent",
            instruction="You are a helpful assistant responding to the user's prompt.",  # Simple instruction
            generate_content_config=generate_config,
        )

        # 3. Set up Runner and Session
        session_service = InMemorySessionService()
        runner = Runner(agent=agent, app_name="adk_test_app", session_service=session_service)
        user_id = "test_user"
        session_id = f"test_session_{provider}_{model_name}"
        session_service.create_session(app_name="adk_test_app", user_id=user_id, session_id=session_id)

        # 4. Prepare the input message
        # LlmAgent expects types.Content
        input_content = types.Content(role="user", parts=[types.Part(text=prompt)])

        # 5. Run the agent asynchronously
        start_time = asyncio.get_event_loop().time()
        final_response_text = "Error: No final response captured."
        final_event = None
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=input_content):
            if verbose:
                print(f"  ...Event: {event.event_type} by {event.author}")  # Basic event logging
            if event.is_final_response():
                final_event = event
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                elif event.error_message:
                    final_response_text = f"Error in final response: {event.error_message}"

        end_time = asyncio.get_event_loop().time()

        # Display results
        print("RESPONSE:")
        print(f"{'-' * 80}")
        print(final_response_text)
        print(f"{'-' * 80}\n")

        # Display metadata if verbose
        if verbose and final_event:
            print("METADATA (from final event):")
            print(f"{'-' * 80}")
            # Extract relevant info from the final event if available
            # This is less direct than the previous metadata dict
            print(f"  Event Type: {final_event.event_type}")
            print(f"  Author: {final_event.author}")
            # Add more details if needed, inspecting final_event attributes
            print(f"{'-' * 80}")

        # Always show provider and timing
        print(f"\nProvider Hint: {provider}")
        print(f"Model Used (Identifier): {adk_model_identifier}")
        print(f"Time: {end_time - start_time:.2f} seconds")

    except Exception as e:
        print(f"ERROR: {e}")

        # Provide guidance on possible causes
        if "API key" in str(e) or "authentication" in str(e).lower():
            print("\nPossible API key/authentication issue. Check environment variables or ADC:")
            print("  - For AI Studio: GOOGLE_API_KEY or AI_STUDIO_API_KEY")
            print("  - For OpenAI: OPENAI_API_KEY")
            print("  - For Anthropic: ANTHROPIC_API_KEY")
            print("  - For Groq: GROQ_API_KEY")
            print("  - For Ollama: Make sure the Ollama service is running on http://localhost:11434")

        # Exit with error code
        sys.exit(1)


def list_providers() -> None:
    """Display the list of available model providers and their default models."""
    providers = get_model_providers()
    default_models = get_default_models_by_provider()

    print("\nAvailable Model Providers:")
    print(f"{'-' * 80}")
    for provider in sorted(providers):
        print(f"- {provider:<12} (default model: {default_models.get(provider, 'unknown')})")
    print(f"{'-' * 80}\n")

    print("Environment Variables for API Keys:")
    print(f"{'-' * 80}")
    print("- AI Studio:   GOOGLE_API_KEY or AI_STUDIO_API_KEY")
    print("- OpenAI:      OPENAI_API_KEY")
    print("- Anthropic:   ANTHROPIC_API_KEY")
    print("- Groq:        GROQ_API_KEY")
    print("- Ollama:      No API key needed (runs locally)")
    print(f"{'-' * 80}\n")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test ADK LlmAgent with different models.")

    # Main options
    # Provider is now mainly a hint for determining the default model if --model is not given
    parser.add_argument("--provider", default="ai_studio", choices=get_model_providers(), help="Provider hint for default model lookup.")
    parser.add_argument(
        "--model", dest="model_name", help="Specific model identifier string for LlmAgent (e.g., gemini-1.5-flash, openai/gpt-4o). Overrides provider default."
    )
    parser.add_argument("--prompt", help="Custom prompt (defaults to a standard test prompt)")

    # Model parameters
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, help="Maximum tokens to generate")

    # Utility options
    parser.add_argument("--list-providers", action="store_true", help="List available model providers and exit")
    parser.add_argument("--verbose", action="store_true", help="Display detailed information including event logs")

    return parser.parse_args()


async def main() -> None:
    """Main entry point for the script."""
    args = parse_args()

    # Handle list-providers option
    if args.list_providers:
        list_providers()
        return

    # Test the model with the specified configuration
    await test_model(
        provider=args.provider,
        model_name=args.model_name,
        prompt=args.prompt,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
