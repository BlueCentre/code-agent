"""Tests for configuration loading, initialization, and helper functions."""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml
from pydantic import ValidationError

import code_agent.config.config  # Import the target module for side effects

# Import from the correct location now
from code_agent.config.config import get_api_key, get_config, initialize_config

# Use the correct path for these models and functions
from code_agent.config.settings_based_config import (
    ApiKeys,
    CodeAgentSettings,  # Use the final merged settings class
    SettingsConfig,
    build_effective_config,
    create_default_config_file,
    load_config_from_file,
)


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Ensures the config singleton is reset before each test."""
    global config_singleton
    config_singleton = None
    yield
    config_singleton = None


@pytest.fixture
def temp_config_path(tmp_path):
    """Creates a temporary config path for testing."""
    config_dir = tmp_path / ".config" / "code-agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    return config_path


@pytest.fixture
def valid_config_data():
    """Returns a valid configuration dictionary for file loading tests."""
    # Based on SettingsConfig structure, but CodeAgentSettings is the final result
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
        "max_tokens": 1500,  # Add fields from CodeAgentSettings if needed
        "temperature": 0.8,
        "max_tool_calls": 5,
        "verbosity": 1,
    }


# --- Tests for Models (ApiKeys, SettingsConfig, CodeAgentSettings) ---


def test_api_keys_model():
    """Test the ApiKeys model."""
    keys = ApiKeys(openai="test-key", ai_studio="test-key-2")
    assert keys.openai == "test-key"
    assert keys.ai_studio == "test-key-2"
    # Test extra keys are allowed and accessible via model_dump
    extra_keys = ApiKeys(openai="test-key", custom_provider="custom-key")
    dump = extra_keys.model_dump(exclude_unset=True)
    assert dump["openai"] == "test-key"
    assert dump["custom_provider"] == "custom-key"


def test_settings_config_model_defaults():
    """Test the default values in SettingsConfig."""
    config = SettingsConfig()
    assert config.default_provider == "ai_studio"
    assert config.default_model == "gemini-2.0-flash"
    assert config.auto_approve_edits is False
    assert config.auto_approve_native_commands is False
    assert config.native_command_allowlist == []
    assert config.rules == []
    # Check defaults for fields inherited/added in CodeAgentSettings
    agent_settings = CodeAgentSettings()  # Should inherit defaults
    assert agent_settings.default_provider == "ai_studio"
    assert agent_settings.max_tokens == 1000  # Default from CodeAgentSettings
    assert agent_settings.temperature == 0.7  # Default from CodeAgentSettings


def test_settings_config_model_custom():
    """Test creating SettingsConfig with custom values."""
    custom_config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4o",
        auto_approve_edits=True,
        native_command_allowlist=["git status"],
    )
    assert custom_config.default_provider == "openai"
    assert custom_config.default_model == "gpt-4o"
    assert custom_config.auto_approve_edits is True
    assert custom_config.native_command_allowlist == ["git status"]


def test_code_agent_settings_merges_correctly():
    """Test that CodeAgentSettings merges fields from SettingsConfig correctly."""
    settings_config = SettingsConfig(default_provider="test_provider", max_tokens=500)
    # Simulate loading into CodeAgentSettings
    merged_settings = CodeAgentSettings(**settings_config.model_dump())
    assert merged_settings.default_provider == "test_provider"
    assert merged_settings.max_tokens == 500  # Takes value from SettingsConfig part
    assert merged_settings.temperature == 0.7  # Takes default from CodeAgentSettings
    assert merged_settings.max_tool_calls == 10  # Takes default from CodeAgentSettings


# --- Tests for File Loading ---


def test_load_config_from_file(temp_config_path, valid_config_data):
    """Test loading configuration from a YAML file."""
    with open(temp_config_path, "w") as f:
        yaml.dump(valid_config_data, f)

    loaded_config = load_config_from_file(temp_config_path)

    # Verify data loaded correctly from file
    assert isinstance(loaded_config, dict)
    assert loaded_config["default_provider"] == "openai"
    assert loaded_config["default_model"] == "gpt-4o"
    assert loaded_config["api_keys"]["openai"].startswith("sk-")
    assert loaded_config["native_command_allowlist"] == ["git status", "ls -la"]
    assert loaded_config["max_tokens"] == 1500  # Check field from CodeAgentSettings


def test_load_config_file_not_exists(temp_config_path):
    """Test loading when config file doesn't exist (should create default)."""
    if temp_config_path.exists():
        temp_config_path.unlink()  # Ensure it doesn't exist

    # Mock create_default_config_file to avoid actual file creation/copy
    with patch("code_agent.config.settings_based_config.create_default_config_file") as mock_create:
        # Mock Path.exists used inside load_config_from_file
        with patch("pathlib.Path.exists", return_value=False):
            loaded_config = load_config_from_file(temp_config_path)

    mock_create.assert_called_once_with(temp_config_path)
    # Should return an empty dict when file doesn't exist and is mocked
    assert loaded_config == {}


