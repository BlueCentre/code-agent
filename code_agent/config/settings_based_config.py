"""
This module provides a settings-based configuration system for the code-agent.

It uses pydantic-settings to handle environment variables and configuration files.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich import print as rich_print
from typing_extensions import Annotated

logger = logging.getLogger(__name__)  # Ensure logger is defined at module level

# Define the default config path
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "code-agent"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "config_template.yaml"

# Define a specific type for verbosity levels for clarity
VerbosityLevel = Annotated[int, Field(ge=0, le=3)]

# --- Pydantic Models for Validation ---


class ApiKeys(BaseModel):
    """API keys for different LLM providers."""

    openai: Optional[str] = None
    ai_studio: Optional[str] = None
    groq: Optional[str] = None
    anthropic: Optional[str] = None

    # Allow extra fields for new providers
    model_config = {"extra": "allow"}


class SecuritySettings(BaseModel):
    """Configuration for security-related features."""

    # Path security settings
    path_validation: bool = Field(
        default=True,
        description="Enable path validation for file operations to prevent path traversal attacks",
    )
    workspace_restriction: bool = Field(
        default=True,
        description="Restrict file operations to the current workspace directory",
    )

    # Command security settings
    command_validation: bool = Field(
        default=True,
        description="Enable command validation to prevent execution of dangerous commands",
    )

    # Risky command patterns
    risky_command_patterns: List[str] = Field(
        default_factory=list,
        description="List of regex patterns for commands that are risky but allowed with warning",
    )

    # Web search setting removed - using ADK's google_search instead


class FileOperationsSettings(BaseModel):
    """Configuration for file operation features."""

    class ReadFileSettings(BaseModel):
        """Settings for the read_file tool."""

        max_file_size_kb: int = Field(
            default=1024,  # 1MB default
            description="Maximum file size in KB that can be read without pagination",
        )
        max_lines: int = Field(
            default=1000,
            description="Maximum number of lines to read at once when using pagination",
        )
        enable_pagination: bool = Field(
            default=False,
            description="Whether to enable pagination for reading large files",
        )

    read_file: ReadFileSettings = Field(
        default_factory=ReadFileSettings,
        description="Settings for the read_file tool",
    )


class NativeCommandSettings(BaseModel):
    """Settings for native command execution."""

    default_timeout: Optional[int] = Field(
        default=None,
        description="Default timeout in seconds for native commands (None means no timeout)",
    )
    default_working_directory: Optional[str] = Field(
        default=None,
        description="Default working directory for native commands (None means current directory)",
    )


class LLMSettings(BaseModel):
    provider: Optional[str] = Field(None, description="LLM provider name (e.g., openai, ai_studio, groq)")
    model: Optional[str] = Field(None, description="Specific LLM model name")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="LLM temperature (0.0-1.0)")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens for LLM response")
    api_key_env_var: Optional[str] = Field(None, description="Environment variable name for the API key")


class CodeAgentSettings(BaseSettings):
    """Defines the application settings model."""

    # --- Add Application Identification --- #
    app_name: str = Field("code_agent_cli", description="Application name used for session identification.")
    user_id: str = Field("cli_user", description="Default user ID used for session identification.")
    # --- End Application Identification --- #

    config_file_path: Path = Field(default_factory=lambda: DEFAULT_CONFIG_PATH, description="Path to the main YAML configuration file.")
    default_provider: Optional[str] = Field("ai_studio", description="Default LLM provider.")
    default_model: Optional[str] = Field("gemini-2.0-flash", description="Default LLM model.")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Default LLM temperature.")
    max_tokens: Optional[int] = Field(1000, gt=0, description="Default maximum tokens.")
    max_tool_calls: int = Field(default=10, description="Maximum number of consecutive tool calls allowed before stopping.")
    verbosity: VerbosityLevel = Field(
        1,  # Default to NORMAL
        description="Verbosity level (0=QUIET, 1=NORMAL, 2=VERBOSE, 3=DEBUG).",
    )
    sessions_dir: Path = Field(default_factory=lambda: DEFAULT_CONFIG_DIR / "sessions", description="Directory to store saved conversation sessions.")
    default_agent_path: Optional[Path] = Field(None, description="Default path to the agent module/package if not provided via CLI.")
    # Placeholder for provider-specific settings if needed later
    providers: Dict[str, LLMSettings] = Field(default_factory=dict, description="Provider-specific configurations (e.g., API keys)")

    # --- Add Nested Settings Models and other missing fields ---
    api_keys: ApiKeys = Field(default_factory=ApiKeys, description="API keys for LLM providers.")
    security: SecuritySettings = Field(default_factory=SecuritySettings, description="Security-related settings.")
    file_operations: FileOperationsSettings = Field(default_factory=FileOperationsSettings, description="Settings for file operations.")
    native_commands: NativeCommandSettings = Field(default_factory=NativeCommandSettings, description="Settings for native command execution.")
    auto_approve_edits: bool = Field(False, description="Automatically approve file edit operations.")
    auto_approve_native_commands: bool = Field(False, description="Automatically approve native command execution.")
    native_command_allowlist: List[str] = Field(default_factory=list, description="List of native commands allowed without confirmation.")
    rules: List[str] = Field(default_factory=list, description="Custom rules (currently unused).")
    # --- End Nested Settings ---

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_prefix="CODE_AGENT_",
        env_nested_delimiter="__",
        case_sensitive=False,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra="ignore",  # Ignore extra fields from config file
    )

    # --- Validators (Keep simple ones, remove complex ones for now) ---
    @field_validator("temperature")
    @classmethod
    def check_temperature(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def check_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Max tokens must be positive")
        return v

    # --- Add back validate_dynamic as a stub --- #
    def validate_dynamic(self, verbose: bool = False) -> bool:
        """Placeholder dynamic validation method."""
        # For now, this does nothing and assumes validity
        # We can add back more complex validation later if needed.
        logger.debug("Skipping dynamic validation (using stub method).")
        return True


# --- Configuration Loading Logic ---

_config: Optional[CodeAgentSettings] = None


def build_effective_config(
    config_file_path: Path = DEFAULT_CONFIG_PATH,
    cli_provider: Optional[str] = None,
    cli_model: Optional[str] = None,
    cli_agent_path: Optional[Path] = None,
    cli_auto_approve_edits: Optional[bool] = None,
    cli_auto_approve_native_commands: Optional[bool] = None,
    cli_log_level: Optional[str] = None,
    cli_verbose: Optional[bool] = None,
) -> CodeAgentSettings:
    """
    Builds the effective configuration by layering sources:
    1. Default values from CodeAgentSettings model.
    2. Values from environment variables (handled by BaseSettings).
    3. Values from the YAML configuration file.
    4. Values from CLI arguments.
    """

    # 1 & 2: Load settings from defaults and environment variables
    try:
        # Pydantic-settings automatically loads from env vars based on model_config
        settings = CodeAgentSettings(
            # Pass config_file_path explicitly if needed by BaseSettings, though it usually handles it via env/defaults
            # config_file_path=config_file_path
        )
    except ValidationError as e:
        logger.error(f"Error loading base settings or environment variables: {e}")
        # Depending on desired behavior, either exit or continue with defaults
        settings = CodeAgentSettings()  # Fallback to pure defaults

    # 3: Load settings from the specified YAML file
    file_values = load_config_from_file(config_file_path)

    # 4: Merge file values into the settings object (carefully)
    # Pydantic models are immutable by default, so we create a new dict and then a new model instance
    merged_data = settings.model_dump()  # Start with env/default values

    # Custom deep update logic needed because model_dump doesn't perfectly handle nested BaseSettings
    def deep_update(target: Dict, source: Dict) -> Dict:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                # Key exists in both and both values are dicts, recurse
                deep_update(target[key], value)
            # elif key in target: # REMOVE THIS CHECK - Allow adding/overwriting keys
            else:
                # Overwrite target key with source value (or add if not present)
                target[key] = value
            # else: ignore keys from file not present in the model (or handle as extra if configured)
        return target

    merged_data = deep_update(merged_data, file_values)

    # Create settings instance incorporating file values over env/defaults
    try:
        settings = CodeAgentSettings(**merged_data)
    except ValidationError as e:
        logger.error(f"Error validating merged settings from file ({config_file_path}): {e}")
        # Fallback or re-raise depending on desired strictness
        # settings = CodeAgentSettings() # Or use the previous settings instance

    # 5: Apply CLI overrides (highest priority)
    cli_overrides: Dict[str, Any] = {}
    if cli_provider is not None:
        cli_overrides["default_provider"] = cli_provider
    if cli_model is not None:
        cli_overrides["default_model"] = cli_model
    if cli_agent_path is not None:
        cli_overrides["default_agent_path"] = cli_agent_path
    if cli_auto_approve_edits is not None:
        cli_overrides["auto_approve_edits"] = cli_auto_approve_edits
    if cli_auto_approve_native_commands is not None:
        cli_overrides["auto_approve_native_commands"] = cli_auto_approve_native_commands

    # Handle verbosity CLI flags (log_level takes precedence)
    if cli_log_level:
        level_map = {"DEBUG": 3, "INFO": 2, "WARNING": 1, "ERROR": 0, "QUIET": 0}
        cli_overrides["verbosity"] = level_map.get(cli_log_level.upper(), settings.verbosity)
    elif cli_verbose:
        # Only apply --verbose if --log-level wasn't given
        cli_overrides["verbosity"] = max(settings.verbosity, 2)  # Set to at least VERBOSE (2)

    # Create the final settings object by applying CLI overrides
    if cli_overrides:
        final_data = settings.model_dump()
        final_data.update(cli_overrides)
        try:
            final_settings = CodeAgentSettings(**final_data)
        except ValidationError as e:
            logger.error(f"Error validating settings after applying CLI overrides: {e}")
            # Fallback to settings before CLI overrides
            final_settings = settings
    else:
        final_settings = settings

    logger.debug(f"Effective configuration loaded: {final_settings.model_dump()}")
    return final_settings


# --- Utility functions for Pydantic model manipulation ---


def create_settings_model(config_data: Dict) -> CodeAgentSettings:
    """Creates a CodeAgentSettings model instance from a dictionary."""
    try:
        return CodeAgentSettings(**config_data)
    except ValidationError as e:
        rich_print(f"[bold red]Error validating configuration data:[/bold red]\n{e}")
        raise


def settings_to_dict(settings: CodeAgentSettings) -> Dict:
    """Converts CodeAgentSettings instance back to a dictionary, excluding defaults if desired."""
    # Use model_dump with exclude_defaults=True if you want to only save non-default values
    # return settings.model_dump(exclude_defaults=False, mode='json') # mode='json' helps with Path types
    # For saving, often better to include defaults unless specifically trimming the file
    return settings.model_dump(mode="json")  # Use mode='json' for serialization compatibility (e.g., Path)


# --- File Handling ---


def load_config_from_file(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.exists():
        # logger.info(f"Configuration file not found at {config_path}. Using defaults/env vars.")
        # Attempt to create a default one if the template exists
        create_default_config_file(config_path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            return config_data if config_data else {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {config_path}: {e}")
        return {}
    except OSError as e:
        logger.error(f"Error reading file {config_path}: {e}")
        return {}


def create_default_config_file(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Creates a default configuration file from the template if it doesn't exist."""
    if config_path.exists():
        # logger.debug(f"Config file {config_path} already exists.")
        return

    if not TEMPLATE_CONFIG_PATH.exists():
        logger.warning(f"Config template {TEMPLATE_CONFIG_PATH} not found. Cannot create default config.")
        return

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATE_CONFIG_PATH, config_path)
        logger.info(f"Created default configuration file at {config_path}")
    except OSError as e:
        logger.error(f"Error creating default config file {config_path}: {e}")


