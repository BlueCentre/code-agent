"""
Integration tests for ADK model implementations.

These tests make actual API calls if credentials are available.
Skip them if no credentials are configured.
"""

import os
from typing import Dict

import pytest

from code_agent.adk.models import (
    EnhancedGemini,
    LiteLlm,
    OllamaLlm,
    create_model,
    get_model_providers,
)


def has_api_key(provider: str) -> bool:
    """Check if we have an API key for the given provider."""
    if provider == "ai_studio":
        return bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_STUDIO_API_KEY"))
    elif provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    elif provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif provider == "groq":
        return bool(os.environ.get("GROQ_API_KEY"))
    elif provider == "ollama":
        # Check if Ollama is running on localhost
        import socket

        try:
            socket.create_connection(("localhost", 11434), timeout=1)
            return True
        except OSError:
            return False
    return False


def get_test_prompts() -> Dict[str, str]:
    """Get test prompts for different providers."""
    return {
        "ai_studio": "Write a haiku about Python programming.",
        "openai": "What is the capital of France?",
        "anthropic": "Tell me about machine learning in one sentence.",
        "groq": "Explain quantum computing briefly.",
        "ollama": "List three programming languages.",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", get_model_providers())
async def test_model_integration(provider: str):
    """Test model integration with real API calls if credentials exist."""
    if not has_api_key(provider):
        pytest.skip(f"Skipping test for {provider} - no API key or service available")

    # Create a model for the provider with appropriate model name
    model_name = None
    if provider == "ollama":
        model_name = "llama3.2:latest"

    model = create_model(provider=provider, model_name=model_name)

    # Get an appropriate test prompt
    prompts = get_test_prompts()
    prompt = prompts.get(provider, "Hello, world!")

    # Generate content
    content, metadata = await model.generate_content(prompt)

    # Basic verification
    assert content and isinstance(content, str)
    assert metadata and isinstance(metadata, dict)
    assert "provider" in metadata
    assert metadata["provider"] == provider

    # Log response for manual inspection
    print(f"\n--- {provider.upper()} RESPONSE ---")
    print(f"Prompt: {prompt}")
    print(f"Response: {content[:100]}..." if len(content) > 100 else f"Response: {content}")
    print(f"Metadata: {metadata}")


@pytest.mark.asyncio
async def test_fallback_mechanism():
    """Test the fallback mechanism with a non-existent provider."""
    # Find which providers we have keys for
    available_providers = [p for p in get_model_providers() if has_api_key(p)]

    # Skip test if we don't have at least one provider available for fallback
    if not available_providers:
        pytest.skip("Skipping fallback test - no API keys available for any provider")

    # Get first available provider for fallback
    fallback_provider = available_providers[0]

    # Use proper model name based on the provider
    fallback_models = {
        "ai_studio": "gemini-1.5-flash",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-haiku",
        "groq": "llama3-70b-8192",
        "ollama": "llama3.2:latest",
    }
    fallback_model = fallback_models.get(fallback_provider, "gpt-3.5-turbo")

    # Create model with invalid primary provider and valid fallback
    model = create_model(provider="invalid_provider", model_name="nonexistent_model", fallback_provider=fallback_provider, fallback_model=fallback_model)

    # Generate content - should use fallback
    content, metadata = await model.generate_content("Test fallback mechanism")

    # Verify response came from fallback provider
    assert content and isinstance(content, str)
    assert metadata and isinstance(metadata, dict)
    assert "provider" in metadata
    assert metadata["provider"] == fallback_provider

    # Log response for manual inspection
    print("\n--- FALLBACK MECHANISM TEST ---")
    print("Attempted provider: invalid_provider")
    print(f"Fallback provider: {fallback_provider}")
    print(f"Response: {content[:100]}..." if len(content) > 100 else f"Response: {content}")
    print(f"Metadata: {metadata}")


@pytest.mark.asyncio
async def test_gemini_with_message_history():
    """Test Gemini model with a conversation history."""
    if not has_api_key("ai_studio"):
        pytest.skip("Skipping test for Gemini - no API key available")

    # Create a model
    model = create_model(provider="ai_studio", model_name="gemini-1.5-flash")

    # Create a conversation history
    messages = [
        {"role": "user", "content": "My name is Alice."},
        {"role": "assistant", "content": "Hello Alice, nice to meet you!"},
        {"role": "user", "content": "What's my name?"},
    ]

    # Generate content
    content, metadata = await model.generate_content(messages)

    # Verify response mentions "Alice"
    assert content and isinstance(content, str)
    assert "Alice" in content

    # Log response for manual inspection
    print("\n--- GEMINI CONVERSATION TEST ---")
    print(f"Response: {content}")


@pytest.mark.asyncio
async def test_ollama_local():
    """Test Ollama integration with local instance if available."""
    if not has_api_key("ollama"):
        pytest.skip("Skipping test for Ollama - no local Ollama instance available")

    # Create Ollama model directly
    model = OllamaLlm(model_name="llama3.2:latest")

    # Simple prompt
    prompt = "Count from 1 to 5."

    # Generate content
    content, metadata = await model.generate_content(prompt)

    # Basic verification
    assert content and isinstance(content, str)
    assert any(str(i) for i in range(1, 6) if str(i) in content)

    # Log response for manual inspection
    print("\n--- OLLAMA LOCAL TEST ---")
    print(f"Response: {content}")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "anthropic", "groq"])
