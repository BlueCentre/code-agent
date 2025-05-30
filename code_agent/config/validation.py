"""Configuration validation with clear, actionable error messages.

This module provides functions to validate configuration settings beyond
the basic type checking done by Pydantic. It includes validation for:

1. Provider-specific model compatibility
2. Command allowlist patterns
3. API key format validation
4. Security recommendations
"""

import re
from typing import Any, Dict, List, Union

# --- Model compatibility validation ---

# Map of provider to supported models (will need to be kept up-to-date)
PROVIDER_MODEL_MAP = {
    "ai_studio": {"gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash", "gemini-1.5-pro"},
    "openai": {
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-4o-mini",
    },
    "anthropic": {"claude-3-opus", "claude-3-sonnet", "claude-3-haiku"},
    "groq": {"llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768", "gemma-7b-it"},
}

# --- API Key validation regexes ---
API_KEY_REGEXES = {
    "openai": r"^sk-[a-zA-Z0-9]{32,}$",
    "ai_studio": r"^AIza[a-zA-Z0-9_-]{35,}$",
    "groq": r"^gsk_[a-zA-Z0-9]{32,}$",
    "anthropic": r"^sk-ant-[a-zA-Z0-9]{32,}$",
}


class ValidationResult:
    """Holds the result of a configuration validation."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.valid = True

    def add_error(self, error: str):
        """Add an error and set valid to False."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        """Add a warning without affecting the valid flag."""
        self.warnings.append(warning)

    def __str__(self) -> str:
        if self.valid and not self.warnings:
            return "Configuration is valid."

        parts = []
        if not self.valid:
            parts.append(f"Found {len(self.errors)} error(s):")
            for i, error in enumerate(self.errors, 1):
                parts.append(f"  {i}. {error}")

        if self.warnings:
            parts.append(f"Found {len(self.warnings)} warning(s):")
            for i, warning in enumerate(self.warnings, 1):
                parts.append(f"  {i}. {warning}")

        return "\n".join(parts)


def validate_model_compatibility(provider: str, model: str, result: ValidationResult) -> None:
    """Validate that the selected model is compatible with the provider."""
    if provider not in PROVIDER_MODEL_MAP:
        result.add_warning(f"Unknown provider '{provider}'. Cannot validate model compatibility.")
        return

    if model not in PROVIDER_MODEL_MAP[provider]:
        # Check for model name pattern matches (some providers use pattern-based names)
        is_openai = provider == "openai"
        is_ft_model = model.startswith("ft:")
        is_vision_model = model.startswith("gpt-4-vision")
        is_32k_model = model.startswith("gpt-4-32k")

        # Special model patterns that are allowed for OpenAI
        is_special_model = is_ft_model or is_vision_model or is_32k_model

        # Only add error if not a special OpenAI model
        if not (is_openai and is_special_model):
            # Add clear error with helpful suggestions
            supported_models = ", ".join(f"'{m}'" for m in sorted(PROVIDER_MODEL_MAP[provider]))
            result.add_error(f"Model '{model}' is not recognized for provider '{provider}'. Supported models include: {supported_models}.")


def validate_api_keys(api_keys: Union[Dict[str, str], Any], default_provider: str, result: ValidationResult) -> None:
    """Validate API keys for format and presence.

    Checks:
    1. The key for the default provider is present
    2. Any provided keys match the expected format

    Args:
        api_keys: Either an ApiKeys object or a dictionary of keys
        default_provider: The configured default provider
        result: ValidationResult to update
    """
    # Get all API keys as a dictionary
    if isinstance(api_keys, dict):
        keys_dict = api_keys
    else:
        # Get the dict representation of the ApiKeys object
        try:
            # Use model_dump for Pydantic v2+, prefer exclude_none
            keys_dict = api_keys.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback for older Pydantic or non-model objects
            keys_dict = {k: v for k, v in vars(api_keys).items() if v is not None}

    # Check if any keys were provided at all
    if not keys_dict:
        result.add_warning("No API keys found in configuration. You will need to set them via environment variables.")
        # If no keys provided at all, the default provider key is definitely missing
        result.add_error(f"API key for default provider '{default_provider}' is missing.")
        return  # Stop further checks if no keys exist

    # --- Critical Check: Default provider key presence ---
    default_key = keys_dict.get(default_provider)
    if not default_key:
        result.add_error(f"API key for default provider '{default_provider}' is missing or empty.")

    # Validate format of provided keys
    for provider, key in keys_dict.items():
        if key is None:  # Should be excluded by model_dump(exclude_none=True), but check anyway
            continue

        # Skip keys from unknown providers for format checking
        if provider not in API_KEY_REGEXES:
            continue

        # Check key format
        if not re.match(API_KEY_REGEXES[provider], key):
            result.add_warning(f"API key for {provider} doesn't match the expected format. Please check that it's correct.")


def validate_native_command_allowlist(allowlist: List[str], result: ValidationResult) -> None:
    """Validate the native command allowlist.

    Checks:
    1. Length and complexity of command patterns
    2. Security of allowed commands
    3. Provides best practice suggestions
    """
    if not allowlist:
        return

    # Check for overly permissive patterns that could be security risks
    dangerous_patterns = []
    for cmd in allowlist:
        # Overly short patterns can match too many commands
        if len(cmd) < 3:
            dangerous_patterns.append(cmd)
        # Patterns that could be used for command chaining
        elif any(c in cmd for c in [";", "|", "&&", "||", "`"]):
            dangerous_patterns.append(cmd)

    if dangerous_patterns:
        patterns_str = ", ".join(f"'{p}'" for p in dangerous_patterns)
        result.add_warning(f"Potentially insecure command patterns in allowlist: {patterns_str}. Consider using more specific command patterns for security.")


def validate_native_command_settings(native_commands: Any, result: ValidationResult) -> None:
    """Validate the native command settings.

    Checks:
    1. Timeout is a positive number if set
    2. Working directory exists or is None
    """
    if native_commands is None:
        return

    # Check timeout
    if hasattr(native_commands, "default_timeout") and native_commands.default_timeout is not None:
        if native_commands.default_timeout <= 0:
            result.add_error(f"Invalid default_timeout value: {native_commands.default_timeout}. Timeout must be a positive number.")

    # Check working directory
    if hasattr(native_commands, "default_working_directory") and native_commands.default_working_directory is not None:
        from pathlib import Path

        working_dir = Path(native_commands.default_working_directory)
        if not working_dir.exists():
            result.add_warning(
                f"Default working directory does not exist: {native_commands.default_working_directory}. Commands may fail if this directory is not created."
            )


def validate_config(config: Any) -> ValidationResult:
    """Validate the complete configuration and return detailed results.

    Args:
        config: The configuration to validate (SettingsConfig object)

    Returns:
        ValidationResult with detailed errors and warnings
    """
    result = ValidationResult()

    # Validate model compatibility
    validate_model_compatibility(config.default_provider, config.default_model, result)

    # Validate API keys (pass default_provider)
    validate_api_keys(config.api_keys, config.default_provider, result)

    # Validate native command allowlist
    validate_native_command_allowlist(config.native_command_allowlist, result)

    # Validate native command settings
    if hasattr(config, "native_commands"):
        validate_native_command_settings(config.native_commands, result)

    # Check for security risks
    if config.auto_approve_native_commands:
        result.add_warning("SECURITY RISK: auto_approve_native_commands is enabled. This allows execution of commands without confirmation.")

    if config.auto_approve_edits:
        result.add_warning("SECURITY RISK: auto_approve_edits is enabled. This allows file modifications without confirmation.")

    return result


def print_validation_result(result: ValidationResult, verbose: bool = False) -> None:
    """Print validation results in a clear, formatted way.

    Args:
        result: The validation result to print
        verbose: Whether to print even if there are no errors/warnings
    """
    if not result.errors and not result.warnings:
        if verbose:
            print("✅ Configuration is valid.")
        return

    if result.errors:
        print(f"❌ Found {len(result.errors)} error(s):")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")

    if result.warnings:
        print(f"⚠️  Found {len(result.warnings)} warning(s):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")

    if not result.errors:
        print("✅ Configuration is valid (with warnings).")
