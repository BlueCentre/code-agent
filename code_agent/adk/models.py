"""
ADK model implementations for Code Agent.

This module provides:
1. Google Gemini model integration via google.adk.models.Gemini
2. LiteLLM wrapper for other model providers (OpenAI, Anthropic, etc.)
3. Factory function to create the appropriate model based on configuration
4. Fallback behavior for handling model failures
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union

import litellm
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field

from code_agent.config.config import get_api_key, get_config
from code_agent.tools.error_utils import format_api_error

# Add abstract methods to BaseLlm
# Monkey patch BaseLlm to add the required methods for testing
BaseLlm._generate_prompt = abstractmethod(lambda self, *args, **kwargs: None)
BaseLlm._extract_content = abstractmethod(lambda self, *args, **kwargs: None)
BaseLlm.generate_content = abstractmethod(lambda self, *args, **kwargs: None)
BaseLlm.generate_content_async = abstractmethod(lambda self, *args, **kwargs: None)


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

    def _generate_prompt(self, prompt: Union[str, List[Dict[str, str]], LlmRequest]) -> List[Dict[str, str]]:
        """
        Convert different prompt types to a standardized messages format.

        Args:
            prompt: Either a string prompt, list of messages, or LlmRequest

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        if isinstance(prompt, LlmRequest):
            # Extract messages from LlmRequest contents
            messages = []
            for content_item in prompt.contents:
                # Assuming simple text parts for now
                if content_item.parts and hasattr(content_item.parts[0], "text") and content_item.parts[0].text:
                    messages.append({"role": content_item.role, "content": content_item.parts[0].text})
            return messages
        elif isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list):
            return prompt
        else:
            raise TypeError(f"Unsupported prompt type: {type(prompt)}")

    def _extract_content(self, response: Any) -> str:
        """
        Extract content from a LiteLLM API response.

        Args:
            response: The raw response from LiteLLM API

        Returns:
            Extracted text content
        """
        return response.choices[0].message.content

    async def generate_content_async(self, prompt: Union[str, List[Dict[str, str]], LlmRequest], **kwargs: Any) -> LlmResponse:
        """
        Generate content using the LiteLLM model (ADK BaseLlm required method).

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            An LlmResponse object containing the generated content and metadata
        """
        # ADK runner might pass LlmRequest, direct calls might pass str/list
        messages = self._generate_prompt(prompt)

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
                content = self._extract_content(response)

                # Return content and metadata
                metadata = {
                    "provider": self.provider,
                    "model": self.model_name,
                    "finish_reason": response.choices[0].finish_reason,
                    "usage": response.usage.model_dump() if hasattr(response, "usage") else {},
                }

                # Construct LlmResponse with content structure
                response_content = types.Content(parts=[types.Part(text=content)])
                # Pass metadata directly if LlmResponse accepts it, otherwise omit or handle differently
                # Assuming LlmResponse might have a metadata field based on previous errors, trying that.
                try:
                    return LlmResponse(content=response_content, metadata=metadata)
                except Exception:  # Fallback if metadata kwarg isn't valid
                    return LlmResponse(content=response_content)

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
        # pragma: no cover # Hard-to-hit safeguard, assumes loop finishes without error/return
        if last_error:
            error_message = format_api_error(last_error, self.provider, self.model_name)
            raise ValueError(f"LiteLLM error: {error_message}") from last_error
        else:  # pragma: no cover # Even less likely path
            raise ValueError("Unknown error in LiteLLM")

    def generate_content(self, prompt: Union[str, List[Dict[str, str]], LlmRequest], **kwargs: Any) -> LlmResponse:
        """
        Synchronous wrapper around generate_content_async.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            An LlmResponse object containing the generated content and metadata
        """
        # Run the async method in a new event loop
        import asyncio

        # Use a helper function to run the async method
        async def _run_async():
            return await self.generate_content_async(prompt, **kwargs)

        # Create a new event loop and run the async function to completion
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_run_async())
        finally:
            loop.close()


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

    async def generate_content_async(self, prompt: Union[str, List[Dict[str, str]]], **kwargs: Any) -> LlmResponse:
        """
        Generate content using the Ollama model.

        Adds Ollama-specific parameters before calling the parent method.

        Args:
            prompt: Either a string prompt or a list of chat messages
            **kwargs: Additional arguments passed to the model

        Returns:
            An LlmResponse object containing the generated content and metadata
        """
        # Add Ollama-specific parameters
        ollama_kwargs = {
            "api_base": self.base_url,
        }

        # Merge with provided kwargs
        all_kwargs = {**ollama_kwargs, **kwargs}

        # Call parent implementation with updated kwargs
        # Parent returns an LlmResponse object
        return await super(OllamaLlm, self).generate_content_async(prompt, **all_kwargs)


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
) -> Union[BaseLlm, str]:
    """
    Factory function to select the appropriate model identifier or instance.

    For LiteLLM/Ollama providers, returns an initialized model instance.
    For ai_studio (Gemini), returns the validated model name string for use with LlmAgent.

    Args:
        provider: LLM provider (ai_studio, openai, anthropic, etc.)
        model_name: Specific model to use
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        retry_count: Number of retries on failure (used by LiteLlm/OllamaLlm)
        fallback_provider: Provider to use if primary provider fails
        fallback_model: Model to use if primary model fails

    Returns:
        - For LiteLLM/Ollama: An initialized BaseLlm instance.
        - For ai_studio: The validated model name string (e.g., "gemini-1.5-flash").

    Raises:
        ValueError: If the provider is not supported or API key is missing
    """
    config = get_config()

    # Use provided values or defaults from config
    # Convert values to strings if they're not None to handle MagicMock objects in tests
    if provider is not None:
        target_provider = str(provider)
    else:
        target_provider = config.default_provider

    if model_name is not None:
        target_model = str(model_name)
    else:
        target_model = config.default_model

    # Check if provider is valid
    known_providers = get_model_providers()

    # If provider is not known, immediately use fallback
    if target_provider not in known_providers:
        # Make sure fallback provider is a string
        if fallback_provider and str(fallback_provider) in known_providers:
            fb_provider = str(fallback_provider)
            fb_model = str(fallback_model) if fallback_model else None
            print(f"Unknown provider '{target_provider}'. Falling back to {fb_provider}/{fb_model}")
            return create_model(
                provider=fb_provider,
                model_name=fb_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count,
                fallback_provider=None,  # Prevent infinite fallback loop
                fallback_model=None,
            )
        else:
            # If initial provider is unknown and no valid fallback is available, raise error
            raise ValueError(f"Unsupported provider: '{target_provider}'. Known providers: {known_providers}")

    # Get API key based on provider
    api_key = get_api_key(target_provider)

    # Configure fallbacks if not explicitly provided
    # Make sure to convert to string for test mocks
    if fallback_provider is None:
        fallback_provider = getattr(config, "fallback_provider", None)
        if fallback_provider is not None:
            fallback_provider = str(fallback_provider)

    if fallback_model is None:
        fallback_model = getattr(config, "fallback_model", None)
        if fallback_model is not None:
            fallback_model = str(fallback_model)

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
            # For ai_studio, return the validated model name string.
            # The caller (e.g., LlmAgent) will handle instantiation.
            # Ensure the target model name is valid for Gemini (optional check, could be added)
            if not target_model.startswith("gemini-"):
                print(f"Warning: Model name '{target_model}' for ai_studio doesn't start with 'gemini-'")
            return target_model
        elif target_provider == "ollama":
            # Use specialized Ollama wrapper
            ollama_config = config.ollama or {}
            ollama_url = ollama_config.get("url", "http://localhost:11434")
            return OllamaLlm(
                model_name=target_model,
                base_url=ollama_url,  # Pass correct URL
                temperature=temperature if temperature is not None else 0.7,  # Use default if None
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count if retry_count is not None else 1,  # Ollama default retry 1
            )
        else:
            # Use general LiteLlm wrapper for other providers
            if target_provider in ["openai", "anthropic", "groq"] and not api_key:
                raise ValueError(f"API key required for {target_provider} but not found")

            litellm_base_url = None
            if target_provider == "openai":
                litellm_base_url = "https://api.openai.com/v1"
            elif target_provider == "groq":
                litellm_base_url = "https://api.groq.com/openai/v1"
            # Add other bases if needed

            return LiteLlm(
                provider=target_provider,
                model_name=target_model,
                api_key=api_key,
                api_base=litellm_base_url,  # Pass base URL if needed
                temperature=temperature if temperature is not None else 0.7,  # Use default if None
                max_tokens=max_tokens,
                timeout=timeout,
                retry_count=retry_count if retry_count is not None else 2,  # Use default if None
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

            # Get fallback model identifier/instance (with no additional fallback)
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
        "openai": "gpt-4",
        "anthropic": "claude-3-opus",
        "groq": "llama3-70b-8192",
        "ollama": "llama3.2:latest",
    }
