# Ollama Integration

This document explains how to use the integration with [Ollama](https://ollama.ai/) in the Code Agent CLI.

## Overview

Ollama is a tool that allows you to run large language models (LLMs) locally on your own machine. The Code Agent provides two ways to use Ollama:

1. **Direct Provider** (Recommended) - A direct HTTP client that communicates with Ollama without using Google ADK
2. **ADK Integration** (Experimental) - Integration with Google ADK (which may have compatibility issues)

## Prerequisites

1. Install Ollama from [https://ollama.ai/download](https://ollama.ai/download)
2. Start Ollama service: `ollama serve`
3. Pull models you want to use:
   ```bash
   ollama pull llama3.2
   ollama pull codellama:13b
   ```

## Using the Direct Provider

The most reliable way to use Ollama is through the `OllamaDirectProvider` class. This bypasses potential compatibility issues with Google ADK.

### Example Usage

```python
from code_agent.agents.ollama import OllamaDirectProvider

# Initialize provider with your model and Ollama URL
provider = OllamaDirectProvider(
    model="llama3.2:latest",  # Use any model you've pulled in Ollama
    base_url="http://localhost:11434"
)

# Generate text (works reliably)
response = provider.generate("What is your name?")
print(response)

# List available models
models = provider.list_models()
for model in models:
    print(f"- {model.get('name')}")
```

See `docs/example_ollama_direct_usage.py` for a complete working example.

## Experimental ADK Integration 

The Code Agent CLI also includes experimental integration with Google ADK. This method is less reliable due to compatibility issues with ADK's model registry.

### Configuration

To use Ollama with the ADK integration:

1. Configure your `~/.config/code-agent/config.yaml`:
   ```yaml
   default_provider: "ollama"
   default_model: "llama3:latest"  # Must match an installed model
   
   ollama:
     url: "http://localhost:11434"
   ```

2. When running commands, specify the provider:
   ```bash
   code-agent run "Your query" --provider ollama
   ```

**Note**: If you encounter model errors, use the Direct Provider approach instead.

## Commands for Managing Ollama

You can manage your Ollama installation directly with these commands:

```bash
# List models 
ollama list

# Pull a model
ollama pull llama3

# Run Ollama (if it's not already running)
ollama serve
```

## Commands

### List Available Models

```bash
code-agent ollama list
```

This will display a table of available models with details like parameter size, family, format, and quantization level.

For JSON output:

```bash
code-agent ollama list --json
```

### Chat with a Model

Use this command for direct, stateful chat sessions with a specific Ollama model, separate from the main agent chat history.

```bash
code-agent ollama chat llama3 "Hello, how are you?"
```

Options:
- `--system`: Set a system prompt
  ```bash
  code-agent ollama chat codellama:13b "How do I use async/await in JavaScript?" --system "You are a helpful coding assistant"
  ```
- `--temperature`: Set the temperature (default: 0.7)
  ```bash
  code-agent ollama chat llama3 "Tell me a story" --temperature 0.9
  ```
- `--url`: Specify custom Ollama API URL
  ```bash
  code-agent ollama chat llama3 "Hello" --url http://remote-server:11434
  ```

## Custom Ollama Server URL

By default, the CLI connects to Ollama at `http://localhost:11434`. You can specify a different URL with the `--url` parameter on the `ollama list` or `ollama chat` commands.

## Test Mode

The `ollama list` and `ollama chat` commands support a test mode which allows you to run the commands without making actual API calls to Ollama. This is useful for testing or demonstrating the CLI when Ollama isn't running or available.

To use test mode, add the `--test` flag:

```bash
# List models in test mode
code-agent ollama list --test

# Chat with a model in test mode
code-agent ollama chat llama3 "Hello, how are you?" --test
```

Test mode will display sample data or simulate interaction.

## Advantages of Local Models

- Privacy: All data stays on your machine
- No API key required
- No usage costs
- Works offline
- Customizable with fine-tuning options

## Troubleshooting

Common issues:

1. **Cannot connect to Ollama**: Make sure Ollama is running locally with `ollama serve`
2. **Model not found**: Check that you've pulled the model first with `ollama pull <model_name>`
3. **Slow responses**: Larger models require more computational resources, try using a smaller model

## Sequence Diagram

The following sequence diagram illustrates the flow of information when using the dedicated Ollama commands:

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Application (cli/main.py)
    participant OllamaCmd as Ollama Commands (cli/commands/ollama.py)
    participant OllamaService as Ollama Local Service

    %% Model listing flow
    User->>CLI: code-agent ollama list
    CLI->>OllamaCmd: Invoke list_models command
    OllamaCmd->>OllamaService: GET /api/tags (via HTTP client)
    OllamaService->>OllamaCmd: Return available models
    OllamaCmd->>CLI: Display models in table or JSON format
    CLI->>User: Show formatted output

    %% Chat completion flow
    User->>CLI: code-agent ollama chat <model> "prompt" [--system ...]
    CLI->>OllamaCmd: Invoke chat_with_model command
    Note over OllamaCmd: Prepare messages array with prompt/system
    OllamaCmd->>OllamaService: POST /api/chat with model and messages (via HTTP client)
    OllamaService->>OllamaCmd: Return completion response
    OllamaCmd->>CLI: Display response content
    CLI->>User: Show model's response
```

This diagram illustrates:
1. How the dedicated `ollama` CLI commands interact directly with the Ollama service.
2. The API endpoints used for listing models and chat completions.
3. How system prompts are handled in the chat flow.
