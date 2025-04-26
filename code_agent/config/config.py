from pathlib import Path
from typing import Optional

from rich import print as rich_print

# Import directly from settings_based_config
from code_agent.config.settings_based_config import (
    DEFAULT_CONFIG_PATH,  # Import path constant
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

_config: Optional[CodeAgentSettings] = None


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
        raise RuntimeError("Configuration failed to initialize.")
    return _config


def get_api_key(provider: str) -> Optional[str]:
    """Get the API key for a specific provider."""
    config = get_config()
    # Access keys directly using vars() or getattr for safety
    return getattr(config.api_keys, provider, None)


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
