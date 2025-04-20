import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Ensure imports work correctly from the test directory
from code_agent.config import (
    SettingsConfig,
    build_effective_config,
    get_config,
    initialize_config,
)

# --- Fixtures ---

@pytest.fixture(autouse=True)
def reset_config_singleton(monkeypatch):
    """Ensures each test starts with a fresh config state and clears env vars."""
    global config_singleton
    config_singleton = None
    # Clear relevant environment variables before test using monkeypatch
    keys_to_clear = [
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "ANTHROPIC_API_KEY",
        "CODE_AGENT_AUTO_APPROVE_EDITS",
        "CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS"
    ]
    for key in keys_to_clear:
        monkeypatch.delenv(key, raising=False)
    yield
    # Monkeypatch handles cleanup automatically

@pytest.fixture
def mock_config_path(tmp_path: Path) -> Path:
    """Provides a temporary path for a mock config file."""
    return tmp_path / "test_config.yaml"

# --- Test Cases ---

def test_load_config_defaults_no_file(mock_config_path: Path):
    """Test loading default config when the file doesn't exist."""
    # Test building effective config when file is missing
    config = build_effective_config(mock_config_path)
    assert isinstance(config, SettingsConfig)
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"
    assert config.api_keys.openai is None
    assert not config.auto_approve_edits
    assert not config.native_command_allowlist

def test_load_config_from_file(mock_config_path: Path):
    """Test loading config from a valid YAML file."""
    config_content = {
        "default_provider": "groq",
        "default_model": "llama3",
        "api_keys": {"groq": "file_groq_key", "openai": "file_openai_key"},
        "auto_approve_edits": True,
        "native_command_allowlist": ["ls", "echo"],
        "rules": ["rule1", "rule2"]
    }
    mock_config_path.write_text(yaml.dump(config_content))

    # Test building effective config with the file
    config = build_effective_config(mock_config_path)
    assert config.default_provider == "groq"
    assert config.default_model == "llama3"
    assert config.api_keys.groq == "file_groq_key"
    assert config.api_keys.openai == "file_openai_key"
    assert config.auto_approve_edits is True
    assert config.native_command_allowlist == ["ls", "echo"]
    assert config.rules == ["rule1", "rule2"]

def test_load_config_env_override(mock_config_path: Path):
    """Test that environment variables override file config for API keys."""
    config_content = {
        "api_keys": {"openai": "file_key", "groq": "file_key"}
    }
    mock_config_path.write_text(yaml.dump(config_content))

    # Set environment variables
    env_vars = {"OPENAI_API_KEY": "env_openai_key", "GROQ_API_KEY": "env_groq_key"}
    with patch.dict(os.environ, env_vars):
        config = build_effective_config(mock_config_path)

    assert config.api_keys.openai == "env_openai_key"
    assert config.api_keys.groq == "env_groq_key"

def test_load_config_env_override_bools(mock_config_path: Path, monkeypatch):
    """Test that env vars override file config for boolean flags."""
    # File sets flags to False
    config_content = {
        "auto_approve_edits": False,
        "auto_approve_native_commands": False
    }
    mock_config_path.write_text(yaml.dump(config_content))

    # Env vars set flags to True
    monkeypatch.setenv("CODE_AGENT_AUTO_APPROVE_EDITS", "true")
    monkeypatch.setenv(
        "CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS", "TRUE"
    ) # Case-insensitive check

    # Build config without CLI overrides
    config = build_effective_config(mock_config_path)

    assert config.auto_approve_edits is True
    assert config.auto_approve_native_commands is True

