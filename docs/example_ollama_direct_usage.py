#!/usr/bin/env python3
"""
Example script demonstrating direct usage of the OllamaDirectProvider.

This script shows how to use Ollama directly without Google ADK, which avoids
compatibility issues that may occur with the experimental integration.
"""

from code_agent.agents.ollama import OllamaDirectProvider


def main():
    # Initialize the Ollama provider
    # Replace model with any model you have pulled in Ollama
    provider = OllamaDirectProvider(
        model="llama3.2:latest",  # Any model you have pulled in Ollama
        base_url="http://localhost:11434",  # Your Ollama server URL
    )

    # List available models
    print("Available models:")
    models = provider.list_models()
    for model in models:
        print(f"- {model.get('name')}")

    print("\n----------------------------------------------------\n")

    # Simple text generation
    prompt = "What is your name?"
    print(f"Generating response for: '{prompt}'")
    response = provider.generate(prompt)
    print(f"\nResponse:\n{response}\n")

    print("\n----------------------------------------------------\n")

    # Chat completion example
    messages = [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": "What can you help me with?"}]

    print("Chat completion example:")
    print("Messages:", messages)
    response = provider.chat(messages)
    print(f"\nResponse:\n{response}\n")


if __name__ == "__main__":
    main()
