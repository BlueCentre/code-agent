"""
Tests for the streaming functionality in code_agent.adk.models_v2 module.
"""

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm.utils import CustomStreamWrapper

from code_agent.adk.models_v2 import LiteLlm, OllamaLlm


class TestLiteLlmStreaming:
    """Test the streaming capabilities of the LiteLlm class."""

    @pytest.mark.asyncio
    async def test_stream_content_async(self):
        """Test that stream_content_async properly handles streaming responses."""
        # Create a mock AsyncMock for litellm.acompletion_streaming
        mock_streaming_response = AsyncMock()
        mock_streaming_response.__aiter__.return_value = [
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content="Hello"),
                        finish_reason=None,
                    )
                ],
                created=1234567890,
                model="gpt-4",
            ),
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content=" world"),
                        finish_reason=None,
                    )
                ],
                created=1234567890,
                model="gpt-4",
            ),
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content="!"),
                        finish_reason="stop",
                    )
                ],
                created=1234567890,
                model="gpt-4",
            ),
        ]

        # Create a LiteLlm instance
        model = LiteLlm(provider="openai", model_name="gpt-4")

        # Mock the litellm.acompletion_streaming method
        with patch("litellm.acompletion_streaming", return_value=mock_streaming_response):
            # Call the stream_content_async method with a simple prompt
            responses = model.stream_content_async("Hello, how are you?")

            # Verify it's an AsyncGenerator
            assert isinstance(responses, AsyncGenerator)

            # Collect the responses
            collected_responses = []
            async for response in responses:
                collected_responses.append(response)

            # Verify we received 3 responses
            assert len(collected_responses) == 3

            # Check content of first response
            assert collected_responses[0].content.parts[0].text == "Hello"

            # Check content of second response
            assert collected_responses[1].content.parts[0].text == " world"

            # Check content of last response
            assert collected_responses[2].content.parts[0].text == "!"

            # Verify metadata in the last response
            assert "finish_reason" in collected_responses[2].metadata
            assert collected_responses[2].metadata["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_stream_content_async_error_handling(self):
        """Test that stream_content_async properly handles errors."""
        # Create a LiteLlm instance
        model = LiteLlm(provider="openai", model_name="gpt-4", retry_count=1)

        # Mock litellm.acompletion_streaming to raise an exception
        with patch("litellm.acompletion_streaming", side_effect=Exception("API Error")):
            # Call the stream_content_async method
            responses = model.stream_content_async("Hello, how are you?")

            # Verify it returns an AsyncGenerator
            assert isinstance(responses, AsyncGenerator)

            # Attempting to iterate should raise ValueError
            with pytest.raises(ValueError, match="LiteLLM error:"):
                async for _ in responses:
                    pass


class TestOllamaLlmStreaming:
    """Test the streaming capabilities of the OllamaLlm class."""

    @pytest.mark.asyncio
    async def test_ollama_stream_content_async(self):
        """Test that OllamaLlm.stream_content_async properly handles streaming responses."""
        # Create a mock AsyncMock for litellm.acompletion_streaming
        mock_streaming_response = AsyncMock()
        mock_streaming_response.__aiter__.return_value = [
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content="Hello"),
                        finish_reason=None,
                    )
                ],
                created=1234567890,
                model="llama3",
            ),
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content=" from"),
                        finish_reason=None,
                    )
                ],
                created=1234567890,
                model="llama3",
            ),
            CustomStreamWrapper(
                choices=[
                    MagicMock(
                        delta=MagicMock(content=" Ollama"),
                        finish_reason="stop",
                    )
                ],
                created=1234567890,
                model="llama3",
            ),
        ]

        # Create an OllamaLlm instance
        model = OllamaLlm(model_name="llama3")

        # Mock the litellm.acompletion_streaming method
        with patch("litellm.acompletion_streaming", return_value=mock_streaming_response):
            # Call the stream_content_async method with a simple prompt
            responses = model.stream_content_async("Hello, how are you?")

            # Verify it's an AsyncGenerator
            assert isinstance(responses, AsyncGenerator)

            # Collect the responses
            collected_responses = []
            async for response in responses:
                collected_responses.append(response)

            # Verify we received 3 responses
            assert len(collected_responses) == 3

            # Check content of responses
            assert collected_responses[0].content.parts[0].text == "Hello"
            assert collected_responses[1].content.parts[0].text == " from"
            assert collected_responses[2].content.parts[0].text == " Ollama"

            # Verify metadata in the last response
            assert "finish_reason" in collected_responses[2].metadata
            assert collected_responses[2].metadata["finish_reason"] == "stop"
            assert collected_responses[2].metadata["provider"] == "ollama"
