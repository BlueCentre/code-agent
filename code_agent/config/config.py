from pathlib import Path
from typing import Optional

from rich import print as rich_print

# Import directly from settings_based_config
from code_agent.config.settings_based_config import (
    DEFAULT_CONFIG_PATH,  # Import path constant
    ApiKeys,
    # Rename to avoid conflict if needed
    CodeAgentSettings,
    build_effective_config,  # Import the correct builder
)

# Configuration management logic will go here
# Placeholder for now
pass

# Define the default config path
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "code-agent"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "template.yaml"

# --- Centralized Configuration Access ---

# Global configuration singleton
# _config: Optional[SettingsConfig] = None # Old type
_config: Optional[CodeAgentSettings] = None  # Correct type


def initialize_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
    validate: bool = True,  # Keep validate flag
) -> None:
    """Initialize the global configuration singleton using the effective builder."""
    global _config
    if _config is None:
        # Use the builder from settings_based_config
        _config = build_effective_config(
            config_file_path=config_file_path,
            cli_provider=cli_provider,
            cli_model=cli_model,
            cli_auto_approve_edits=cli_auto_approve_edits,
            cli_auto_approve_native_commands=cli_auto_approve_native_commands,
        )
        if validate:
            # Call the validation method on the final CodeAgentSettings object
            _config.validate_dynamic(verbose=False)
    # else: config already initialized


def get_config() -> CodeAgentSettings:
    """Get the global configuration singleton (CodeAgentSettings instance)."""
    global _config
    if _config is None:
        # Initialize with defaults if not already done (e.g., direct call without CLI)
        rich_print("[yellow]Warning: Configuration accessed before explicit initialization. Initializing with defaults.[/yellow]")
        initialize_config()
    # Ensure _config is not None after initialization attempt
    if _config is None:
        # This should only happen if build_effective_config itself failed critically
        raise RuntimeError("Configuration failed to initialize.")
    return _config


def get_api_key(provider: str) -> Optional[str]:
    """Get the API key for a specific provider."""
    config = get_config()
    api_keys_obj = config.api_keys

    # Ensure api_keys_obj is valid before proceeding
    if not isinstance(api_keys_obj, ApiKeys):
        rich_print(
            f"[yellow]Warning: api_keys in config is not an ApiKeys instance (type: {type(api_keys_obj)}). Cannot retrieve key for '{provider}'.[/yellow]"
        )
        return None

    # 1. Try direct attribute access (for defined fields like openai, ai_studio etc.)
    key = getattr(api_keys_obj, provider, None)
    if key is not None:
        return key

    # 2. Fallback: Check if the key exists as an extra field in the model
    #    This handles providers loaded dynamically from config/env vars that are not explicitly defined fields.
    #    Access the underlying __dict__ or use model_extra if available in Pydantic v2 context
    #    Safest approach is often to check model_extra if using Pydantic v2
    #    For simplicity and avoiding potential linter issues with model_dump here too,
    #    we rely on getattr covering both defined and potentially extra fields if loaded correctly.
    #    If getattr returned None, the key is considered missing.

    return None  # Key not found as defined attribute or known extra field


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
