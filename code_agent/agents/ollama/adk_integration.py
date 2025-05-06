#!/usr/bin/env python3
"""
EXPERIMENTAL: Google ADK integration for Ollama.

This module contains experimental code for integrating Ollama with Google ADK.
It is not fully functional due to compatibility challenges with Google ADK.
See the end-to-end testing documentation for more details.

DO NOT USE IN PRODUCTION.
"""

import json
import logging
from typing import AsyncGenerator, List

import aiohttp
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import ConfigDict


class OllamaLlm(BaseLlm):
    """
    EXPERIMENTAL: Custom Ollama implementation for Google ADK.

    Note: This implementation is incomplete due to compatibility challenges
    with the current version of Google ADK (0.4.0).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        """Initialize Ollama LLM

        Args:
            model: The Ollama model name (e.g., llama3)
            base_url: Ollama API base URL
        """
        super().__init__(model=model)
        # Store Ollama-specific configuration in model_extras
        self.model_extras = {"base_url": base_url, "api_url": f"{base_url}/api/chat"}

    @classmethod
    def supported_models(cls) -> List[str]:
        """Returns a list of supported models in regex for LlmRegistry."""
        return ["ollama:.*"]

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        """Generates content from Ollama

        Args:
            llm_request: LlmRequest, the request to send to Ollama
            stream: Whether to stream the response

        Yields:
            LlmResponse: The response from Ollama
        """
        base_url = self.model_extras["base_url"]
        api_url = self.model_extras["api_url"]

        # Add debug logging
        logging.debug(f"OllamaLlm.generate_content_async called with model={self.model}, url={api_url}")

        # Convert ADK contents to Ollama messages format
        ollama_messages = []

        for content in llm_request.contents:
            message_text = ""
            # Extract text from content parts
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    message_text += part.text

            # Add debug logging for the message being sent
            logging.debug(f"Processing message from {content.role}: {message_text[:50]}{'...' if len(message_text) > 50 else ''}")

            # Add message to Ollama format
            ollama_messages.append({"role": content.role, "content": message_text})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": stream,
        }

        logging.debug(f"Sending request to Ollama API: {payload}")

        if not stream:
            # Non-streaming implementation
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logging.error(f"Ollama API error: {response.status} - {error_text}")
                            yield LlmResponse(
                                error_code="API_ERROR",
                                error_message=f"Error from Ollama API: {error_text}",
                            )
                            return

                        result = await response.json()
                        logging.debug(f"Received response from Ollama: {result}")

                        # Check if response has the expected format
                        if "message" not in result or "content" not in result["message"]:
                            logging.error(f"Unexpected response format from Ollama: {result}")
                            yield LlmResponse(error_code="FORMAT_ERROR", error_message="Unexpected response format from Ollama API")
                            return

                        response_text = result["message"]["content"]
                        logging.debug(f"Extracted response text: {response_text[:50]}{'...' if len(response_text) > 50 else ''}")

                        # Create Content object with the text response
                        content = types.Content(
                            parts=[types.Part(text=response_text)],
                            role="model",
                        )

                        yield LlmResponse(content=content)
            except Exception as e:
                logging.exception(f"Exception in OllamaLlm.generate_content_async: {e}")
                yield LlmResponse(
                    error_code="EXCEPTION",
                    error_message=f"Error: {e!s}",
                )
        else:
            # Basic streaming implementation
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=payload, headers={"Accept": "application/json"}) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logging.error(f"Ollama API streaming error: {response.status} - {error_text}")
                            yield LlmResponse(
                                error_code="API_ERROR",
                                error_message=f"Error from Ollama API: {error_text}",
                            )
                            return

                        buffer = ""
                        async for chunk in response.content:
                            if chunk:
                                chunk_text = chunk.decode("utf-8")
                                try:
                                    chunk_data = json.loads(chunk_text)
                                    if "message" in chunk_data and "content" in chunk_data["message"]:
                                        content_chunk = chunk_data["message"]["content"]
                                        buffer += content_chunk

                                        # Create Content object with the text response
                                        content = types.Content(
                                            parts=[types.Part(text=buffer)],
                                            role="model",
                                        )

                                        yield LlmResponse(content=content)
                                except json.JSONDecodeError:
                                    logging.warning(f"Failed to parse JSON from chunk: {chunk_text}")
                                    continue
            except Exception as e:
                logging.exception(f"Exception in streaming mode: {e}")
                yield LlmResponse(
                    error_code="STREAMING_EXCEPTION",
                    error_message=f"Streaming error: {e!s}",
                )
