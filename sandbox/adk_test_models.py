#!/usr/bin/env python
"""
Command-line utility for testing ADK model implementations.

This script allows testing different model providers and configurations
directly from the command line, without requiring the full agent.

Examples:
    # Test with Google AI Studio models
    python adk_test_models.py --provider ai_studio --model gemini-1.5-flash

    # Test with OpenAI models
    python adk_test_models.py --provider openai --model gpt-3.5-turbo

    # Test with Ollama models
    python adk_test_models.py --provider ollama --model llama3

    # Test fallback behavior
    python adk_test_models.py --provider invalid --fallback-provider openai

    # List available providers
    python adk_test_models.py --list-providers

    # Use a specific prompt
    python adk_test_models.py --prompt "Explain quantum computing in simple terms"
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

# Add the project root to the Python path to allow importing from code_agent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from code_agent.adk.models import create_model, get_default_models_by_provider, get_model_providers


async def test_model(
    provider: str,
    model_name: Optional[str] = None,
    prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
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
        fallback_provider: Provider to use if primary provider fails
        fallback_model: Model to use if primary model fails
        verbose: Whether to display detailed information
    """
    # Get default model for provider if not specified
    if not model_name:
        default_models = get_default_models_by_provider()
        model_name = default_models.get(provider)

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

    print(f"\n{'=' * 80}")
    print(f"Testing model: {provider}/{model_name}")
    print(f"Prompt: {prompt}")
    if fallback_provider:
        print(f"Fallback: {fallback_provider}/{fallback_model or 'default'}")
    print(f"{'=' * 80}\n")

    try:
        # Create model with the specified configuration
        model = create_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )

        # Generate content
        start_time = asyncio.get_event_loop().time()
        content, metadata = await model.generate_content(prompt)
        end_time = asyncio.get_event_loop().time()

        # Display results
        print("RESPONSE:")
        print(f"{'-' * 80}")
        print(content)
        print(f"{'-' * 80}\n")

        # Display metadata if verbose
        if verbose:
            print("METADATA:")
            print(f"{'-' * 80}")
            for key, value in metadata.items():
                print(f"{key}: {value}")
            print(f"{'-' * 80}")

        # Always show provider and timing
        print(f"\nProvider: {metadata.get('provider', provider)}")
        print(f"Model: {metadata.get('model', model_name)}")
        print(f"Time: {end_time - start_time:.2f} seconds")

    except Exception as e:
        print(f"ERROR: {e}")

        # Provide guidance on possible causes
        if "API key" in str(e) or "authentication" in str(e).lower():
            print("\nPossible API key issue. Check these environment variables:")
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
    for provider in providers:
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
    parser = argparse.ArgumentParser(description="Test ADK model implementations with different providers and parameters.")

    # Main options
    parser.add_argument("--provider", default="ai_studio", help="Model provider (ai_studio, openai, anthropic, groq, ollama)")
    parser.add_argument("--model", dest="model_name", help="Specific model to use (defaults to provider's default model)")
    parser.add_argument("--prompt", help="Custom prompt (defaults to a standard test prompt)")

    # Model parameters
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, help="Maximum tokens to generate")

    # Fallback options
    parser.add_argument("--fallback-provider", help="Provider to use if primary provider fails")
    parser.add_argument("--fallback-model", help="Model to use if primary model fails")

    # Utility options
    parser.add_argument("--list-providers", action="store_true", help="List available model providers and exit")
    parser.add_argument("--verbose", action="store_true", help="Display detailed information")

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
        fallback_provider=args.fallback_provider,
        fallback_model=args.fallback_model,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
