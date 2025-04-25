"""
ADK model implementations for Code Agent.

This module provides:
1. Google Gemini model integration via google.adk.models.Gemini
2. LiteLLM wrapper for other model providers (OpenAI, Anthropic, etc.)
3. Factory function to create the appropriate model based on configuration
4. Fallback behavior for handling model failures
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union

import litellm
from google.adk.models import BaseLlm
from pydantic import BaseModel, ConfigDict, Field

from code_agent.config import get_api_key, get_config
from code_agent.tools.error_utils import format_api_error


class LiteLlm(BaseLlm):
    """
    ADK model implementation that wraps LiteLLM to support multiple model providers.

    This allows using OpenAI, Anthropic, and other models through the ADK interface.
    """

    # Pydantic configuration to allow extra fields
    model_config = ConfigDict(extra="allow")

    # Add required BaseLlm field "model"
    model: str = Field(default="openai/gpt-3.5-turbo")

    # Additional Pydantic fields for LiteLlm
    provider: str = Field(default="openai")
    model_name: str = Field(default="gpt-3.5-turbo")
    api_key: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    timeout: Optional[int] = Field(default=None)
    retry_count: int = Field(default=2)
    litellm_model: str = Field(default="openai/gpt-3.5-turbo")

    def __init__(
        self,
        provider: str = "openai",
        model_name: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        retry_count: int = 2,
        **kwargs,
    ):
        """
        Initialize the LiteLLM wrapper for ADK.

        Args:
            provider: The LLM provider (openai, anthropic, etc.)
            model_name: The specific model to use
            api_key: API key for the provider
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        # Set the model field required by BaseLlm
        model = f"{provider}/{model_name}"
        litellm_model = model

        # Create super with all fields
        super().__init__(
            model=model,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            retry_count=retry_count,
            litellm_model=litellm_model,
            **kwargs,
        )

    async def generate_content_async(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using the LiteLLM model (ADK BaseLlm required method).

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            A tuple of (generated_text, metadata)
        """
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt

        # Merge instance parameters with kwargs
        all_kwargs = {
            "api_key": self.api_key,
            "temperature": self.temperature,
        }
        if self.max_tokens:
            all_kwargs["max_tokens"] = self.max_tokens
        if self.timeout:
            all_kwargs["timeout"] = self.timeout

        # Override with provided kwargs
        all_kwargs.update(kwargs)

        # Use a retry loop for resilience
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = await litellm.acompletion(model=self.litellm_model, messages=messages, **all_kwargs)

                # Extract content from response
                content = response.choices[0].message.content

                # Return content and metadata
                metadata = {
                    "provider": self.provider,
                    "model": self.model_name,
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": response.usage.model_dump() if hasattr(response, "usage") else {},
                }

                return content, metadata

            except Exception as e:
                last_error = e
                if attempt < self.retry_count:
                    # Log the error and retry
                    print(f"LiteLLM error (attempt {attempt + 1}/{self.retry_count + 1}): {e}")
                    continue
                else:
                    # Re-raise on final attempt
                    error_message = format_api_error(e, self.provider, self.model_name)
                    raise ValueError(f"LiteLLM error: {error_message}") from e

        # This should never be reached due to the raise in the loop,
        # but adding as a safety measure
        if last_error:
            error_message = format_api_error(last_error, self.provider, self.model_name)
            raise ValueError(f"LiteLLM error: {error_message}") from last_error
        else:
            raise ValueError("Unknown error in LiteLLM")

    async def generate_content(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using the LiteLLM model.

        This is a convenience method that calls generate_content_async.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            A tuple of (generated_text, metadata)
        """
        return await self.generate_content_async(prompt, **kwargs)


class OllamaLlm(LiteLlm):
    """
    Specialized LiteLLM wrapper for Ollama models.

    Adds Ollama-specific configuration and handling.
    """

    # Pydantic fields (inherit from LiteLlm and add Ollama-specific fields)
    base_url: str = Field(default="http://localhost:11434")

    def __init__(
        self,
        model_name: str = "llama3.2:latest",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        retry_count: int = 1,
        **kwargs,
    ):
        """
        Initialize the Ollama model wrapper.

        Args:
            model_name: Ollama model name (e.g., llama3, mistral, etc.)
            base_url: Ollama API base URL
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        # Call parent with ollama provider but don't pass litellm_model
        super().__init__(
            provider="ollama",
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout or 60,  # Higher default timeout for local models
            retry_count=retry_count,
            base_url=base_url,  # Pass this to the parent for Pydantic
            **kwargs,
        )

        # Override the model and litellm_model fields after calling super
        self.litellm_model = f"ollama/{model_name}"
        self.model = self.litellm_model

    async def generate_content_async(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using the Ollama model.

        Adds Ollama-specific parameters before calling the parent method.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            A tuple of (generated_text, metadata)
        """
        # Add Ollama-specific parameters
        ollama_kwargs = {
            "api_base": self.base_url,
        }

        # Merge with provided kwargs
        all_kwargs = {**ollama_kwargs, **kwargs}

        # Call parent implementation with updated kwargs
        return await super().generate_content_async(prompt, **all_kwargs)


class EnhancedGemini(BaseLlm):
    """
    Enhanced Gemini model with additional features.

    Direct implementation using the Google Generative AI Python SDK.
    Provides:
    1. Better error handling
    2. Retry logic for transient failures
    3. Detailed metadata
    """

    model_config = ConfigDict(extra="allow")

    # Add required BaseLlm field "model"
    model: str = Field(default="gemini-1.5-flash")

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        retry_count: int = 2,
        **kwargs,
    ):
        """
        Initialize the Enhanced Gemini model.

        Args:
            model_name: The specific Gemini model to use
            api_key: Google AI API key
            temperature: Sampling temperature (0.0-1.0)
            max_output_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        # Initialize the parent BaseLlm
        super().__init__(model=model_name, **kwargs)

        # Get API key from environment if not provided
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("AI_STUDIO_API_KEY")

        if not api_key:
            raise ValueError("API key is required for Gemini but not found. Set GOOGLE_API_KEY or AI_STUDIO_API_KEY environment variable.")

        # Store parameters
        self._model_name = model_name
        self._api_key = api_key
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._timeout = timeout
        self._retry_count = retry_count

    def _configure_api(self):
        """Configure the Google Generative AI API with the API key."""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        return genai

    def _create_model(self, genai):
        """Create and return a Gemini model instance."""
        return genai.GenerativeModel(self._model_name)

    async def _process_string_prompt(self, model, prompt):
        """Process a string prompt and return the response."""
        response = await model.generate_content_async(prompt)
        # Handle async generator
        if hasattr(response, "__aiter__"):
            parts = []
            async for part in response:
                parts.append(part)
            response = parts[-1] if parts else None
        return response

    async def _process_message_list(self, model, messages):
        """Process a list of messages and return the chat response."""
        # Convert list of message dicts to chat format
        chat = model.start_chat()
        for message in messages:
            if message["role"] == "user":
                response = await chat.send_message_async(message["content"])
                # Handle async generator
                if hasattr(response, "__aiter__"):
                    parts = []
                    async for part in response:
                        parts.append(part)
                    response = parts[-1] if parts else None
            # For simplicity, we ignore assistant messages as they're already part of the history

        # Get the last response from the chat
        return chat.last

    def _extract_text(self, response):
        """Extract text from a response object."""
        if hasattr(response, "text"):
            return response.text
        else:
            return str(response)

    def _build_metadata(self, attempt):
        """Build metadata for the response."""
        return {
            "provider": "ai_studio",
            "model": self._model_name,
            "attempt": attempt + 1,
        }

    def _handle_error(self, error, attempt):
        """Handle errors, either by logging for retry or raising."""
        if attempt < self._retry_count:
            # Log the error and signal for retry
            print(f"Gemini error (attempt {attempt + 1}/{self._retry_count + 1}): {error}")
            return True  # Retry
        else:
            # Format error message and re-raise on final attempt
            error_message = format_api_error(error, "ai_studio", self._model_name)
            raise ValueError(f"Gemini error: {error_message}") from error

    async def generate_content_async(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content using the Google Generative AI Python SDK.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            A tuple of (generated_text, metadata)
        """
        # Use a retry loop for resilience
        last_error = None
        for attempt in range(self._retry_count + 1):
            try:
                # Configure the API
                genai = self._configure_api()

                # Create a model
                model = self._create_model(genai)

                # Process the prompt
                if isinstance(prompt, str):
                    # Simple text prompt
                    response = await self._process_string_prompt(model, prompt)
                else:
                    # Chat messages
                    response = await self._process_message_list(model, prompt)

                # Extract text from response
                result_text = self._extract_text(response)

                # Build metadata
                metadata = self._build_metadata(attempt)

                # Return the result
                return result_text, metadata

            except Exception as e:
                last_error = e
                should_retry = self._handle_error(e, attempt)
                if should_retry:
                    continue
                # If _handle_error didn't raise, we still propagate the exception
                raise

        # This should never be reached due to the raise in the loop
        raise ValueError("Unknown error in Gemini")

    async def generate_content(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content with the Gemini model.

        This is a convenience method that calls generate_content_async.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            A tuple of (generated_text, metadata)
        """
        return await self.generate_content_async(prompt, **kwargs)

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def retry_count(self) -> int:
        """Get the retry count."""
        return self._retry_count


class ModelConfig(BaseModel):
    """Configuration for model creation."""

    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    retry_count: int = 2
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


def create_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
    retry_count: int = 2,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
) -> BaseLlm:
    """
    Factory function to create the appropriate model based on configuration.

    Args:
        provider: LLM provider (ai_studio, openai, anthropic, etc.)
        model_name: Specific model to use
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        retry_count: Number of retries on failure
        fallback_provider: Provider to use if primary provider fails
        fallback_model: Model to use if primary model fails

    Returns:
        An ADK BaseLlm instance for the requested provider and model

    Raises:
        ValueError: If the provider is not supported or API key is missing
    """
    config = get_config()

    # Use provided values or defaults from config
    target_provider = provider or config.default_provider
    target_model = model_name or config.default_model

    # Check if provider is valid
    known_providers = get_model_providers()

    # If provider is not known, immediately use fallback
    if target_provider not in known_providers:
        if fallback_provider and fallback_provider in known_providers:
            print(f"Unknown provider '{target_provider}'. Falling back to {fallback_provider}/{fallback_model}")
            return create_model(
                provider=fallback_provider,
                model_name=fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
                fallback_provider=None,  # Prevent infinite fallback loop
                fallback_model=None,
            )

    # Get API key for the provider
    api_key = get_api_key(target_provider)

    # Configure fallbacks if not explicitly provided
    fallback_provider = fallback_provider or getattr(config, "fallback_provider", None)
    fallback_model = fallback_model or getattr(config, "fallback_model", None)

    # Set up default fallbacks if still not configured
    if not fallback_provider and target_provider != "ai_studio":
        fallback_provider = "ai_studio"
        fallback_model = "gemini-1.5-flash"
    elif not fallback_provider and target_provider == "ai_studio":
        fallback_provider = "openai"
        fallback_model = "gpt-3.5-turbo"

    # Create model based on provider
    try:
        if target_provider == "ai_studio":
            # Use enhanced Gemini implementation
            return EnhancedGemini(
                model_name=target_model,
                api_key=api_key,
                temperature=temperature,
                max_output_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
            )
        elif target_provider == "ollama":
            # Use specialized Ollama wrapper
            return OllamaLlm(
                model_name=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
            )
        else:
            # Use general LiteLlm wrapper for other providers
            if target_provider in ["openai", "anthropic", "groq"] and not api_key:
                raise ValueError(f"API key required for {target_provider} but not found")

            return LiteLlm(
                provider=target_provider,
                model_name=target_model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
            )
    except Exception as e:
        # If fallback is configured and this isn't already a fallback attempt,
        # try to create a fallback model
        if fallback_provider and fallback_model and target_provider != fallback_provider:
            print(f"Error creating {target_provider}/{target_model}: {e}")
            print(f"Falling back to {fallback_provider}/{fallback_model}")

            # Ensure the fallback values are strings (important for tests with mocks)
            fb_provider = str(fallback_provider) if fallback_provider is not None else None
            fb_model = str(fallback_model) if fallback_model is not None else None

            # Create fallback model (with no additional fallback to prevent loops)
            return create_model(
                provider=fb_provider,
                model_name=fb_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
                fallback_provider=None,
                fallback_model=None,
            )
        else:
            # No fallback or already in fallback, re-raise the error
            raise


def get_model_providers() -> List[str]:
    """
    Get the list of available model providers.

    Returns:
        List of provider names
    """
    return ["ai_studio", "openai", "anthropic", "groq", "ollama"]


def get_default_models_by_provider() -> Dict[str, str]:
    """
    Get the default models for each provider.

    Returns:
        Dictionary mapping provider names to their default models
    """
    return {
        "ai_studio": "gemini-1.5-flash",
        "openai": "gpt-3.5-turbo",
        "anthropic": "claude-3-haiku",
        "groq": "llama3-70b-8192",
        "ollama": "llama3.2:latest",
    }
