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

    # Web search settings
    enable_web_search: bool = Field(
        default=True,
        description="Enable web search functionality to retrieve information from the internet",
    )


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
        description="Custom rules to influence the agent's behavior",
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
    auto_approve_edits: bool = False
    auto_approve_native_commands: bool = False
    native_command_allowlist: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)

    # Add file_operations settings
    file_operations: FileOperationsSettings = Field(default_factory=FileOperationsSettings)

    # Add native command settings
    native_commands: NativeCommandSettings = Field(default_factory=NativeCommandSettings)

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
) -> SettingsConfig:
    """Builds the effective config by layering File > Env > CLI > Defaults.

    Using pydantic-settings for robust environment variable handling.

    Args:
        config_file_path: Path to the config file
        cli_provider: Provider override from CLI
        cli_model: Model override from CLI
        cli_auto_approve_edits: Auto-approve edits override from CLI
        cli_auto_approve_native_commands: Auto-approve commands override from CLI

    Returns:
        SettingsConfig instance with all settings applied
    """
    try:
        # 1. Load file settings as base values
        file_config_data = load_config_from_file(config_file_path)

        # 2. Preprocess file data to handle potential None values in lists
        if "native_command_allowlist" in file_config_data and file_config_data["native_command_allowlist"] is None:
            file_config_data["native_command_allowlist"] = []
        if "rules" in file_config_data and file_config_data["rules"] is None:
            file_config_data["rules"] = []

        # 3. Create settings - this will automatically load values from environment variables
        # based on the model_config settings
        settings = SettingsConfig(**file_config_data)

        # 4. Apply CLI overrides (highest priority)
        if cli_provider is not None:
            settings.default_provider = cli_provider
        if cli_model is not None:
            settings.default_model = cli_model
        if cli_auto_approve_edits is not None:
            settings.auto_approve_edits = cli_auto_approve_edits
        if cli_auto_approve_native_commands is not None:
            settings.auto_approve_native_commands = cli_auto_approve_native_commands

        return settings

    except ValidationError as e:
        print(f"Error: Invalid configuration:\n{e}")
        print("Falling back to default configuration.")
        return SettingsConfig()
    except Exception as e:
        print(f"Error creating configuration: {e}")
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
        print("[bold red]Error:[/bold red] Configuration accessed before initialization.")
        # Initialize with defaults as a fallback, though this indicates a logic error
        initialize_config()
    return _config


# --- Helper Functions (Example) ---


def get_api_key(provider: str) -> Optional[str]:
    """Gets the API key for a specific provider from the loaded config."""
    config = get_config()
    # Access keys directly using vars() instead of model_dump
    return vars(config.api_keys).get(provider)


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
