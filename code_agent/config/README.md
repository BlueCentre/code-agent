# Configuration Management

This directory contains the configuration management code for the Code Agent project.

## Overview

There are two implementations of the configuration management system:

1. **Standard Implementation (`config.py`)** - The current production implementation
2. **Pydantic Settings-Based Implementation (`settings_based_config.py`)** - An alternative implementation using pydantic-settings for more robust environment variable handling

## Standard Implementation (`config.py`)

The standard implementation uses a manual approach to load and merge configuration from multiple sources in this priority order:

1. Default values defined in the Pydantic model
2. Configuration file settings
3. Environment variable overrides
4. CLI arguments (highest priority)

It handles validation through Pydantic and provides graceful fallbacks to default values when necessary.

## Pydantic Settings-Based Implementation (`settings_based_config.py`)

This alternative implementation uses `pydantic-settings` to provide more robust environment variable handling. It leverages the built-in features of pydantic-settings such as:

- Automatic environment variable parsing with prefix support
- Custom environment variable mappings
- .env file support
- Nested delimiter support for structured settings

### Key Differences

- The standard implementation requires more manual code for environment variable handling
- The pydantic-settings implementation reduces boilerplate code through its built-in features
- Both implementations maintain the same priority order for configuration sources
- Both implementations provide validation and fallback mechanisms

## Usage

Both implementations expose the same API:

```python
from code_agent.config import get_config, initialize_config

# Initialize configuration (should be done once at application startup)
initialize_config(
    config_file_path="/path/to/config.yaml",  # Optional
    cli_provider="openai",                     # Optional
    cli_model="gpt-4",                         # Optional
    cli_auto_approve_edits=False,              # Optional
    cli_auto_approve_native_commands=False,    # Optional
)

# Get the configuration
config = get_config()

# Access configuration values
model = config.default_model
openai_key = config.api_keys.openai
```

## Environment Variables

Both implementations support the following environment variables:

- `OPENAI_API_KEY` - OpenAI API key
- `AI_STUDIO_API_KEY` - Google AI Studio API key
- `GROQ_API_KEY` - Groq API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `CODE_AGENT_AUTO_APPROVE_EDITS` - Set to "true" to auto-approve edits
- `CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS` - Set to "true" to auto-approve native commands

## Future Directions

In the future, we may:

1. Migrate fully to the pydantic-settings based implementation
2. Add additional validation and documentation for configuration options
3. Implement dynamic validation with clear error messages
4. Add support for more configuration options and providers