def test_load_config_from_empty_file(temp_config_path):
    """Test loading configuration from an empty file."""
    temp_config_path.touch()  # Create empty file

    loaded_config = load_config_from_file(temp_config_path)
    assert loaded_config == {}  # Loading empty YAML returns None, which we convert to {}


# Patch standard print as that's what load_config_from_file uses
@patch("builtins.print")
def test_load_config_from_invalid_yaml(mock_print, temp_config_path):
    """Test loading configuration from a file with invalid YAML."""
    invalid_yaml_content = "default_provider: openai\n  invalid_yaml: ["  # Invalid YAML
    with open(temp_config_path, "w") as f:
        f.write(invalid_yaml_content)

    # The function should catch the error and return empty dict
    loaded_config = load_config_from_file(temp_config_path)
    assert loaded_config == {}

    # Check that a warning was printed
    mock_print.assert_called_once()
    # More specific check for the warning content
    args, kwargs = mock_print.call_args
    assert "Warning: Could not read config file" in args[0]
    assert "Error: mapping values are not allowed here" in args[0]


# --- Tests for Default Config File Creation ---


# Patch the specific calls made within create_default_config_file
@patch("code_agent.config.settings_based_config.shutil.copy2")
@patch("pathlib.Path.mkdir")  # Patch mkdir on the class
@patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH")  # Patch the object itself
def test_create_default_config_file_copies_template(mock_template_path, mock_mkdir, mock_copy, temp_config_path):
    """Test create_default_config_file copies template if it exists."""
    # Configure the mocked template path object
    mock_template_path.exists.return_value = True  # Template exists

    create_default_config_file(temp_config_path)

    # Assert mkdir was called for the parent directory
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Assert template check was done
    mock_template_path.exists.assert_called_once()
    # Assert copy was called
    mock_copy.assert_called_once_with(mock_template_path, temp_config_path)  # Use mocked object here


# Patch the specific calls made within create_default_config_file
@patch("builtins.open", new_callable=mock_open)
@patch("code_agent.config.settings_based_config.yaml.dump")
@patch("pathlib.Path.mkdir")  # Patch mkdir on the class
@patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH")  # Patch the object itself
def test_create_default_config_file_creates_empty_if_no_template(mock_template_path, mock_mkdir, mock_yaml_dump, mock_open_file, temp_config_path):
    """Test create_default_config_file creates file with defaults if template is missing."""
    # Configure the mocked template path object
    mock_template_path.exists.return_value = False  # Template does NOT exist

    create_default_config_file(temp_config_path)

    # Assert mkdir was called for the parent directory
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Assert template check was done
    mock_template_path.exists.assert_called_once()
    # Assert open was called to write the file
    mock_open_file.assert_called_once_with(temp_config_path, "w")
    # Assert yaml.dump was called to write default content
    mock_yaml_dump.assert_called_once()
    dump_args, _ = mock_yaml_dump.call_args
    assert "default_provider" in dump_args[0]
    assert "api_keys" in dump_args[0]


