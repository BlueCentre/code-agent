"""Tests for configuration validation module."""

from unittest.mock import patch

import pytest

from code_agent.config import SettingsConfig
from code_agent.config.settings_based_config import ApiKeys, CodeAgentSettings, SecuritySettings
from code_agent.config.validation import (
    ValidationResult,
    validate_api_keys,
    validate_config,
    validate_model_compatibility,
    validate_native_command_allowlist,
    validate_native_command_settings,
)


@pytest.fixture
def valid_config():
    """Fixture for a valid configuration."""
    return SettingsConfig(
        default_provider="ai_studio",
        default_model="gemini-2.0-flash",
        api_keys={"openai": "sk-" + "a" * 48, "ai_studio": "AIza" + "a" * 35},
        auto_approve_edits=False,
        auto_approve_native_commands=False,
        native_command_allowlist=["ls", "git status"],
    )


def test_validation_result():
    """Test the ValidationResult class."""
    result = ValidationResult()
    assert result.valid is True
    assert not result.errors
    assert not result.warnings

    # Test adding warnings
    result.add_warning("This is a warning")
    assert result.valid is True  # Still valid
    assert len(result.warnings) == 1
    assert "This is a warning" in result.warnings

    # Test adding errors
    result.add_error("This is an error")
    assert result.valid is False  # No longer valid
    assert len(result.errors) == 1
    assert "This is an error" in result.errors

    # Test string representation
    str_result = str(result)
    assert "1 error(s)" in str_result
    assert "1 warning(s)" in str_result
    assert "This is an error" in str_result
    assert "This is a warning" in str_result


def test_validate_model_compatibility():
    """Test model compatibility validation."""
    result = ValidationResult()

    # Valid provider and model
    validate_model_compatibility("ai_studio", "gemini-2.0-flash", result)
    assert result.valid is True
    assert not result.errors

    # Unknown provider
    validate_model_compatibility("unknown_provider", "some_model", result)
    assert result.valid is True  # Unknown providers don't make the config invalid
    assert len(result.warnings) == 1
    assert "Unknown provider" in result.warnings[0]

    # Invalid model for known provider
    result = ValidationResult()  # Fresh result
    validate_model_compatibility("ai_studio", "invalid_model", result)
    assert result.valid is False
    assert len(result.errors) == 1
    assert "is not recognized for provider" in result.errors[0]
    assert "gemini-2.0-flash" in result.errors[0]  # Should suggest valid models


def test_validate_api_keys():
    """Test API key validation."""
    result = ValidationResult()

    # Valid keys
    api_keys = {"openai": "sk-" + "a" * 48, "groq": "gsk_" + "a" * 40}
    validate_api_keys(api_keys, result)
    assert result.valid is True
    assert not result.warnings

    # No keys
    result = ValidationResult()
    empty_keys = {}
    validate_api_keys(empty_keys, result)
    assert result.valid is True  # Not having keys isn't an error
    assert len(result.warnings) == 1
    assert "No API keys found" in result.warnings[0]

    # Invalid key format
    result = ValidationResult()
    invalid_keys = {"openai": "invalid-key-format"}
    validate_api_keys(invalid_keys, result)
    assert result.valid is True  # Invalid format is a warning, not an error
    assert len(result.warnings) == 1
    assert "doesn't match the expected format" in result.warnings[0]


def test_validate_native_command_allowlist():
    """Test command allowlist validation."""
    result = ValidationResult()

    # Valid allowlist
    valid_allowlist = ["git status", "ls -la", "python -m tests"]
    validate_native_command_allowlist(valid_allowlist, result)
    assert result.valid is True
    assert not result.warnings

    # Empty allowlist
    empty_allowlist = []
    validate_native_command_allowlist(empty_allowlist, result)
    assert result.valid is True
    assert not result.warnings

    # Potentially insecure allowlist
    result = ValidationResult()
    insecure_allowlist = ["rm", "ls | rm", "g", ";"]
    validate_native_command_allowlist(insecure_allowlist, result)
    assert result.valid is True  # Allowlist issues are warnings, not errors
    assert len(result.warnings) == 1
    assert "Potentially insecure command patterns" in result.warnings[0]
    # Check that the command patterns are listed in the warning
    assert all(cmd in result.warnings[0] for cmd in ["'rm'", "'g'", "';'", "'ls | rm'"])


def test_validate_config_with_valid_config(valid_config):
    """Test the main validation function with a valid config."""
    result = validate_config(valid_config)
    assert result.valid is True
    assert not result.errors

    # Valid config may have a warning about short command patterns like 'ls'
    # So check for security warnings by adding them to the config

    # Check warning for security settings
    config_with_security_risk = valid_config.model_copy(
        update={
            "auto_approve_native_commands": True,
            "native_command_allowlist": ["long-command", "another-safe-command"],  # Use safer commands
        }
    )
    result = validate_config(config_with_security_risk)
    assert result.valid is True  # Security issues are warnings, not errors
    assert len(result.warnings) == 1
    assert "SECURITY RISK" in result.warnings[0]
    assert "auto_approve_native_commands" in result.warnings[0]

    # Check both security warnings
    config_with_both_risks = valid_config.model_copy(
        update={
            "auto_approve_native_commands": True,
            "auto_approve_edits": True,
            "native_command_allowlist": ["long-command", "another-safe-command"],  # Use safer commands
        }
    )
    result = validate_config(config_with_both_risks)
    assert result.valid is True
    assert len(result.warnings) == 2
    assert any("auto_approve_native_commands" in w for w in result.warnings)
    assert any("auto_approve_edits" in w for w in result.warnings)


