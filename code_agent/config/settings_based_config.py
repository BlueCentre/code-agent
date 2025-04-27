import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich import print as rich_print

from code_agent.config.validation import validate_config

# Define the default config path
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "code-agent"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "template.yaml"

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


class CodeAgentSettings(BaseModel):
    """Main configuration settings for the code agent."""

    # Default provider and model
    default_provider: str = Field(
        default="ai_studio",
        description="Default LLM provider to use",
    )
    default_model: str = Field(
        default="gemini-2.0-flash",
        description="Default model to use for the selected provider",
    )

    # API Keys
    api_keys: ApiKeys = Field(
        default_factory=ApiKeys,
        description="API keys for different LLM providers",
    )

    # Verbosity setting
    verbosity: int = Field(
        default=1,
        description="Output verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)",
    )

    # Auto-approve settings
    auto_approve_edits: bool = Field(
        default=False,
        description="Auto-approve file edits without confirmation",
    )
    auto_approve_native_commands: bool = Field(
        default=False,
        description="Auto-approve command execution without confirmation",
    )

    # Command security
    native_command_allowlist: List[str] = Field(
        default_factory=list,
        description="List of command prefixes that are allowed without confirmation",
    )

    # Native command settings
    native_commands: NativeCommandSettings = Field(
        default_factory=NativeCommandSettings,
        description="Settings for native command execution",
    )

    # Security settings
    security: SecuritySettings = Field(
        default_factory=SecuritySettings,
        description="Security-related configuration options",
    )

    # File operations settings
    file_operations: FileOperationsSettings = Field(
        default_factory=FileOperationsSettings,
        description="File operation configuration options",
    )

    # Agent rules
    rules: List[str] = Field(
        default_factory=list,
        description="Custom rules to influence the agent\'s behavior",
    )

    # Add max_tokens setting here as well to match SettingsConfig and ensure it's a known field
    max_tokens: int = Field(
        default=1000,
        description="Maximum number of tokens for the LLM response",
    )

    # Add max_tool_calls setting
    max_tool_calls: int = Field(default=10, description="Maximum number of consecutive tool calls allowed before stopping.")

    # Temperature setting
    temperature: float | None = Field(
        default=0.7,
        description="Temperature for the LLM model",
    )

    # User-specific configurations
    user_id: Optional[str] = None
    auto_approve_edit: bool = False  # Added new setting

    # Tool-specific configurations
    tool_schema: Optional[dict[str, Any]] = None

    # LiteLLM Additional Parameters
    additional_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional keyword arguments to pass to litellm.completion",
    )

    # Other fields from config can be added as needed
    model_config = {"extra": "allow"}

    def validate_dynamic(self, verbose: bool = False) -> bool:
        """
        Perform dynamic validation beyond basic Pydantic validation.

        This method checks:
        1. Provider-specific model compatibility
        2. API key formats
        3. Command allowlist patterns
        4. Security configuration warnings

        Args:
            verbose: Whether to print validation results

        Returns:
            True if valid (may have warnings), False if invalid
        """
        result = validate_config(self)

        if verbose:
            if result.errors:
                rich_print(f"[bold red]Found {len(result.errors)} configuration error(s):[/bold red]")
                for i, error in enumerate(result.errors, 1):
                    rich_print(f"[red]{i}. {error}[/red]")

            if result.warnings:
                rich_print(f"[bold yellow]Found {len(result.warnings)} configuration warning(s):[/bold yellow]")
                for i, warning in enumerate(result.warnings, 1):
                    rich_print(f"[yellow]{i}. {warning}[/yellow]")

            if not result.errors and not result.warnings:
                rich_print("[bold green]✓ Configuration is valid.[/bold green]")
            elif not result.errors:
                rich_print("[bold green]✓ Configuration is valid[/bold green] [yellow](with warnings)[/yellow]")

        return result.valid


class SettingsConfig(BaseSettings):
    """Configuration settings for code-agent using pydantic-settings.

    This implementation leverages pydantic-settings for more robust
    environment variable handling.
    """

    # Default provider and model
    default_provider: str = "ai_studio"
    default_model: str = "gemini-2.0-flash"
    api_keys: ApiKeys = Field(default_factory=ApiKeys)

    # Verbosity setting
    verbosity: int = Field(
        default=1,
        description="Output verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)",
    )

    auto_approve_edits: bool = False
    auto_approve_native_commands: bool = False
    native_command_allowlist: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)

    # Add file_operations settings
    file_operations: FileOperationsSettings = Field(default_factory=FileOperationsSettings)

    # Add native command settings
    native_commands: NativeCommandSettings = Field(default_factory=NativeCommandSettings)

    # Add max_tool_calls setting here as well
    max_tool_calls: int = Field(default=10, description="Maximum number of consecutive tool calls allowed before stopping.")

    # Temperature setting
    temperature: float | None = Field(
        default=0.7,
        description="Temperature for the LLM model",
    )

    # Add max_tokens setting here for env var loading
    max_tokens: int = Field(
        default=1000, # Default can live here or be overridden by CodeAgentSettings default
        description="Maximum number of tokens for the LLM response",
    )

    # Environment variable mapping configuration
    model_config = SettingsConfigDict(
        env_prefix="CODE_AGENT_",
        env_nested_delimiter="__",
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
        # Special mappings for API keys that don't follow the prefix pattern
        env_mapping={
            "api_keys.openai": "OPENAI_API_KEY",
            "api_keys.ai_studio": "AI_STUDIO_API_KEY",
            "api_keys.groq": "GROQ_API_KEY",
            "api_keys.anthropic": "ANTHROPIC_API_KEY",
        },
    )


