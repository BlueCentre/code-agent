from typing import Any, Dict, List, Optional

import requests


class OllamaProvider:
    """Provider for Ollama local models."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> List[Dict[str, Any]]:
        """Get a list of available models from Ollama."""
        response = requests.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return response.json()["models"]

    def get_completion(
        self, model: str, prompt: str, system: Optional[str] = None, temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Get a completion from an Ollama model."""
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        }

        if system:
            payload["system"] = system

        if tools:
            payload["tools"] = tools

        response = requests.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()
        return response.json()

    def chat_completion(
        self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7, tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Get a chat completion from an Ollama model."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools

        response = requests.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()