# --- Tests for Building Effective Config ---


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_defaults(mock_load_config):
    """Test building effective config with only defaults."""
    mock_load_config.return_value = {}  # Simulate empty config file

    config = build_effective_config()  # Use default path

    assert isinstance(config, CodeAgentSettings)
    # Check default values from CodeAgentSettings
    assert config.default_provider == "ai_studio"
    assert config.default_model == "gemini-2.0-flash"
    assert config.max_tokens == 1000
    assert config.temperature == 0.7
    assert config.auto_approve_edits is False
    assert config.api_keys.openai is None  # Check default API key is None


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_file_values(mock_load_config, valid_config_data):
    """Test building effective config loading values from file."""
    mock_load_config.return_value = valid_config_data

    config = build_effective_config()

    assert config.default_provider == "openai"  # From file
    assert config.default_model == "gpt-4o"  # From file
    assert config.max_tokens == 1500  # From file
    assert config.temperature == 0.8  # From file
    assert config.auto_approve_native_commands is False  # From file
    assert config.native_command_allowlist == ["git status", "ls -la"]  # From file
    assert config.api_keys.openai.startswith("sk-")  # From file
    assert config.api_keys.ai_studio.startswith("AIza")  # From file


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_cli_overrides(mock_load_config, valid_config_data):
    """Test building effective config with CLI overrides."""
    mock_load_config.return_value = valid_config_data

    config = build_effective_config(
        cli_provider="anthropic",
        cli_model="claude-3-opus",
        cli_auto_approve_edits=True,
        cli_auto_approve_native_commands=True,  # Override file value
    )

    assert config.default_provider == "anthropic"  # CLI override
    assert config.default_model == "claude-3-opus"  # CLI override
    assert config.auto_approve_edits is True  # CLI override
    assert config.auto_approve_native_commands is True  # CLI override
    # Values not overridden should come from file
    assert config.max_tokens == 1500
    assert config.api_keys.openai.startswith("sk-")


@patch.dict(os.environ, {"CODE_AGENT_DEFAULT_PROVIDER": "groq", "CODE_AGENT_DEFAULT_MODEL": "llama3", "CODE_AGENT_API_KEYS__GROQ": "env-groq-key"})
@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_env_vars(mock_load_config, valid_config_data):
    """Test building effective config with environment variables."""
    # File values should be overridden by environment variables
    mock_load_config.return_value = valid_config_data

    config = build_effective_config()

    assert config.default_provider == "groq"  # Env override
    assert config.default_model == "llama3"  # Env override
    assert config.api_keys.groq == "env-groq-key"  # Env override
    # Values not overridden by env should come from file
    assert config.max_tokens == 1500
    assert config.api_keys.openai.startswith("sk-")


@patch.dict(os.environ, {"CODE_AGENT_DEFAULT_MODEL": "env-model"})
@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_all_layers(mock_load_config, valid_config_data):
    """Test precedence: CLI > Environment > File > Defaults."""
    mock_load_config.return_value = valid_config_data  # File values

    config = build_effective_config(
        cli_provider="cli-provider"  # CLI override
    )

    assert config.default_provider == "cli-provider"  # CLI wins
    assert config.default_model == "env-model"  # Env wins over file
    assert config.max_tokens == 1500  # File wins over default
    assert config.temperature == 0.8  # File wins over default
    assert config.api_keys.openai.startswith("sk-")  # File wins over default


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_validation_error(mock_load_config):
    """Test that build_effective_config raises ValidationError for invalid data."""
    invalid_data = {"max_tokens": "not-a-number"}
    mock_load_config.return_value = invalid_data

    with pytest.raises(ValidationError, match="max_tokens"):
        build_effective_config()