def get_config() -> CodeAgentSettings:
    """Returns the current configuration settings, loading if necessary."""
    global _config
    if _config is None:
        # logger.debug("Configuration not loaded, initializing...")
        _config = build_effective_config()  # Load using default path
        # logger.debug(f"Configuration loaded: {_config.model_dump()}")
    # else:
    # logger.debug("Returning cached configuration.")
    return _config


def initialize_config(**cli_args) -> CodeAgentSettings:
    """Loads or reloads the configuration using build_effective_config, applying CLI args."""
    global _config
    # logger.debug(f"Initializing/Reloading configuration with CLI args: {cli_args}")
    # Map relevant CLI args to build_effective_config parameters
    build_args = {
        "config_file_path": cli_args.get("config_file", DEFAULT_CONFIG_PATH),
        "cli_provider": cli_args.get("provider"),
        "cli_model": cli_args.get("model"),
        "cli_agent_path": cli_args.get("agent_path"),
        "cli_auto_approve_edits": cli_args.get("auto_approve_edits"),
        "cli_auto_approve_native_commands": cli_args.get("auto_approve_native_commands"),
        "cli_log_level": cli_args.get("log_level"),
        "cli_verbose": cli_args.get("verbose"),
    }
    _config = build_effective_config(**build_args)
    # logger.debug(f"Configuration initialized/reloaded: {_config.model_dump()}")
    return _config


def get_api_key(provider_name: str) -> Optional[str]:
    """Gets the API key for a specific provider from the config."""
    config = get_config()
    api_keys_obj = config.api_keys
    key = getattr(api_keys_obj, provider_name, None)
    if not key:
        # Fallback check: Maybe it's stored as an extra attribute if loaded from env directly?
        # This shouldn't be necessary if env_mapping is used correctly in BaseSettings
        key = api_keys_obj.model_extra.get(provider_name) if api_keys_obj.model_extra else None

    if not key:
        logger.warning(f"API key for provider '{provider_name}' not found in configuration.")
        # Optionally, prompt the user or guide them to set it.
    return key
