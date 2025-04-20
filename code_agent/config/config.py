import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

# Configuration management logic will go here
# Placeholder for now
pass

# Define the default config path
DEFAULT_CONFIG_DIR = Path.home() / "code-agent"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "template.yaml"

# --- Pydantic Models for Validation ---


class ApiKeys(BaseModel):
    # Allow extra fields for flexibility with different providers
    class Config:
        extra = "allow"

    openai: Optional[str] = None
    ai_studio: Optional[str] = None
    groq: Optional[str] = None
    anthropic: Optional[str] = None
    # Other keys loaded will be accessible via model_extra


class SettingsConfig(BaseModel):
    default_provider: str = "ai_studio"
    default_model: str = "gemini-1.5-flash"
    api_keys: ApiKeys = Field(default_factory=ApiKeys)
    auto_approve_edits: bool = False
    auto_approve_native_commands: bool = False
    native_command_allowlist: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)


# --- Configuration Loading Logic ---

_config: Optional[SettingsConfig] = None


def load_config_from_file(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration purely from a YAML file, returning a dict."""
    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # If config file doesn't exist, create it from template
    if not config_path.exists():
        create_default_config_file(config_path)
        print(f"Created default configuration file at {config_path}")
        print("Edit this file to add your API keys or set appropriate environment variables.")
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not read config file at {config_path}. Error: {e}")
        return {}


def create_default_config_file(config_path: Path) -> None:
    """Creates a default configuration file from the template."""
    try:
        if TEMPLATE_CONFIG_PATH.exists():
            # Copy from template if it exists
            shutil.copy2(TEMPLATE_CONFIG_PATH, config_path)
        else:
            # Fallback if template doesn't exist
            default_config = {
                "default_provider": "ai_studio",
                "default_model": "gemini-1.5-flash",
                "api_keys": {
                    "ai_studio": None,
                    "openai": None,
                    "groq": None,
                },
                "auto_approve_edits": False,
                "auto_approve_native_commands": False,
                "native_command_allowlist": [],
                "rules": [],
            }
            
            with open(config_path, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"Warning: Could not create default config file at {config_path}. Error: {e}")


def build_effective_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
) -> SettingsConfig:
    """Builds the effective config by layering File > Env > CLI > Defaults."""

    # 1. Start with defaults defined in the Pydantic model
    effective_config_data = SettingsConfig().model_dump()

    # 2. Layer config file settings
    file_config_data = load_config_from_file(config_file_path)
    # Simple merge (consider deep merge for nested dicts like api_keys if needed)
    if isinstance(file_config_data.get("api_keys"), dict):
        # Merge api_keys separately to avoid overwriting entire dict
        effective_config_data["api_keys"].update(file_config_data["api_keys"])
        del file_config_data["api_keys"]  # Remove so it's not overwritten below

    effective_config_data.update(file_config_data)

    # 3. Layer Environment Variable Overrides (Focus on API keys for now)
    # TODO: Use pydantic-settings for more robust env var handling?
    if "OPENAI_API_KEY" in os.environ:
        effective_config_data["api_keys"]["openai"] = os.environ["OPENAI_API_KEY"]
    if "AI_STUDIO_API_KEY" in os.environ:
        effective_config_data["api_keys"]["ai_studio"] = os.environ["AI_STUDIO_API_KEY"]
    if "GROQ_API_KEY" in os.environ:
        effective_config_data["api_keys"]["groq"] = os.environ["GROQ_API_KEY"]
    if "ANTHROPIC_API_KEY" in os.environ:
        effective_config_data["api_keys"]["anthropic"] = os.environ["ANTHROPIC_API_KEY"]
    # Add more provider keys as needed

    # Environment variables for auto-approve flags
    if "CODE_AGENT_AUTO_APPROVE_EDITS" in os.environ:
        effective_config_data["auto_approve_edits"] = (
            os.environ["CODE_AGENT_AUTO_APPROVE_EDITS"].lower() == "true"
        )
    if "CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS" in os.environ:
        effective_config_data["auto_approve_native_commands"] = (
            os.environ["CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS"].lower() == "true"
        )

    # 4. Layer CLI Overrides (Highest priority)
    if cli_provider is not None:
        effective_config_data["default_provider"] = cli_provider
    if cli_model is not None:
        effective_config_data["default_model"] = cli_model
    # Check if CLI flag was explicitly passed (Typer sets it to True/False if present, None otherwise)
    if cli_auto_approve_edits is not None:
        effective_config_data["auto_approve_edits"] = cli_auto_approve_edits
    if cli_auto_approve_native_commands is not None:
        effective_config_data["auto_approve_native_commands"] = (
            cli_auto_approve_native_commands
        )

    # 5. Validate and return the final config object
    try:
        final_config = SettingsConfig(**effective_config_data)
        return final_config
    except ValidationError as e:
        print(f"Error: Invalid effective configuration:\n{e}")
        print("Falling back to default configuration.")
        return SettingsConfig()
    except Exception as e:
        print(f"Error creating final configuration: {e}")
        print("Falling back to default configuration.")
        return SettingsConfig()


def initialize_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
):
    """Initializes the global config singleton with effective settings."""
    global _config
    if _config is None:
        _config = build_effective_config(
            config_file_path=config_file_path,
            cli_provider=cli_provider,
            cli_model=cli_model,
            cli_auto_approve_edits=cli_auto_approve_edits,
            cli_auto_approve_native_commands=cli_auto_approve_native_commands,
        )
    # else: config already initialized


def get_config() -> SettingsConfig:
    """Returns the loaded configuration, raising error if not initialized."""
    if _config is None:
        # This should ideally not happen if initialize_config is called in main
        print(
            "[bold red]Error:[/bold red] Configuration accessed before initialization."
        )
        # Initialize with defaults as a fallback, though this indicates a logic error
        initialize_config()
        # raise RuntimeError("Configuration accessed before initialization. Call initialize_config first.")
    return _config


# --- Helper Functions (Example) ---


def get_api_key(provider: str) -> Optional[str]:
    """Gets the API key for a specific provider from the loaded config."""
    config = get_config()
    # Access keys directly or via model_extra if using Pydantic v2 extra='allow'
    return config.api_keys.model_dump().get(provider)


# Create default config directory if it doesn't exist
# Moved initialization call to cli main
# DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# # Example usage (can be removed later)
# if __name__ == "__main__":
#     print("--- Testing Config Loading --- ")
#     # 1. Initialize with defaults + potential env vars
#     print("\n1. Initializing with defaults + env...")
#     initialize_config()
#     cfg1 = get_config()
#     print(cfg1.model_dump_json(indent=2))
#
#     # 2. Reset and initialize with CLI overrides
#     _config = None # Manually reset for testing
#     print("\n2. Initializing with CLI overrides...")
#     initialize_config(
#         cli_provider="cli_groq",
#         cli_model="cli_llama",
#         cli_auto_approve_edits=True # Test override
#     )
#     cfg2 = get_config()
#     print(cfg2.model_dump_json(indent=2))
#     print(f"Provider should be cli_groq: {cfg2.default_provider}")
#     print(f"Model should be cli_llama: {cfg2.default_model}")
#     print(f"Auto Approve Edits should be True: {cfg2.auto_approve_edits}")
#     print(f"OpenAI Key from config/env: {get_api_key('openai')}")
