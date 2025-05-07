# Agent Templates

This directory contains the template system for the Code Agent CLI.

## Overview

The template system allows for creating agents with different provider configurations through a flexible, YAML-based approach. Templates are stored in the `agents/` directory and loaded dynamically.

## Available Templates

The following templates are currently available:

- `gemini_api.yaml` - Google AI Studio (Gemini) API-based agent
- `vertex_ai.yaml` - Google Cloud Vertex AI-based agent
- `ollama.yaml` - Local Ollama-based agent
- `openai.yaml` - OpenAI (GPT) API-based agent
- `anthropic.yaml` - Anthropic (Claude) API-based agent
- `groq.yaml` - Groq API-based agent

## Creating a New Template

To create a new template, add a YAML file to the `agents/` directory with the following structure:

```yaml
name: "Template Name"
description: "Description of the template"
id: "unique_template_id"
default_model: "default-model-name"
requires:
  - key_name: "ENV_VAR_NAME"
  # Add more required parameters as needed
files:
  # Define files to be created
  agent.py: |
    # File content with {variables} for substitution
    from google.adk.agents import Agent
    
    root_agent = Agent(
        model='{model_name}',
        name='root_agent',
        description='A helpful assistant.',
        instruction='Answer user questions',
    )
  __init__.py: |
    from . import agent
  .env: |
    # Environment variables
    KEY_NAME={key_name}
setup_instructions: |
  Your agent has been created.
  
  To use your agent:
    code-agent run "Your query here" {agent_folder}
```

## Parameters

- `name`: Display name for the template
- `description`: Brief description of what this template provides
- `id`: Unique identifier (used with --template flag)
- `default_model`: Default model to use with this template
- `requires`: List of parameters that need to be collected from the user
- `files`: Dict of filename -> content for files to generate
- `setup_instructions`: Message shown to the user after successful creation

## Variable Substitution

In file content and setup instructions, you can use `{variable}` syntax to substitute values collected from the user:

- `{model_name}`: The chosen model 
- `{agent_folder}`: The folder where the agent is created
- Any parameter specified in the `requires` section

## Using Templates

Templates can be used through the CLI:

```bash
# Show available templates
code-agent create --list

# Create an agent with a specific template
code-agent create my_agent --template ollama

# Create with interactive selection
code-agent create my_agent
``` 