async def test_litellm_wrapper(provider: str):
    """Test LiteLLM wrapper for specific providers."""
    if not has_api_key(provider):
        pytest.skip(f"Skipping test for {provider} - no API key available")

    # Get default model for provider
    model_map = {
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-haiku",
        "groq": "llama3-70b-8192",
    }
    model_name = model_map.get(provider)

    # Create model directly using LiteLlm
    from code_agent.config import get_api_key

    api_key = get_api_key(provider)
    model = LiteLlm(provider=provider, model_name=model_name, api_key=api_key)

    # Simple test prompt
    prompt = f"Say hello in the style of a {provider} model!"

    # Generate content
    content, metadata = await model.generate_content(prompt)

    # Basic verification
    assert content and isinstance(content, str)

    # Log response for manual inspection
    print(f"\n--- {provider.upper()} LITELLM WRAPPER TEST ---")
    print(f"Response: {content}")


@pytest.mark.asyncio
async def test_enhanced_gemini():
    """Test the EnhancedGemini model with retry logic."""
    if not has_api_key("ai_studio"):
        pytest.skip("Skipping test for EnhancedGemini - no API key available")

    # Create model directly
    model = EnhancedGemini(model_name="gemini-1.5-flash", retry_count=2)

    # Simple test prompt
    prompt = "What is the meaning of life?"

    # Generate content
    content, metadata = await model.generate_content(prompt)

    # Basic verification
    assert content and isinstance(content, str)
    assert "provider" in metadata and metadata["provider"] == "ai_studio"
    assert "attempt" in metadata

    # Log response for manual inspection
    print("\n--- ENHANCED GEMINI TEST ---")
    print(f"Response: {content[:100]}..." if len(content) > 100 else f"Response: {content}")
    print(f"Metadata: {metadata}")


if __name__ == "__main__":
    # This allows running the tests directly, which can be helpful
    # for debugging and manual inspection of real API responses
    import asyncio
    from pprint import pprint

    print("Running manual integration tests for ADK models...")

    async def run_tests():
        for provider in get_model_providers():
            if has_api_key(provider):
                print(f"\nTesting {provider}...")
                try:
                    test_prompt = get_test_prompts()[provider]
                    model = create_model(provider=provider)
                    content, metadata = await model.generate_content(test_prompt)
                    print(f"SUCCESS: Got response from {provider}")
                    print(f"Prompt: {test_prompt}")
                    print(f"Response: {content[:100]}..." if len(content) > 100 else f"Response: {content}")
                    print("Metadata:")
                    pprint(metadata)
                except Exception as e:
                    print(f"ERROR: Failed to test {provider}: {e}")
            else:
                print(f"\nSkipping {provider} - no API key or service available")

        # Test fallback
        print("\nTesting fallback mechanism...")
        try:
            model = create_model(provider="invalid_provider", fallback_provider="ai_studio" if has_api_key("ai_studio") else "openai")
            content, metadata = await model.generate_content("Test fallback")
            print("SUCCESS: Fallback worked")
            print(f"Response: {content[:100]}..." if len(content) > 100 else f"Response: {content}")
            print("Metadata:")
            pprint(metadata)
        except Exception as e:
            print(f"ERROR: Failed to test fallback: {e}")

    # Run the async tests
    asyncio.run(run_tests())