# --- Configuration Loading Logic ---

_config: Optional[SettingsConfig] = None


def load_config_from_file(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration purely from a YAML file, returning a dict."""
    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for config at old location (~/.code-agent/config.yaml) and migrate if needed
    old_config_dir = Path.home() / "code-agent"
    old_config_path = old_config_dir / "config.yaml"
    if old_config_path.exists() and not config_path.exists():
        try:
            print(f"Migrating config from {old_config_path} to {config_path}")
            # Copy old config to new location
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_config_path, config_path)
            print(f"Successfully migrated configuration to {config_path}")
        except Exception as e:
            print(f"Warning: Could not migrate config. Error: {e}")

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
                "default_model": "gemini-2.0-flash",
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
) -> CodeAgentSettings:
    """Builds the effective configuration by layering sources:
    Defaults < Config File < Environment Variables < CLI Arguments.
    """

    # Helper for deep merging dictionaries (remains the same)
    def deep_update(target: Dict, source: Dict) -> Dict:
        for key, value in source.items():
            # Filter out None values from source unless the key doesn't exist in target
            if value is not None or key not in target:
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    deep_update(target[key], value)
                else:
                    target[key] = value
        return target

    # 1. Load defaults from CodeAgentSettings
    effective_data = CodeAgentSettings().model_dump()

    # 2. Load config file data and merge
    settings_file_data = load_config_from_file(config_file_path)
    effective_data = deep_update(effective_data, settings_file_data)

    # 3. Load environment variables using SettingsConfig and merge
    # Let ValidationError propagate if env vars are invalid
    env_settings = SettingsConfig()  # Loads from .env and env vars
    env_data = env_settings.model_dump(exclude_unset=True)
    # Special handling for potentially empty nested dicts like api_keys
    if "api_keys" in env_data and not env_data["api_keys"]:
        del env_data["api_keys"]  # Don't merge empty dict over existing keys

    effective_data = deep_update(effective_data, env_data)

    # 4. Prepare CLI overrides (only non-None values)
    cli_overrides = {
        "default_provider": cli_provider,
        "default_model": cli_model,
        "auto_approve_edits": cli_auto_approve_edits,
        "auto_approve_native_commands": cli_auto_approve_native_commands,
    }
    cli_overrides = {k: v for k, v in cli_overrides.items() if v is not None}

    # 5. Merge CLI overrides
    effective_data = deep_update(effective_data, cli_overrides)

    # 6. Create the final CodeAgentSettings object
    try:
        final_settings = create_settings_model(effective_data)
    except ValidationError as e:
        print(f"Validation Error creating final CodeAgentSettings from merged config: {e}")
        print("Merged data passed to create_settings_model:")
        try:
            import json

            print(json.dumps(effective_data, indent=2, default=str))
        except Exception:
            print("Could not serialize merged data to JSON.")  # Fallback
            print(effective_data)
        raise

    return final_settings


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
        print("[bold red]Error:[/bold red] Configuration accessed before initialization.")
        # Initialize with defaults as a fallback, though this indicates a logic error
        initialize_config()
    return _config


# --- Helper Functions (Example) ---


def get_api_key(provider: str) -> Optional[str]:
    """Gets the API key for a specific provider from the loaded config."""
    config = get_config()
    api_keys_obj = config.api_keys

    # 1. Try direct attribute access (for defined fields)
    try:
        key = getattr(api_keys_obj, provider, None)
        if key is not None:
            return key
    except AttributeError:
        pass # Field not explicitly defined, proceed to check extras

    # 2. Fallback: Check extra fields via model_dump()
    # Use exclude_unset=True to include all fields, even defaults if needed
    # Use exclude_none=False if you want to differentiate between unset and set-to-None
    try:
        # Ensure api_keys_obj is an ApiKeys instance before calling model_dump
        if isinstance(api_keys_obj, ApiKeys):
            keys_dict = api_keys_obj.model_dump(exclude_unset=True, exclude_none=True)
            return keys_dict.get(provider)
        else:
            # Handle case where api_keys_obj is None or not the expected type
            return None
    except Exception:
        # Handle potential errors during model_dump or if it's not a dict
        return None


def create_settings_model(config_data: Dict) -> CodeAgentSettings:
    """
    Create a settings model from a dictionary.

    Args:
        config_data: Dictionary containing configuration data.

    Returns:
        A CodeAgentSettings instance.
    """
    # Handle the security section specifically
    if "security" not in config_data:
        config_data["security"] = {}

    # Ensure we have security settings even if the config doesn't
    security_data = config_data.get("security", {})
    if not isinstance(security_data, dict):
        security_data = {}

    # Set default values if not present
    for field in ["path_validation", "workspace_restriction", "command_validation"]:
        if field not in security_data:
            security_data[field] = True

    config_data["security"] = security_data

    return CodeAgentSettings(**config_data)


# Function to convert settings model back to dict for saving
def settings_to_dict(settings: CodeAgentSettings) -> Dict:
    """
    Convert a settings model to a dictionary.

    Args:
        settings: A CodeAgentSettings instance.

    Returns:
        Dictionary representation of the settings.
    """
    settings_dict = settings.model_dump(exclude_none=True)

    # Handle API keys specially to avoid saving null values
    if "api_keys" in settings_dict:
        api_keys = settings_dict["api_keys"]
        settings_dict["api_keys"] = {k: v for k, v in api_keys.items() if v is not None}

    return settings_dict