# --- Tests for Initialization and Singleton Access ---


@patch("code_agent.config.config.build_effective_config")
def test_initialize_and_get_config(mock_build_config):
    """Test initializing and retrieving the config singleton."""
    # Configure the mock return value
    mock_settings = CodeAgentSettings(default_provider="mock_provider")
    mock_build_config.return_value = mock_settings

    # First call initializes
    initialize_config(validate=False)  # Disable validation for this test simplicity
    mock_build_config.assert_called_once()

    # Second call should return the initialized instance
    config1 = get_config()
    assert config1 is mock_settings
    assert config1.default_provider == "mock_provider"

    # Subsequent get_config calls return the same instance
    config2 = get_config()
    assert config2 is config1

    # Calling initialize again should not re-initialize
    mock_build_config.reset_mock()
    initialize_config(validate=False)
    mock_build_config.assert_not_called()
    config3 = get_config()
    assert config3 is config1  # Still the original instance


def set_mock_config(*args, **kwargs):
    """Side effect to set the global _config in the target module."""
    # No need to import here if imported at top level
    # import code_agent.config.config
    # Use the actual CodeAgentSettings or a MagicMock depending on test needs
    # Here, just setting it to non-None is enough for this specific test
    code_agent.config.config._config = MagicMock(spec=CodeAgentSettings)


# Use patch to control the singleton value directly
@patch("code_agent.config.config.initialize_config", side_effect=set_mock_config)  # Add side effect
@patch("code_agent.config.config._config", None)  # Ensure _config is None before test
def test_get_config_initializes_if_needed(mock_initialize):
    """Test that get_config calls initialize_config if singleton is None."""
    # No need to import here if imported at top level
    # import code_agent.config.config

    # Ensure _config starts as None (done by patch)
    assert code_agent.config.config._config is None

    # Call get_config when _config is None (patched)
    retrieved_config = get_config()

    # Check initialize_config was called
    mock_initialize.assert_called_once()
    # Check that _config is now set (by the side_effect)
    assert code_agent.config.config._config is not None
    assert retrieved_config is code_agent.config.config._config


def test_get_api_key_helper():
    """Test the get_api_key helper function."""
    # Set up a mock config object for get_config to return
    mock_keys = ApiKeys(openai="openai-key", anthropic="anthropic-key")
    mock_settings = CodeAgentSettings(api_keys=mock_keys)

    with patch("code_agent.config.config.get_config", return_value=mock_settings):
        assert get_api_key("openai") == "openai-key"
        assert get_api_key("anthropic") == "anthropic-key"
        assert get_api_key("nonexistent") is None
        assert get_api_key("ai_studio") is None  # Not set in mock keys


# --- Tests for Validation Integration (optional basic check) ---


# Use patch to control the singleton value
@patch("code_agent.config.config.build_effective_config")
@patch("code_agent.config.settings_based_config.CodeAgentSettings.validate_dynamic")
@patch("code_agent.config.config._config", None)  # Ensure _config is None before test
def test_initialize_config_calls_validation(mock_validate, mock_build_config):
    """Test that initialize_config calls validate_dynamic by default."""
    mock_settings = CodeAgentSettings()
    mock_build_config.return_value = mock_settings

    initialize_config()  # Default validate=True
    mock_validate.assert_called_once_with(verbose=False)


# Use patch to control the singleton value
@patch("code_agent.config.config.build_effective_config")
@patch("code_agent.config.settings_based_config.CodeAgentSettings.validate_dynamic")
@patch("code_agent.config.config._config", None)  # Ensure _config is None before test
def test_initialize_config_skips_validation(mock_validate, mock_build_config):
    """Test that initialize_config skips validation when validate=False."""
    mock_settings = CodeAgentSettings()
    mock_build_config.return_value = mock_settings

    initialize_config(validate=False)
    mock_validate.assert_not_called()
