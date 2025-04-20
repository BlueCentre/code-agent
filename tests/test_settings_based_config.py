"""Tests for settings-based configuration module."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from code_agent.config.settings_based_config import (
    ApiKeys,
    SettingsConfig,
    build_effective_config,
    create_default_config_file,
    get_api_key,
    get_config,
    initialize_config,
    load_config_from_file,
)


@pytest.fixture
def temp_config_path(tmp_path):
    """Creates a temporary config path for testing."""
    config_dir = tmp_path / ".config" / "code-agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    return config_path


@pytest.fixture
def valid_config_data():
    """Returns a valid configuration dictionary."""
    return {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "api_keys": {
            "openai": "sk-" + "a" * 48,
            "ai_studio": "AIza" + "a" * 35,
        },
        "auto_approve_edits": False,
        "auto_approve_native_commands": False,
        "native_command_allowlist": ["git status", "ls -la"],
        "rules": ["rule1", "rule2"],
    }


def test_api_keys_model():
    """Test the ApiKeys model."""
    # Test with standard keys
    keys = ApiKeys(openai="test-key", ai_studio="test-key-2")
    assert keys.openai == "test-key"
    assert keys.ai_studio == "test-key-2"

    # Test with extra keys (using model_dump to access)
    extra_keys = ApiKeys(openai="test-key", custom_provider="custom-key")
    assert extra_keys.openai == "test-key"
    assert "custom_provider" in extra_keys.model_dump(exclude_unset=True)


def test_settings_config_model():
    """Test the SettingsConfig model."""
    # Test default values
    config = SettingsConfig()
    assert config.default_provider == "ai_studio"
    assert config.default_model == "gemini-2.0-flash"
    assert config.auto_approve_edits is False
    assert config.auto_approve_native_commands is False
    assert config.native_command_allowlist == []
    assert config.rules == []

    # Test with custom values
    custom_config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4o",
        auto_approve_edits=True,
        native_command_allowlist=["git status"],
    )
    assert custom_config.default_provider == "openai"
    assert custom_config.default_model == "gpt-4o"
    assert custom_config.auto_approve_edits is True
    assert custom_config.auto_approve_native_commands is False
    assert custom_config.native_command_allowlist == ["git status"]


def test_load_config_from_file(temp_config_path, valid_config_data):
    """Test loading configuration from a file."""
    # Create a test config file
    with open(temp_config_path, "w") as f:
        yaml.dump(valid_config_data, f)

    # Load the config
    loaded_config = load_config_from_file(temp_config_path)

    # Verify loaded data
    assert loaded_config["default_provider"] == "openai"
    assert loaded_config["default_model"] == "gpt-4o"
    assert loaded_config["api_keys"]["openai"].startswith("sk-")
    assert loaded_config["native_command_allowlist"] == ["git status", "ls -la"]


def test_load_config_file_not_exists(temp_config_path):
    """Test loading when config file doesn't exist."""
    # Need to ensure the file doesn't exist
    if temp_config_path.exists():
        temp_config_path.unlink()

    # Mock the create_default_config_file to avoid actual file operations
    with (
        patch("code_agent.config.settings_based_config.create_default_config_file") as mock_create,
        patch("pathlib.Path.exists", return_value=False),
    ):
        loaded_config = load_config_from_file(temp_config_path)

        # Verify create_default_config_file was called
        mock_create.assert_called_once_with(temp_config_path)

        # Should return empty dict
        assert isinstance(loaded_config, dict)


def test_load_config_migration():
    """Test aspects of config loading that don't require full migration logic."""
    # Use a mock for the open function to avoid file operations
    mock_file = mock_open(read_data=yaml.dump({"default_provider": "test"}))

    with (
        patch("builtins.open", mock_file),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.mkdir"),
    ):
        # Call function with a path
        config = load_config_from_file(Path("some_path"))

        # Verify we got some data back
        assert isinstance(config, dict)
        assert "default_provider" in config


def test_create_default_config_file(temp_config_path):
    """Test creating default config file."""
    # Test with template not existing
    with patch("pathlib.Path.exists", return_value=False), patch("builtins.open", mock_open()) as mock_file:
        create_default_config_file(temp_config_path)

        # Verify file was opened for writing
        mock_file.assert_called_once_with(temp_config_path, "w")

    # Test with template existing
    with patch("pathlib.Path.exists", return_value=True), patch("shutil.copy2") as mock_copy:
        create_default_config_file(temp_config_path)

        # Verify copy was attempted
        mock_copy.assert_called_once()


def test_build_effective_config():
    """Test building effective config with various layers."""
    # Mock the file loading to return our test config
    test_config = {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "api_keys": {"openai": "file-key"},
    }

    with patch("code_agent.config.settings_based_config.load_config_from_file", return_value=test_config):
        # Test with CLI overrides
        config = build_effective_config(cli_provider="cli-provider", cli_model="cli-model", cli_auto_approve_edits=True)

        # CLI takes precedence over file
        assert config.default_provider == "cli-provider"
        assert config.default_model == "cli-model"
        assert config.auto_approve_edits is True

        # The API key should be from the file config since we're mocking the load
        assert vars(config.api_keys).get("openai") == "file-key"


def test_build_effective_config_error_handling():
    """Test error handling in build_effective_config."""
    # Test with invalid config that causes ValidationError
    with patch(
        "code_agent.config.settings_based_config.load_config_from_file", return_value={"default_provider": 123}
    ):  # Invalid type for provider
        config = build_effective_config()

        # Should fall back to defaults
        assert config.default_provider == "ai_studio"
        assert config.default_model == "gemini-2.0-flash"


def test_initialize_and_get_config():
    """Test initializing and getting config."""
    # Reset the module config
    import code_agent.config.settings_based_config

    code_agent.config.settings_based_config._config = None

    # Mock build_effective_config to avoid actual file operations
    test_config = SettingsConfig(default_provider="test-provider")
    with patch("code_agent.config.settings_based_config.build_effective_config", return_value=test_config):
        # Initialize config
        initialize_config()

        # Get config should return the same instance
        config = get_config()
        assert config.default_provider == "test-provider"

        # Calling initialize again should not change the config
        with patch(
            "code_agent.config.settings_based_config.build_effective_config",
            return_value=SettingsConfig(default_provider="different-provider"),
        ):
            initialize_config()
            # Should still have original values
            assert get_config().default_provider == "test-provider"


def test_get_api_key():
    """Test the get_api_key helper function."""
    # Reset the module config
    import code_agent.config.settings_based_config

    code_agent.config.settings_based_config._config = None

    # Create a config with standard API keys
    test_config = SettingsConfig(api_keys=ApiKeys(openai="test-key"))

    # Also test with a custom ApiKeys-like dictionary (simulating what vars() does)
    api_keys_dict = {"openai": "test-key", "custom": "custom-key"}

    with (
        patch("code_agent.config.settings_based_config.get_config", return_value=test_config),
        patch("code_agent.config.settings_based_config.vars", return_value=api_keys_dict),
    ):
        # Test getting standard key
        assert get_api_key("openai") == "test-key"

        # Test getting the mocked custom key
        assert get_api_key("custom") == "custom-key"

        # Test getting non-existent key
        assert get_api_key("nonexistent") is None