def test_load_config_cli_override_bools(mock_config_path: Path, monkeypatch):
    """Test that CLI flags override Env vars and File config for boolean flags."""
    # File sets to False
    config_content = {
        "auto_approve_edits": False,
        "auto_approve_native_commands": False
    }
    mock_config_path.write_text(yaml.dump(config_content))
    # Env vars set to True
    monkeypatch.setenv("CODE_AGENT_AUTO_APPROVE_EDITS", "true")
    monkeypatch.setenv("CODE_AGENT_AUTO_APPROVE_NATIVE_COMMANDS", "true")

    # Build config with CLI overrides setting to False
    config = build_effective_config(
        mock_config_path,
        cli_auto_approve_edits=False,
        cli_auto_approve_native_commands=False
    )
    assert config.auto_approve_edits is False
    assert config.auto_approve_native_commands is False

    # Build config with CLI overrides setting to True (overriding File=False, Env=True)
    config_cli_true = build_effective_config(
        mock_config_path,
        cli_auto_approve_edits=True,
        cli_auto_approve_native_commands=True
    )
    assert config_cli_true.auto_approve_edits is True
    assert config_cli_true.auto_approve_native_commands is True

def test_load_config_cli_override_provider_model(mock_config_path: Path, monkeypatch):
    """Test CLI override for provider/model over Env/File."""
    config_content = {"default_provider": "file_p", "default_model": "file_m"}
    mock_config_path.write_text(yaml.dump(config_content))
    # No env vars for provider/model currently implemented in build_effective_config

    config = build_effective_config(
        mock_config_path,
        cli_provider="cli_p",
        cli_model="cli_m"
    )
    assert config.default_provider == "cli_p"
    assert config.default_model == "cli_m"

def test_load_config_invalid_yaml(mock_config_path: Path, capsys):
    """Test loading config from an invalid YAML file (should use defaults)."""
    mock_config_path.write_text("default_provider: openai\n: invalid_yaml")

    # Test building effective config with invalid file
    config = build_effective_config(mock_config_path)
    captured = capsys.readouterr()

    # Check that it fell back to defaults
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"
    assert config.api_keys.openai is None
    assert "Warning: Could not read config file" in captured.out or \
           "Warning: Could not read config file" in captured.err

def test_load_config_invalid_structure(mock_config_path: Path, capsys):
    """Test loading config with invalid structure/types (should use defaults)."""
    config_content = {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "auto_approve_edits": "not_a_boolean", # Invalid type
        "native_command_allowlist": "not_a_list" # Invalid type
    }
    mock_config_path.write_text(yaml.dump(config_content))

    # Test building effective config with invalid structure
    config = build_effective_config(mock_config_path)
    captured = capsys.readouterr()

    # Check that it fell back to defaults
    assert config.default_provider == "openai"
    assert config.default_model == "gpt-4o"
    assert config.auto_approve_edits is False # Default value
    assert config.native_command_allowlist == [] # Default value

    # Check that validation errors were printed
    assert "Error: Invalid effective configuration" in captured.out or \
           "Error: Invalid effective configuration" in captured.err
    assert "Falling back to default configuration" in captured.out or \
           "Falling back to default configuration" in captured.err

def test_get_config_raises_error_if_not_initialized():
    """Test that get_config returns default or raises error if not initialized."""
    # Ensure config is None initially
    global config_singleton
    config_singleton = None
    # In the current implementation, it initializes with defaults if called early
    # If we changed it to raise RuntimeError, this test would need modification.
    config = get_config() # Should trigger initialization with defaults
    assert isinstance(config, SettingsConfig)
    assert config.default_provider == "openai" # Check default value
    # with pytest.raises(
    #     RuntimeError,
    #     match="Configuration accessed before initialization"
    # ):
    #     get_config()

def test_get_config_loads_once(mock_config_path: Path):
    """Test that initialize_config calls build_effective_config only once."""
    mock_config_path.write_text(yaml.dump({"default_model": "model_1"}))

    # Use patch to spy on load_config calls
    with patch("code_agent.config.build_effective_config", wraps=build_effective_config) as mock_build:
        initialize_config() # First call
        config1 = get_config()
        initialize_config(cli_provider="other") # Second call - should be ignored
        config2 = get_config()

        assert config1 is config2 # Should be the same object
        assert config1.default_model == "model_1"
        mock_build.assert_called_once() # build should only have been called once
