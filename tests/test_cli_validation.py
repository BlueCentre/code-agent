"""End-to-end tests for the configuration validation CLI command."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from code_agent.cli.main import app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_path(tmp_path: Path) -> Path:
    """Provides a temporary path for a mock config file."""
    return tmp_path / "config.yaml"


@pytest.fixture
def setup_env_config_path(monkeypatch, mock_config_path):
    """Set up environment to use the mock config file."""
    monkeypatch.setenv("CODE_AGENT_CONFIG_PATH", str(mock_config_path))
    return mock_config_path


def test_validate_valid_config(runner, setup_env_config_path):
    """Test validation with a valid configuration."""
    # Create a valid config file
    config_content = {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "api_keys": {"openai": "sk-" + "a" * 48},
        "auto_approve_edits": False,
        "auto_approve_native_commands": False,
        "native_command_allowlist": ["git status", "ls -la", "python -m tests"],
        "rules": ["rule1", "rule2"],
    }
    setup_env_config_path.write_text(yaml.dump(config_content))

    # Mock the validate_config function to return True and capture calls
    with patch("code_agent.config.config.validate_config") as mock_validate:
        mock_validate.return_value = True

        # Run the CLI command
        result = runner.invoke(app, ["config", "validate"])

        # Verify the command was successful
        assert result.exit_code == 0
        assert mock_validate.called


def test_validate_config_with_warnings(runner, setup_env_config_path):
    """Test validation with a config that has warnings."""
    # Create a config file with potential warnings (auto-approve flags)
    config_content = {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "api_keys": {"openai": "sk-" + "a" * 48},
        "auto_approve_edits": True,  # This will generate a warning
        "auto_approve_native_commands": True,  # This will generate a warning
        "native_command_allowlist": ["ls"],  # This will generate a warning (short command)
    }
    setup_env_config_path.write_text(yaml.dump(config_content))

    # Run the CLI command with verbose flag to see all warnings
    result = runner.invoke(app, ["config", "validate", "--verbose"])

    # Command should still succeed with warnings
    assert result.exit_code == 0

    # Check output for warning messages
    assert "warning" in result.stdout.lower() or "⚠️" in result.stdout


def test_validate_config_with_errors(runner, setup_env_config_path):
    """Test validation with a config that has errors."""
    # Create a config file with validation errors (invalid model)
    config_content = {
        "default_provider": "openai",
        "default_model": "invalid-model-name",  # Invalid model
        "api_keys": {"openai": "sk-" + "a" * 48},
    }
    setup_env_config_path.write_text(yaml.dump(config_content))

    # Mock the validate_config function to return False (indicating errors)
    with patch("code_agent.config.config.validate_config") as mock_validate:
        mock_validate.return_value = False

        # Run the CLI command
        result = runner.invoke(app, ["config", "validate"])

        # Verify command exited with error code
        assert result.exit_code == 1
        assert mock_validate.called


def test_validate_command_integration(runner, tmp_path):
    """Test actual integration of validation command (no mocks)."""
    # Set up config dir and file
    config_dir = tmp_path / ".config" / "code-agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"

    # Create a config with both warnings and an error
    config_content = {
        "default_provider": "ai_studio",
        "default_model": "invalid-model-name",  # Error - invalid model
        "auto_approve_edits": True,  # Warning
        "native_command_allowlist": ["rm"],  # Warning - short command
    }
    config_path.write_text(yaml.dump(config_content))

    # Patch DEFAULT_CONFIG_PATH directly to use our test file
    with patch("code_agent.config.config.DEFAULT_CONFIG_PATH", config_path):
        # Run validate command
        result = runner.invoke(app, ["config", "validate"])

        # Check that validation found issues
        assert "model" in result.stdout.lower()
        assert "invalid-model-name" in result.stdout

        # For warnings
        assert "warning" in result.stdout.lower() or "⚠️" in result.stdout
