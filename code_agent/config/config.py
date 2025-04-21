import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from rich import print as rich_print

from code_agent.config.settings_based_config import (
    CodeAgentSettings,
    create_settings_model,
)
from code_agent.tools.error_utils import format_config_error

# Configuration management logic will go here
# Placeholder for now
pass

# Define the default config path
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "code-agent"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "template.yaml"

# --- Configuration Loading Logic ---

_config: Optional[CodeAgentSettings] = None


def load_config_from_file(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    config_data = {}

    try:
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        else:
            # Create default config file if it doesn't exist
            rich_print(f"[yellow]Config file not found at {config_path}.[/yellow]")
            rich_print("[yellow]Creating default configuration file...[/yellow]")
            create_default_config_file(config_path)
            # Try loading again
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
            else:
                rich_print("[bold red]Could not create config file.[/bold red]")
    except (yaml.YAMLError, OSError) as e:
        error_message = format_config_error(e, config_item=str(config_path))
        rich_print(f"[bold red]{error_message}[/bold red]")
        rich_print("[yellow]Using default configuration.[/yellow]")

    return config_data


def create_default_config_file(config_path: Path) -> None:
    """Creates a default configuration file from the template."""
    try:
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if TEMPLATE_CONFIG_PATH.exists():
            # Copy from template if it exists
            shutil.copy2(TEMPLATE_CONFIG_PATH, config_path)
        else:
            # Fallback if template doesn't exist
            default_config = {
                "default_provider": "ai_studio",
                "default_model": "gemini-2.0-flash",
                "api_keys": {
                    "ai_studio": None,
                    "openai": None,
                    "groq": None,
                },
                "auto_approve_edits": False,
                "auto_approve_native_commands": False,
                "native_command_allowlist": [],
                "security": {
                    "path_validation": True,
                    "workspace_restriction": True,
                    "command_validation": True,
                },
                "rules": [],
            }

            with open(config_path, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"Warning: Could not create default config file at {config_path}. " f"Error: {e}")


def build_effective_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
) -> CodeAgentSettings:
    """Builds the effective config by layering File > Env > CLI > Defaults."""

    # 1. Load configuration data from file
    file_config_data = load_config_from_file(config_file_path)

    # 2. Apply environment variables (focus on API keys for now)
    if "api_keys" not in file_config_data:
        file_config_data["api_keys"] = {}

    # Provider API keys
    for provider, env_var in [("openai", "OPENAI_API_KEY"), ("ai_studio", "AI_STUDIO_API_KEY"), ("groq", "GROQ_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")]:
        if env_var in os.environ:
            file_config_data["api_keys"][provider] = os.environ[env_var]

    # Environment variables for auto-approve flags
    if "CODE_AGENT_AUTO_APPROVE_EDITS" in os.environ:
        file_config_data["auto_approve_edits"] = os.environ["CODE_AGENT_AUTO_APPROVE_EDITS"].lower() == "true"
    if "CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS" in os.environ:
        file_config_data["auto_approve_native_commands"] = os.environ["CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS"].lower() == "true"

    # Handle security settings from environment
    if "security" not in file_config_data:
        file_config_data["security"] = {}

    for setting in ["path_validation", "workspace_restriction", "command_validation"]:
        env_var = f"CODE_AGENT_SECURITY_{setting.upper()}"
        if env_var in os.environ:
            file_config_data["security"][setting] = os.environ[env_var].lower() == "true"

    # 3. Apply CLI overrides
    if cli_provider is not None:
        file_config_data["default_provider"] = cli_provider
    if cli_model is not None:
        file_config_data["default_model"] = cli_model
    if cli_auto_approve_edits is not None:
        file_config_data["auto_approve_edits"] = cli_auto_approve_edits
    if cli_auto_approve_native_commands is not None:
        file_config_data["auto_approve_native_commands"] = cli_auto_approve_native_commands

    # 4. Create and return the settings model
    return create_settings_model(file_config_data)


def initialize_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
    validate: bool = True,
) -> None:
    """Initialize the global configuration singleton."""
    global _config

    _config = build_effective_config(
        config_file_path,
        cli_provider,
        cli_model,
        cli_auto_approve_edits,
        cli_auto_approve_native_commands,
    )

    if validate:
        validate_config(verbose=False)


def get_config() -> CodeAgentSettings:
    """Get the global configuration singleton."""
    global _config
    if _config is None:
        initialize_config()
    return _config


def get_api_key(provider: str) -> Optional[str]:
    """Get the API key for a specific provider."""
    config = get_config()
    return vars(config.api_keys).get(provider)


def validate_config(verbose: bool = False) -> bool:
    """Validate the configuration and print any warnings or errors."""
    config = get_config()
    return config.validate_dynamic(verbose=verbose)


# For testing
if __name__ == "__main__":
    config = get_config()
    rich_print("Effective Configuration:")
    rich_print(config.model_dump())
    validate_config(verbose=True)
