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
TEMPLATE_CONFIG_PATH = Path(__file__).parent / "config_template.yaml"

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

    # Default agent path
    default_agent_path: Optional[Path] = Field(
        default=None,
        description="Default path to the agent module to run with the 'run' command",
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
        description="Custom rules to influence the agent's behavior",
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

    # Default agent path
    default_agent_path: Optional[Path] = None

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
        default=1000,  # Default can live here or be overridden by CodeAgentSettings default
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
    2. Values from the YAML configuration file.
    3. Values from environment variables (via SettingsConfig).
    4. Values explicitly passed via CLI arguments.

    Args:
        config_file_path: Path to the YAML config file.
        cli_provider: Provider specified via CLI.
        cli_model: Model specified via CLI.
        cli_agent_path: Agent path specified via CLI.
        cli_auto_approve_edits: Auto-approve edits flag from CLI.
        cli_auto_approve_native_commands: Auto-approve commands flag from CLI.
        cli_log_level: Log level string from CLI.
        cli_verbose: Verbose flag from CLI.

    Returns:
        The final, effective CodeAgentSettings configuration object.
    """

    # 1. Start with Pydantic model defaults (implicitly handled by model instantiation)

    # 2. Load from YAML file if it exists
    yaml_config: Dict[str, Any] = {}
    if config_file_path.exists():
        yaml_config = load_config_from_file(config_file_path)
    else:
        # If the default config doesn't exist, create it from the template
        if config_file_path == DEFAULT_CONFIG_PATH and TEMPLATE_CONFIG_PATH.exists():
            try:
                create_default_config_file(config_file_path)
                rich_print(f"[green]Created default configuration file at:[/green] {config_file_path}")
                yaml_config = load_config_from_file(config_file_path)
            except Exception as e:
                rich_print(f"[yellow]Warning:[/yellow] Could not create default config file: {e}")

    # 3. Load from environment variables using pydantic-settings
    # We instantiate SettingsConfig which automatically reads env vars based on its definition
    try:
        env_settings = SettingsConfig()
        # Convert env_settings to a dict, excluding unset values to avoid overriding YAML with None
        env_config = env_settings.model_dump(exclude_unset=True)
    except ValidationError as e:
        rich_print(f"[yellow]Warning:[/yellow] Error validating environment variable settings: {e}")
        env_config = {}

    # 4. Prepare CLI overrides
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

    # Determine effective verbosity based on cli_verbose and cli_log_level
    # - cli_verbose=True sets verbosity to 2 (VERBOSE) if not already higher
    # - cli_log_level sets verbosity based on mapping (DEBUG=3, VERBOSE=2, etc.)
    # Priority: cli_log_level > cli_verbose > env > yaml > default
    effective_verbosity = -1  # Sentinel value
    log_level_map = {"DEBUG": 3, "VERBOSE": 2, "INFO": 1, "NORMAL": 1, "WARNING": 0, "ERROR": 0, "CRITICAL": 0, "QUIET": 0}
    if cli_log_level is not None:
        level_upper = cli_log_level.upper()
        if level_upper in log_level_map:
            effective_verbosity = log_level_map[level_upper]
            cli_overrides["verbosity"] = effective_verbosity
        else:
            rich_print(f"[yellow]Warning:[/yellow] Invalid CLI log level '{cli_log_level}'. Ignoring.")
    elif cli_verbose is True:
        # Apply cli_verbose only if cli_log_level wasn't set
        # Check env/yaml/default verbosity before overriding
        current_verbosity = env_config.get("verbosity", yaml_config.get("verbosity", 1))  # Default verbosity = 1
        if current_verbosity < 2:  # Only increase if current is less than VERBOSE
            effective_verbosity = 2
            cli_overrides["verbosity"] = effective_verbosity

    # Merge configurations: Defaults < Env < YAML < CLI
    # pydantic-settings (SettingsConfig) handles Defaults < Env automatically.
    # We need to layer YAML and CLI on top of that.
    final_config_data: Dict[str, Any] = env_config  # Start with env/default config

    # Helper for deep merging dictionaries
    def deep_update(target: Dict, source: Dict) -> Dict:
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                deep_update(target[key], value)
            elif value is not None:  # Only update if source value is not None
                target[key] = value
        return target

    # Perform the merge: Update env_config with yaml_config, then with cli_overrides
    final_config_data = deep_update(final_config_data, yaml_config)
    final_config_data = deep_update(final_config_data, cli_overrides)

    # Instantiate the final CodeAgentSettings model
    try:
        final_settings = CodeAgentSettings(**final_config_data)
    except ValidationError as e:
        rich_print(f"[bold red]Error creating final configuration:[/bold red]\n{e}")
        # Fallback to default settings on catastrophic validation error during merge
        rich_print("[yellow]Falling back to default settings.[/yellow]")
        final_settings = CodeAgentSettings()

    return final_settings


# --- Utility functions for Pydantic model manipulation ---


def create_settings_model(config_data: Dict) -> CodeAgentSettings:
    """Instantiate CodeAgentSettings from a dictionary, handling validation errors."""
    try:
        return CodeAgentSettings(**config_data)
    except ValidationError as e:
        rich_print(f"[bold red]Validation Error loading configuration:[/bold red]\n{e}")
        raise  # Re-raise after printing for calling function to handle


def settings_to_dict(settings: CodeAgentSettings) -> Dict:
    """Convert CodeAgentSettings instance to a dictionary, excluding defaults if needed."""
    # Use model_dump for Pydantic v2
    return settings.model_dump(exclude_defaults=False)  # Set exclude_defaults as needed


# --- File Handling ---


def load_config_from_file(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Loads configuration from a YAML file."""
    if not config_path.is_file():
        return {}
    try:
        with open(config_path, "r") as f:
            # Use safe_load to prevent arbitrary code execution
            data = yaml.safe_load(f)
            return data if data else {}
    except yaml.YAMLError as e:
        rich_print(f"[bold red]Error parsing YAML file {config_path}:[/bold red] {e}")
        return {}
    except IOError as e:
        rich_print(f"[bold red]Error reading file {config_path}:[/bold red] {e}")
        return {}


def create_default_config_file(config_path: Path) -> None:
    """Copies the template config file to the specified path."""
    if not TEMPLATE_CONFIG_PATH.exists():
        rich_print("[yellow]Warning:[/yellow] Template configuration file not found. Cannot create default config.")
        return
    try:
        # Ensure the target directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(TEMPLATE_CONFIG_PATH, config_path)
    except Exception as e:
        rich_print(f"[bold red]Error copying template config file:[/bold red] {e}")
        raise  # Re-raise to indicate failure
