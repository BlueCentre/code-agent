# Ollama Integration

This package provides integration with [Ollama](https://ollama.ai/) for running local LLM models.

## Code Organization

The Ollama integration code has been completely reorganized as of [date]:

- All functional code is now properly located in this package
- All end-to-end tests have been moved to the `tests/e2e/` directory 
- Legacy files and test directories at the project root have been removed

## Components

- `provider.py` - Contains the `OllamaDirectProvider` class for direct HTTP interaction with Ollama
- `adk_integration.py` - EXPERIMENTAL integration with Google ADK (not fully functional)

## Usage

### Direct Provider

The `OllamaDirectProvider` provides a simple interface for interacting with Ollama:

```python
from code_agent.agents.ollama import OllamaDirectProvider

# Initialize with a specific model
provider = OllamaDirectProvider(model="llama3")

# Generate text
response = provider.generate("What is the capital of France?")
print(response)

# Chat with messages
messages = [
    {"role": "user", "content": "Hello, how are you?"}
]
response = provider.chat(messages)
print(response)

# List available models
models = provider.list_models()
print(models)
```

## Google ADK Integration Status

The Google ADK integration (`OllamaLlm` in `adk_integration.py`) is **experimental** and not fully functional due to compatibility challenges with the current Google ADK version (0.4.0).

See `docs/testing_adk_cli_e2e.md` for details on the challenges encountered during integration testing. 

### Agent Usage

```python
from google.adk.agents import Agent
from code_agent.agents.ollama.adk_integration import OllamaLlm

# Create custom Ollama LLM for ADK
ollama_llm = OllamaLlm(
    model="llama3.2",  # Use your preferred Ollama model
    base_url="http://localhost:11434"  # Adjust if your Ollama server is on a different address
)

# Initialize agent with the custom LLM
root_agent = Agent(
    model=ollama_llm,  # Use the OllamaLlm instance instead of model name string
    name='root_agent',
    description='A helpful assistant powered by a local Ollama model.',
    instruction='Answer user questions to the best of your knowledge.'
)
```