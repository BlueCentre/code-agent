# Models and Providers Feature

This document details the supported AI model providers and specific models available in Code Agent.

## Supported Providers

Code Agent supports multiple AI providers through LiteLLM integration, allowing you to choose the best model for your needs:

| Provider | Description | Default Model | API Key Format |
|----------|-------------|---------------|----------------|
| Google AI Studio | Google's Gemini models | gemini-2.0-flash | `aip-...` |
| OpenAI | GPT models | gpt-4o | `sk-...` |
| Anthropic | Claude models | claude-3-sonnet | `sk-ant-...` |
| Groq | Fast inference for open models | llama3-70b-8192 | `gsk_...` |

## Provider-Specific Models

### Google AI Studio

Google AI Studio is the default provider in Code Agent.

**Available Models:**
- `gemini-2.0-flash` (Default) - Fast, efficient model for most tasks
- `gemini-2.0-pro` - More powerful model for complex tasks
- `gemini-1.5-flash` - Previous generation fast model
- `gemini-1.5-pro` - Previous generation capable model

**API Key Setup:**
1. Get your key from [AI Studio](https://ai.google.dev/)
2. Set as environment variable: `export AI_STUDIO_API_KEY=aip-...`
3. Or add to config: `api_keys.ai_studio: "aip-..."`

**Usage Example:**
```bash
# Use the default AI Studio provider
code-agent run "Explain generators in Python"

# Specify a more powerful model
code-agent --model gemini-2.0-pro run "Write a complex regex for email validation"
```

### OpenAI

**Available Models:**
- `gpt-4o` - Latest GPT-4 model with vision capabilities
- `gpt-4-turbo` - Fast GPT-4 model with recent knowledge
- `gpt-4` - Original GPT-4 model
- `gpt-3.5-turbo` - Faster, more efficient model
- `gpt-4o-mini` - Smaller, faster version of GPT-4o

**API Key Setup:**
1. Get your key from [OpenAI Platform](https://platform.openai.com/)
2. Set as environment variable: `export OPENAI_API_KEY=sk-...`
3. Or add to config: `api_keys.openai: "sk-..."`

**Usage Example:**
```bash
# Use OpenAI as provider
code-agent --provider openai run "Create a JavaScript function for array pagination"

# Specify a specific OpenAI model
code-agent --provider openai --model gpt-3.5-turbo run "Simple Python script to rename files"
```

### Anthropic

**Available Models:**
- `claude-3.5-sonnet` - Latest Claude model with enhanced performance
- `claude-3-opus` - Most powerful Claude model
- `claude-3-sonnet` - Balanced performance and speed
- `claude-3-haiku` - Fastest, most efficient Claude model

**API Key Setup:**
1. Get your key from [Anthropic Console](https://console.anthropic.com/)
2. Set as environment variable: `export ANTHROPIC_API_KEY=sk-ant-...`
3. Or add to config: `api_keys.anthropic: "sk-ant-..."`

**Usage Example:**
```bash
# Use Anthropic as provider
code-agent --provider anthropic run "Create a comprehensive test suite for a Python function"

# Specify a specific Anthropic model
code-agent --provider anthropic --model claude-3-opus run "Design a complex database schema"
```

### Groq

**Available Models:**
- `llama3-70b-8192` - Largest, most capable Llama 3 model
- `llama3-8b-8192` - Smaller Llama 3 model
- `mixtral-8x7b-32768` - Mixtral model with large context window
- `gemma-7b-it` - Google's Gemma model

**API Key Setup:**
1. Get your key from [Groq Console](https://console.groq.com/)
2. Set as environment variable: `export GROQ_API_KEY=gsk_...`
3. Or add to config: `api_keys.groq: "gsk_..."`

**Usage Example:**
```bash
# Use Groq as provider for fast inference
code-agent --provider groq --model llama3-70b-8192 run "Generate a complex SQL query"
```

## Selecting Models and Providers

### Command Line Options

You can specify the provider and model directly in the command line:

```bash
code-agent --provider <provider_name> --model <model_name> [command]
```

These options take precedence over configuration file settings.

### Configuration File

You can set default provider and model in your configuration file:

```yaml
# In ~/.config/code-agent/config.yaml
default_provider: "openai"
default_model: "gpt-4o"
```

### Environment Variables

You can set the default provider and model using environment variables:

```bash
export CODE_AGENT_DEFAULT_PROVIDER=anthropic
export CODE_AGENT_DEFAULT_MODEL=claude-3-sonnet
```

## Provider Tools

The command line offers tools to explore and configure providers:

```bash
# List all available providers
code-agent providers list

# Get configuration help for a specific provider
code-agent config openai
code-agent config aistudio
code-agent config anthropic
code-agent config groq
```

## Model Selection Best Practices

1. **Balance Cost and Performance**:
   - Start with faster, cheaper models for simple tasks
   - Use more powerful models only when needed

2. **Consider Task Complexity**:
   - Simple code explanations: `gemini-2.0-flash`, `gpt-3.5-turbo`
   - Complex architecture design: `gpt-4o`, `claude-3-opus`, `gemini-2.0-pro`

3. **Provider Specialties**:
   - OpenAI: Strong general coding ability
   - Anthropic: Strong reasoning and explanations
   - Groq: Fast inference for open models
   - AI Studio: Balanced performance and cost

4. **Look for Rate Limit Errors**:
   - If hitting rate limits, switch to a different provider