def test_validate_config_with_invalid_config(valid_config):
    """Test the main validation function with invalid configurations."""
    # Invalid model
    invalid_model_config = valid_config.model_copy(update={"default_model": "not-a-real-model"})
    result = validate_config(invalid_model_config)
    assert result.valid is False
    assert len(result.errors) == 1
    assert "not recognized for provider" in result.errors[0]


def test_validate_dynamic_method():
    """Test the validate_dynamic method on CodeAgentSettings."""
    # Valid settings
    valid_settings = CodeAgentSettings(
        default_provider="ai_studio",
        default_model="gemini-2.0-flash",
        api_keys=ApiKeys(
            openai="sk-" + "a" * 48,
            ai_studio="AIza" + "a" * 35,
        ),
        auto_approve_edits=False,
        auto_approve_native_commands=False,
        native_command_allowlist=["git status", "ls -la"],
        security=SecuritySettings(
            path_validation=True,
            workspace_restriction=True,
            command_validation=True,
        ),
    )

    # Test valid config
    with patch("code_agent.config.settings_based_config.rich_print") as mock_print:
        result = valid_settings.validate_dynamic()
        assert result is True
        # Without verbose=True, it shouldn't print anything
        mock_print.assert_not_called()

    # Test with verbose=True
    with patch("code_agent.config.settings_based_config.rich_print") as mock_print:
        result = valid_settings.validate_dynamic(verbose=True)
        assert result is True
        # It should print valid message
        mock_print.assert_any_call("[bold green]✓ Configuration is valid.[/bold green]")

    # Invalid settings (bad model)
    invalid_settings = CodeAgentSettings(
        default_provider="ai_studio",
        default_model="not-a-real-model",  # Invalid model
        api_keys=ApiKeys(
            openai="sk-" + "a" * 48,
            ai_studio="AIza" + "a" * 35,
        ),
    )

    # Test invalid config
    result = invalid_settings.validate_dynamic()
    assert result is False

    # Test with verbose=True
    with patch("code_agent.config.settings_based_config.rich_print") as mock_print:
        result = invalid_settings.validate_dynamic(verbose=True)
        assert result is False
        # It should print error message
        mock_print.assert_any_call("[bold red]Found 1 configuration error(s):[/bold red]")

    # Settings with warnings (security risks)
    warning_settings = CodeAgentSettings(
        default_provider="ai_studio",
        default_model="gemini-2.0-flash",
        api_keys=ApiKeys(
            openai="sk-" + "a" * 48,
            ai_studio="AIza" + "a" * 35,
        ),
        auto_approve_edits=True,  # Security risk
        auto_approve_native_commands=True,  # Security risk
        native_command_allowlist=["git status", "ls -la"],
    )

    # Test with warnings
    with patch("code_agent.config.settings_based_config.rich_print") as mock_print:
        result = warning_settings.validate_dynamic(verbose=True)
        assert result is True  # Valid but with warnings
        # Should print warnings
        mock_print.assert_any_call("[bold yellow]Found 2 configuration warning(s):[/bold yellow]")
        # Should indicate that it's valid with warnings
        mock_print.assert_any_call("[bold green]✓ Configuration is valid[/bold green] [yellow](with warnings)[/yellow]")


def test_validate_native_command_allowlist_with_dangerous_patterns():
    result = ValidationResult()
    dangerous_allowlist = ["rm", ";" "mv *"]
    validate_native_command_allowlist(dangerous_allowlist, result)
    assert len(result.warnings) == 1
    assert "Potentially insecure command patterns" in result.warnings[0]
    assert "rm" in result.warnings[0]
    assert "mv *" in result.warnings[0]


def test_validate_native_command_settings_null():
    """Test validation with null settings."""
    result = ValidationResult()
    validate_native_command_settings(None, result)
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_validate_native_command_settings_negative_timeout():
    """Test validation with negative timeout value."""
    result = ValidationResult()

    # Create a simple mock object
    class MockSettings:
        def __init__(self):
            self.default_timeout = -10
            self.default_working_directory = None

    settings = MockSettings()
    validate_native_command_settings(settings, result)

    assert len(result.errors) == 1
    assert "Invalid default_timeout value" in result.errors[0]
    assert "-10" in result.errors[0]


def test_validate_native_command_settings_nonexistent_dir():
    """Test validation with nonexistent working directory."""
    result = ValidationResult()

    # Create a simple mock object
    class MockSettings:
        def __init__(self):
            self.default_timeout = 30
            self.default_working_directory = "/nonexistent/directory/path"

    settings = MockSettings()
    validate_native_command_settings(settings, result)

    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert "Default working directory does not exist" in result.warnings[0]
    assert "/nonexistent/directory/path" in result.warnings[0]


def test_validate_native_command_settings_valid():
    """Test validation with valid settings."""
    result = ValidationResult()

    # Create a simple mock object with valid values
    class MockSettings:
        def __init__(self):
            self.default_timeout = 30
            self.default_working_directory = None  # None is always valid

    settings = MockSettings()
    validate_native_command_settings(settings, result)

    assert len(result.errors) == 0
    assert len(result.warnings) == 0
