import os
from unittest.mock import mock_open, patch

import pytest
import yaml
from typer.testing import CliRunner

from code_agent.cli.main import app
from code_agent.config.config import (
    ApiKeys,
    SettingsConfig,
    get_config,
)

# Default config used in tests
DEFAULT_CONFIG = {
    "default_provider": "ai_studio",
    "default_model": "gemini-2.0-flash",
    "auto_approve_edits": False,
    "auto_approve_native_commands": False,
    "native_command_allowlist": [],
    "rules": [],
}


@pytest.fixture
def mock_env_vars():
    """Mock environment variables with contextmanager."""
    original_environ = os.environ.copy()

    # Set mock environment variables
    os.environ["OPENAI_API_KEY"] = "env_openai_key"
    os.environ["ANTHROPIC_API_KEY"] = "env_anthropic_key"
    os.environ["CODE_AGENT_DEFAULT_PROVIDER"] = "env_provider"
    os.environ["CODE_AGENT_DEFAULT_MODEL"] = "env_model"
    os.environ["CODE_AGENT_AUTO_APPROVE_EDITS"] = "true"
    os.environ["CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS"] = "false"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture
def mock_config_file():
    """Mock the config file with test configuration."""
    config_content = {
        "default_provider": "file_provider",
        "default_model": "file_model",
        "api_keys": {"openai": "file_openai_key", "groq": "file_groq_key"},
        "auto_approve_edits": False,
        "auto_approve_native_commands": True,
        "native_command_allowlist": ["ls", "cat", "pwd"],
        "rules": ["Be concise", "Explain code"],
    }

    with (
        patch("builtins.open", mock_open(read_data=yaml.dump(config_content))),
        patch("os.path.exists", return_value=True),
    ):
        yield config_content


@pytest.fixture
def reset_config_cache():
    """Clear any cached config."""
    # If get_config uses caching, this would reset it
    # This is important to ensure tests don't affect each other
    if hasattr(get_config, "cache_clear"):
        get_config.cache_clear()
    yield


@pytest.fixture
def cli_runner():
    """Create a CLI runner."""
    return CliRunner()


# --- Test get_config with different sources ---


def test_config_defaults_only():
    """Test default configuration when no file or env vars present."""
    # Mock file not existing and no env vars
    with patch("os.path.exists", return_value=False), patch("os.environ", {}):
        config = get_config()

    # Should match defaults
    assert config.default_provider == DEFAULT_CONFIG["default_provider"]
    assert config.default_model == DEFAULT_CONFIG["default_model"]
    assert config.auto_approve_edits == DEFAULT_CONFIG["auto_approve_edits"]
    assert (
        config.auto_approve_native_commands
        == DEFAULT_CONFIG["auto_approve_native_commands"]
    )
    assert config.native_command_allowlist == DEFAULT_CONFIG["native_command_allowlist"]
    assert config.rules == DEFAULT_CONFIG["rules"]


def test_config_file_only(mock_config_file, reset_config_cache):
    """Test configuration from file only (no env vars)."""
    # Clear environment variables that might be set
    with patch("os.environ", {}):
        config = get_config()

    # Should match file values
    assert config.default_provider == mock_config_file["default_provider"]
    assert config.default_model == mock_config_file["default_model"]
    assert config.auto_approve_edits == mock_config_file["auto_approve_edits"]
    assert (
        config.auto_approve_native_commands
        == mock_config_file["auto_approve_native_commands"]
    )
    assert (
        config.native_command_allowlist == mock_config_file["native_command_allowlist"]
    )
    assert config.rules == mock_config_file["rules"]

    # API keys should match file
    assert config.api_keys.openai == mock_config_file["api_keys"]["openai"]
    assert config.api_keys.groq == mock_config_file["api_keys"]["groq"]
    assert config.api_keys.anthropic is None  # Not in file


def test_config_env_vars_only(mock_env_vars, reset_config_cache):
    """Test configuration from environment variables only (no file)."""
    # Mock file not existing
    with patch("os.path.exists", return_value=False):
        config = get_config()

    # Should match environment values where set
    assert config.default_provider == "env_provider"
    assert config.default_model == "env_model"
    assert config.auto_approve_edits is True
    assert config.auto_approve_native_commands is False

    # API keys should match environment vars
    assert config.api_keys.openai == "env_openai_key"
    assert config.api_keys.anthropic == "env_anthropic_key"
    assert config.api_keys.groq is None  # Not in env


def test_config_env_overrides_file(mock_config_file, mock_env_vars, reset_config_cache):
    """Test environment variables override file config."""
    config = get_config()

    # Should match environment values where set
    assert config.default_provider == "env_provider"  # From env
    assert config.default_model == "env_model"  # From env
    assert config.auto_approve_edits is True  # From env
    assert config.auto_approve_native_commands is False  # From env

    # API keys should prefer env values when available
    assert config.api_keys.openai == "env_openai_key"  # From env
    assert config.api_keys.anthropic == "env_anthropic_key"  # From env
    assert config.api_keys.groq == "file_groq_key"  # From file

    # Other settings should come from file if not in env
    assert (
        config.native_command_allowlist == mock_config_file["native_command_allowlist"]
    )
    assert config.rules == mock_config_file["rules"]


