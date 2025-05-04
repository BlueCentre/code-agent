# Import directly from the config module
from .config import (
    DEFAULT_CONFIG_PATH,  # Import path from config.py (assuming it's defined there or imported)
    CodeAgentSettings,  # Import the main settings class from config.py (assuming it's defined/imported there)
    get_api_key,
    get_config,
    initialize_config,  # Import from config.py
    validate_config,  # Import from config.py
)

# Import only necessary things from settings_based_config if needed elsewhere,
# but avoid re-exporting the core functions from here.
from .settings_based_config import (
    # SettingsConfig, # Only if needed directly elsewhere
    ApiKeys,  # Might be needed for type hints
    build_effective_config,  # Keep this as it seems to be the core builder logic
)

# Define what is exported when using 'from code_agent.config import *'
__all__ = [
    "CodeAgentSettings",  # Export the correct settings class
    # "SettingsConfig", # Export the base config model only if needed
    "get_config",
    "get_api_key",
    "validate_config",
    "initialize_config",
    "build_effective_config",  # Keep exporting the builder
    "DEFAULT_CONFIG_PATH",
    "ApiKeys",  # Export ApiKeys if needed for type hinting
]
