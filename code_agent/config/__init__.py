# Import directly from the config module
from .config import (
    get_api_key,
    get_config,
)

# Import the specific settings class and functions from its module
from .settings_based_config import (
    DEFAULT_CONFIG_PATH,  # Add default path
    # create_settings_model, # This seems internal, maybe not needed for export
    CodeAgentSettings,  # Import the correct class
    SettingsConfig,  # Import the base config model if needed elsewhere
    build_effective_config,  # Moved from config.py
    initialize_config,  # Moved from config.py
    validate_config,  # Moved from config.py
)

# Define what is exported when using 'from code_agent.config import *'
__all__ = [
    "CodeAgentSettings",  # Export the correct settings class
    "SettingsConfig",  # Export the base config model if needed
    "get_config",  # Added back
    "get_api_key",  # Added back
    "validate_config",  # Export moved function
    "initialize_config",  # Export moved function
    "build_effective_config",  # Export moved function
    # "load_config_from_file", # Removed
    # "create_settings_model", # Removed from export
    "DEFAULT_CONFIG_PATH",  # Export default path
]
