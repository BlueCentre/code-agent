# ADK Model Integration

This document outlines the implementation of model integration for the Google ADK Migration project.

## Overview

The model integration enables:

1. Native support for Google Gemini models through the enhanced `EnhancedGemini` class
2. Support for other LLM providers (OpenAI, Anthropic, Groq) through a custom `LiteLlm` wrapper
3. Integration with local Ollama models via a specialized `OllamaLlm` implementation
4. Consistent interface through the `BaseLlm` abstract class from Google ADK
5. Resilient error handling with configurable retry logic and fallback mechanisms
6. Flexible model switching based on configuration

## Implementation Files

The model integration consists of the following files:

- `code_agent/adk/models.py`: Main implementation of model wrappers and factory function
- `code_agent/adk/__init__.py`: Re-exports model components for easy access
- `tests/unit/test_adk_models.py`: Unit tests for model implementations
- `tests/integration/test_adk_models_integration.py`: Integration tests for actual API calls
- `sandbox/adk_test_models.py`: CLI tool for manual testing of model implementations

## Architecture

### BaseLlm Implementation

All model implementations inherit from Google ADK's `BaseLlm` abstract class, which defines the core interface:

```python
async def generate_content(
    self,
    prompt: Union[str, List[Dict[str, str]]],
    **kwargs: Any
) -> Tuple[str, Dict[str, Any]]:
    """Generate content from a prompt or messages."""
```

This provides a consistent interface for all model implementations.

### Model Implementations

1. **Enhanced Gemini Model**: Extension of ADK's `Gemini` class with improved features:

```python
class EnhancedGemini(Gemini):
    """Enhanced Gemini model with additional features."""
    
    async def generate_content_async(self, prompt, **kwargs):
        # Implement retry logic
        # Handle errors with detailed messages
        # Add enhanced metadata
        # Call parent implementation
```

2. **LiteLlm Wrapper**: Custom wrapper for other providers through litellm:

```python
class LiteLlm(BaseLlm):
    """ADK model implementation that wraps LiteLLM."""
    
    async def generate_content(self, prompt, **kwargs):
        # Convert prompt to messages if needed
        # Call litellm.acompletion
        # Process response and return content with metadata
```

3. **OllamaLlm**: Specialized implementation for local Ollama models:

```python
class OllamaLlm(LiteLlm):
    """Specialized LiteLLM wrapper for Ollama models."""
    
    def __init__(self, model_name="llama3", base_url="http://localhost:11434", ...):
        # Configure for Ollama
        super().__init__(provider="ollama", model_name=model_name, ...)
        self.base_url = base_url
```

### Factory Function

The `create_model` factory function provides a simple way to create the appropriate model based on configuration, with support for fallback models:

```python
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
    """Factory function to create the appropriate model with fallback support."""
    # Use config defaults if not specified
    # Configure fallback chains
    # Try to create primary model
    # Fall back to alternative if primary fails
```

## Configuration

Model configuration is integrated with the existing configuration system:

1. **Default Provider and Model**:
   - `default_provider` from config (e.g., "ai_studio", "openai")
   - `default_model` from config (e.g., "gemini-1.5-flash", "gpt-4")

2. **API Keys**:
   - Loaded from config or environment variables
   - Environment variable mapping:
     - `GOOGLE_API_KEY` or `AI_STUDIO_API_KEY` for Google AI Studio
     - `OPENAI_API_KEY` for OpenAI
     - `ANTHROPIC_API_KEY` for Anthropic
     - `GROQ_API_KEY` for Groq

3. **Model Parameters**:
   - `temperature` (default: 0.7)
   - `max_tokens` (optional)
   - `timeout` (optional)
   - `retry_count` (default: 2)

4. **Fallback Configuration**:
   - `fallback_provider` - Alternative provider if primary fails
   - `fallback_model` - Alternative model if primary fails
   - Default fallbacks:
     - For non-Gemini models: falls back to "ai_studio"/"gemini-1.5-flash"
     - For Gemini models: falls back to "openai"/"gpt-3.5-turbo"

## Error Handling and Resilience

The model implementations include robust error handling and resilience features:

1. **Retry Logic**:
   - Configurable retry count for transient errors
   - Progressive error reporting
   - Detailed error messages using existing `format_api_error` utility

2. **Fallback Chains**:
   - Automatic fallback to secondary models when primary models fail
   - Configurable fallback providers and models
   - Smart defaults that avoid falling back to the same provider
   - Loop prevention for fallback chains

3. **Validation**:
   - API key verification before attempting calls
   - Parameter validation
   - Provider-specific error handling

4. **Enhanced Metadata**:
   - Attempt count tracking
   - Provider identification
   - Model information
   - Standardized metadata format across providers

## Testing

### Unit Tests

Unit tests (`tests/unit/test_adk_models.py`) verify:

1. Correct formatting of prompts and messages
2. Proper handling of API responses
3. Retry behavior
4. Error handling
5. Provider-specific parameter handling
6. Fallback mechanism functionality

### Integration Tests

Integration tests (`tests/integration/test_adk_models_integration.py`) verify:

1. Actual API connectivity (when credentials are available)
2. Response quality and format
3. Conversation history handling
4. Cross-provider compatibility
5. Fallback behavior with unavailable models

### Manual Testing

The `sandbox/adk_test_models.py` script provides a simple CLI for manual testing:

```bash
# List available providers
python sandbox/adk_test_models.py --list-providers

# Test Gemini model
python sandbox/adk_test_models.py --provider ai_studio

# Test OpenAI with specific model
python sandbox/adk_test_models.py --provider openai --model gpt-4 --verbose

# Test with custom prompt
python sandbox/adk_test_models.py --provider anthropic --prompt "Explain quantum computing"

# Test fallback behavior
python sandbox/adk_test_models.py --provider invalid --fallback-provider openai
```

## Usage Examples

### Basic Usage

```python
from code_agent.adk.models import create_model

# Create model using config defaults
model = create_model()

# Generate content from a string prompt
content, metadata = await model.generate_content("Hello, world!")
print(content)

# Generate content from a message history
messages = [
    {"role": "user", "content": "Who are you?"},
    {"role": "assistant", "content": "I'm an AI assistant."},
    {"role": "user", "content": "What can you help me with?"}
]
content, metadata = await model.generate_content(messages)
print(content)
```

### Specific Provider with Fallback

```python
# Create OpenAI model with Gemini fallback
openai_model = create_model(
    provider="openai",
    model_name="gpt-4-turbo",
    temperature=0.8,
    fallback_provider="ai_studio",
    fallback_model="gemini-1.5-flash"
)

# Create Ollama model with OpenAI fallback
ollama_model = create_model(
    provider="ollama",
    model_name="llama3",
    temperature=0.5,
    fallback_provider="openai",
    fallback_model="gpt-3.5-turbo"
)
```

## Next Steps

1. **Stream Support**: Add streaming response support for models that offer it
2. **Tool Calling**: Implement function/tool calling for models that support it
3. **Caching**: Add response caching for improved performance
4. **Context Window Management**: Add utilities for managing context windows across providers 