# --- Test CLI overrides ---


def test_cli_overrides_config(mock_config_file, mock_env_vars, cli_runner):
    """Test CLI arguments override both file and environment config."""
    # Run command with CLI overrides
    with patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        # First return the mock config
        mock_get_config.return_value = get_config()

        # Run with provider and model overrides
        result = cli_runner.invoke(
            app,
            [
                "--provider",
                "cli_provider",
                "--model",
                "cli_model",
                "run",
                "Test prompt",
            ],
        )

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that we logged the CLI overrides
    assert "Provider Override: cli_provider" in result.stdout
    assert "Model Override: cli_model" in result.stdout


def test_cli_specific_options(cli_runner):
    """Test CLI-specific options that don't exist in config file."""
    # Test --verbose flag
    with patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        mock_get_config.return_value = get_config()

        result = cli_runner.invoke(app, ["--verbose", "run", "Test prompt"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that verbose mode was enabled
    assert "Verbose mode enabled" in result.stdout


def test_config_inheritance_for_api_keys(reset_config_cache):
    """Test proper inheritance of API keys from different sources."""
    # Create a partial config file
    file_config = {
        "api_keys": {
            "openai": "file_openai_key",
            "groq": "file_groq_key",
            # anthropic missing from file
        }
    }

    # Override with some environment variables
    env_vars = {
        "ANTHROPIC_API_KEY": "env_anthropic_key",
        # openai present in file but not env
        # groq present in both
        "GROQ_API_KEY": "env_groq_key",
    }

    with (
        patch("builtins.open", mock_open(read_data=yaml.dump(file_config))),
        patch("os.path.exists", return_value=True),
        patch("os.environ", env_vars),
    ):
        config = get_config()

    # Check proper precedence
    assert config.api_keys.openai == "file_openai_key"  # From file only
    assert config.api_keys.anthropic == "env_anthropic_key"  # From env only
    assert config.api_keys.groq == "env_groq_key"  # Env overrides file


def test_config_autoload_on_cli_command(cli_runner):
    """Test that config is automatically loaded for each CLI command."""
    with patch("code_agent.cli.main.config_module.get_config") as mock_get_config:
        mock_config = SettingsConfig(
            default_provider="test_provider",
            default_model="test_model",
            api_keys=ApiKeys(openai="test_key"),
        )
        mock_get_config.return_value = mock_config

        # Run a command
        result = cli_runner.invoke(app, ["config", "show"])

    # Check command executed successfully
    assert result.exit_code == 0

    # Check that get_config was called
    mock_get_config.assert_called_once()


def test_config_boolean_conversion_from_env(reset_config_cache):
    """Test correct conversion of string env vars to boolean config values."""
    # Test various string representations of boolean values
    env_cases = {
        "true": True,
        "True": True,
        "TRUE": True,
        "1": True,
        "yes": True,
        "false": False,
        "False": False,
        "FALSE": False,
        "0": False,
        "no": False,
    }

    for env_str, expected_bool in env_cases.items():
        # Create environment with this boolean string
        env_vars = {"CODE_AGENT_AUTO_APPROVE_EDITS": env_str}

        with patch("os.path.exists", return_value=False), patch("os.environ", env_vars):
            config = get_config()

            # Check correct conversion
            assert (
                config.auto_approve_edits is expected_bool
            ), f"Failed to convert '{env_str}' to {expected_bool}"


def test_config_validation_rules():
    """Test config validation rules from Pydantic."""
    # Test invalid provider name
    invalid_config = {
        "default_provider": "invalid_provider",  # Not in supported providers
        "api_keys": {},
    }

    with (
        patch("builtins.open", mock_open(read_data=yaml.dump(invalid_config))),
        patch("os.path.exists", return_value=True),
        pytest.raises(ValueError) as exc_info,
    ):
        get_config()

    # Should raise validation error about invalid provider
    assert "default_provider" in str(exc_info.value).lower()

    # Test incompatible allow list and auto approve
    risky_config = {
        "native_command_allowlist": ["rm", "sudo"],  # Dangerous commands
        "auto_approve_native_commands": True,  # Auto approve is risky with these
    }

    with (
        patch("builtins.open", mock_open(read_data=yaml.dump(risky_config))),
        patch("os.path.exists", return_value=True),
        pytest.raises(ValueError) as exc_info,
    ):
        get_config()

    # Should raise validation error about dangerous commands with auto approve
    assert (
        "dangerous" in str(exc_info.value).lower()
        or "risky" in str(exc_info.value).lower()
    )
