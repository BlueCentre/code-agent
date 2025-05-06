#!/usr/bin/env python3
"""
Ollama provider implementation for interacting with local Ollama models.

This module provides a direct interface to the Ollama API without Google ADK dependencies.
"""

import json
from typing import Any, Dict, List

import requests


class OllamaDirectProvider:
    """
    A direct approach to interact with Ollama via HTTP requests.

    This class provides a simple interface for interacting with Ollama's API
    for both the generate and chat endpoints.
    """

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """Initialize the Ollama direct provider.

        Args:
            model: The Ollama model name to use (e.g., llama3, codellama, mistral, etc.)
            base_url: Base URL for the Ollama API
        """
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        self.chat_url = f"{base_url}/api/chat"

    def generate(self, prompt: str, stream: bool = False) -> str:
        """Generate text from a prompt using the Ollama generate API.

        Args:
            prompt: The text prompt to send to Ollama
            stream: Whether to stream the response

        Returns:
            The generated text response
        """
        payload = {"model": self.model, "prompt": prompt, "stream": stream}

        response = requests.post(self.generate_url, json=payload)
        response.raise_for_status()

        # For non-streaming, we need to parse the JSON-per-line format
        complete_response = ""
        for line in response.text.split("\n"):
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                if "response" in data:
                    complete_response += data["response"]
            except json.JSONDecodeError:
                pass

        return complete_response

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Chat with Ollama using the chat API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            The assistant's response text
        """
        payload = {"model": self.model, "messages": messages}

        try:
            response = requests.post(self.chat_url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]
        except Exception as e:
            return f"Error in chat API: {e}"

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models in the local Ollama instance.

        Returns:
            List of model information dictionaries
        """
        list_url = f"{self.base_url}/api/tags"

        try:
            response = requests.get(list_url)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
