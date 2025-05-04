"""
Tests for the config commands in code_agent.cli.main module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import app

# Need to import DEFAULT_CONFIG_PATH for use in assertions
from code_agent.config.settings_based_config import DEFAULT_CONFIG_PATH

# Import VerbosityLevel for controller check
from code_agent.verbosity import VerbosityLevel


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestConfigCommands:
    """Test class for the config commands."""

    def test_config_get_agent_path(self, runner):
        """Test get-agent-path command."""
        # Mock config with a default agent path
        mock_config = MagicMock()
        mock_config.default_agent_path = Path("code_agent/agent/multi_agent.py")

        # Patch where get_config is used within the command
        with patch("code_agent.cli.commands.config.get_config", return_value=mock_config):
            # Run the command
            result = runner.invoke(app, ["config", "get-agent-path"])

            # Check the result
            assert result.exit_code == 0
            assert str(mock_config.default_agent_path) in result.stdout

    def test_config_get_agent_path_none(self, runner):
        """Test get-agent-path command when no path is set."""
        # Mock config with no default agent path
        mock_config = MagicMock()
        mock_config.default_agent_path = None

        # Patch where get_config is used within the command
        with patch("code_agent.cli.commands.config.get_config", return_value=mock_config):
            # Run the command
            result = runner.invoke(app, ["config", "get-agent-path"])

            # Check the result
            assert result.exit_code == 0
            assert "No default agent path" in result.stdout

    @patch("code_agent.cli.commands.config.get_config")
    def test_config_show(self, mock_get_config, runner):
        """Test config show command."""
        # Mock config with sample values
        mock_config = MagicMock()
        mock_config.model_dump_json.return_value = '{"test": "config"}'
        mock_get_config.return_value = mock_config

        # Run the command
        result = runner.invoke(app, ["config", "show"])

        # Check the result
        assert result.exit_code == 0
        assert "Current Effective Configuration" in result.stdout
        assert mock_config.model_dump_json.called

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_openai_default_key_found(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config openai' when it's the default provider and key exists."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "openai"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = "sk-..."  # Simulate key found

        result = runner.invoke(app, ["config", "openai"])

        assert result.exit_code == 0
        assert "OpenAI Configuration" in result.stdout
        assert "✅ OpenAI is currently the default provider." in result.stdout
        assert "✅ OpenAI API key is configured" in result.stdout
        mock_get_api_key.assert_called_once_with("openai")

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_openai_not_default_key_missing(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config openai' when it's not default and key is missing."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "aistudio"  # Different default
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = None  # Simulate key not found

        result = runner.invoke(app, ["config", "openai"])

        assert result.exit_code == 0
        assert "OpenAI Configuration" in result.stdout
        assert "❌ OpenAI is NOT the default provider" in result.stdout
        assert "❌ No OpenAI API key found" in result.stdout
        mock_get_api_key.assert_called_once_with("openai")

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_aistudio_default_key_found(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config aistudio' when it's the default provider and key exists."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "ai_studio"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = "AIza..."  # Simulate key found

        result = runner.invoke(app, ["config", "aistudio"])

        assert result.exit_code == 0
        assert "Google AI Studio Configuration" in result.stdout
        assert "✅ AI Studio is currently the default provider." in result.stdout
        assert "✅ AI Studio API key is configured" in result.stdout
        mock_get_api_key.assert_called_once_with("ai_studio")

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_aistudio_not_default_key_missing(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config aistudio' when it's not default and key is missing."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "openai"  # Different default
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = None  # Simulate key not found

        result = runner.invoke(app, ["config", "aistudio"])

        assert result.exit_code == 0
        assert "Google AI Studio Configuration" in result.stdout
        assert "❌ AI Studio is NOT the default provider" in result.stdout
        assert "❌ No AI Studio API key found" in result.stdout
        mock_get_api_key.assert_called_once_with("ai_studio")

    # --- Add tests for groq --- #
    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_groq_default_key_found(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config groq' when it's the default provider and key exists."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "groq"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = "gsk-..."

        result = runner.invoke(app, ["config", "groq"])

        assert result.exit_code == 0
        assert "Groq Configuration" in result.stdout
        assert "✅ Groq is currently the default provider." in result.stdout
        assert "✅ Groq API key is configured" in result.stdout
        mock_get_api_key.assert_called_once_with("groq")

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_groq_not_default_key_missing(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config groq' when it's not default and key is missing."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "openai"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = None

        result = runner.invoke(app, ["config", "groq"])

        assert result.exit_code == 0
        assert "Groq Configuration" in result.stdout
        assert "❌ Groq is NOT the default provider" in result.stdout
        assert "❌ No Groq API key found" in result.stdout
        mock_get_api_key.assert_called_once_with("groq")

    # --- Add tests for anthropic --- #
    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_anthropic_default_key_found(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config anthropic' when it's the default provider and key exists."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "anthropic"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = "sk-ant-..."

        result = runner.invoke(app, ["config", "anthropic"])

        assert result.exit_code == 0
        assert "Anthropic Configuration" in result.stdout
        assert "✅ Anthropic is currently the default provider." in result.stdout
        assert "✅ Anthropic API key is configured" in result.stdout
        mock_get_api_key.assert_called_once_with("anthropic")

    @patch("code_agent.cli.commands.config.get_api_key")
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_anthropic_not_default_key_missing(self, mock_get_config, mock_get_api_key, runner):
        """Test 'config anthropic' when it's not default and key is missing."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "openai"
        mock_get_config.return_value = mock_config_obj
        mock_get_api_key.return_value = None

        result = runner.invoke(app, ["config", "anthropic"])

        assert result.exit_code == 0
        assert "Anthropic Configuration" in result.stdout
        assert "❌ Anthropic is NOT the default provider" in result.stdout
        assert "❌ No Anthropic API key found" in result.stdout
        mock_get_api_key.assert_called_once_with("anthropic")

    # --- Add tests for ollama --- #
    # Ollama doesn't use API keys, so tests are simpler
    @patch("code_agent.cli.commands.config.get_config")
    def test_config_ollama_default(self, mock_get_config, runner):
        """Test 'config ollama' when it's the default provider."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "ollama"
        mock_get_config.return_value = mock_config_obj

        result = runner.invoke(app, ["config", "ollama"])

        assert result.exit_code == 0
        assert "Ollama Configuration" in result.stdout
        assert "✅ Ollama is currently the default provider." in result.stdout

    @patch("code_agent.cli.commands.config.get_config")
    def test_config_ollama_not_default(self, mock_get_config, runner):
        """Test 'config ollama' when it's not default."""
        mock_config_obj = MagicMock()
        mock_config_obj.default_provider = "openai"
        mock_get_config.return_value = mock_config_obj

        result = runner.invoke(app, ["config", "ollama"])

        assert result.exit_code == 0
        assert "Ollama Configuration" in result.stdout
        assert "❌ Ollama is NOT the default provider" in result.stdout

    # --- Tests for config reset --- #
    @patch("code_agent.cli.commands.config.shutil.copy2")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_DIR")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_PATH")
    @patch("code_agent.cli.commands.config.TEMPLATE_CONFIG_PATH")
    def test_config_reset_success_no_existing(self, mock_template, mock_default_path, mock_default_dir, mock_copy, runner):
        """Test config reset when no config file exists."""
        mock_template.exists.return_value = True
        mock_default_path.exists.return_value = False  # No existing config

        result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 0
        mock_default_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_copy.assert_called_once_with(mock_template, mock_default_path)
        assert "Configuration reset to defaults" in result.stdout

    @patch("code_agent.cli.commands.config.shutil.copy2")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_DIR")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_PATH")
    @patch("code_agent.cli.commands.config.TEMPLATE_CONFIG_PATH")
    def test_config_reset_success_with_backup(self, mock_template, mock_default_path, mock_default_dir, mock_copy, runner):
        """Test config reset when config exists, including backup."""
        mock_template.exists.return_value = True
        mock_default_path.exists.return_value = True  # Existing config
        mock_backup_path = MagicMock(spec=Path)
        mock_default_path.with_suffix.return_value = mock_backup_path

        # Simulate successful copy for backup and reset
        mock_copy.side_effect = [None, None]  # First call for backup, second for reset

        result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 0
        mock_default_path.with_suffix.assert_called_once_with(".yaml.bak")
        assert mock_copy.call_count == 2
        mock_copy.assert_any_call(mock_default_path, mock_backup_path)  # Backup call
        mock_copy.assert_any_call(mock_template, mock_default_path)  # Reset call
        assert "Created backup" in result.stdout
        assert "Configuration reset to defaults" in result.stdout

    @patch("code_agent.cli.commands.config.shutil.copy2")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_DIR")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_PATH")
    @patch("code_agent.cli.commands.config.TEMPLATE_CONFIG_PATH")
    def test_config_reset_backup_fails(self, mock_template, mock_default_path, mock_default_dir, mock_copy, runner):
        """Test config reset when creating backup fails."""
        mock_template.exists.return_value = True
        mock_default_path.exists.return_value = True
        mock_copy.side_effect = [IOError("Disk full"), None]  # Fail backup, succeed reset

        result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 0  # Should still proceed with reset
        assert mock_copy.call_count == 2
        assert "Warning: Could not create backup" in result.stdout
        assert "Configuration reset to defaults" in result.stdout  # Reset should still happen

    @patch("code_agent.cli.commands.config.shutil.copy2")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_DIR")
    @patch("code_agent.cli.commands.config.DEFAULT_CONFIG_PATH")
    @patch("code_agent.cli.commands.config.TEMPLATE_CONFIG_PATH")
    def test_config_reset_template_copy_fails(self, mock_template, mock_default_path, mock_default_dir, mock_copy, runner):
        """Test config reset when copying the template fails."""
        mock_template.exists.return_value = True
        mock_default_path.exists.return_value = False
        mock_copy.side_effect = IOError("Permission denied")  # Fail template copy

        result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 1  # Should exit with error
        mock_default_dir.mkdir.assert_called_once()
        mock_copy.assert_called_once_with(mock_template, mock_default_path)
        assert "Error resetting configuration" in result.stdout

    @patch("code_agent.cli.commands.config.TEMPLATE_CONFIG_PATH")
    def test_config_reset_template_missing(self, mock_template, runner):
        """Test config reset when the template file is missing."""
        mock_template.exists.return_value = False

        result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 1
        assert "Template config file not found" in result.stdout

    # --- Tests for config validate --- #
    @patch("code_agent.cli.commands.config.get_config")  # Mock get_config first
    def test_config_validate_valid(self, mock_get_config, runner):
        """Test config validate when config is valid."""
        # Arrange
        mock_config_obj = MagicMock()
        mock_config_obj.validate_dynamic.return_value = True  # Simulate valid
        mock_get_config.return_value = mock_config_obj

        # Act
        result = runner.invoke(app, ["config", "validate"])

        # Assert
        assert result.exit_code == 0
        # validate_dynamic now handles printing, check if called correctly
        mock_config_obj.validate_dynamic.assert_called_once_with(verbose=True)
        # Check for the simple valid message printed when not verbose and valid
        # Note: validate_dynamic(verbose=True) is called, but the command
        # itself prints the simple message if verbose=False (default) and valid=True
        assert "✓ Configuration is valid." in result.stdout

    @patch("code_agent.cli.commands.config.get_config")  # Mock get_config first
    def test_config_validate_invalid(self, mock_get_config, runner):
        """Test config validate when config is invalid."""
        # Arrange
        mock_config_obj = MagicMock()
        mock_config_obj.validate_dynamic.return_value = False  # Simulate invalid
        mock_get_config.return_value = mock_config_obj

        # Act
        result = runner.invoke(app, ["config", "validate"])

        # Assert
        assert result.exit_code == 1  # Exit code should be 1
        # validate_dynamic handles printing errors/warnings when verbose=True
        mock_config_obj.validate_dynamic.assert_called_once_with(verbose=True)
        # Check for the final failure message from the command
        assert "Configuration validation failed." in result.stdout

    @patch("code_agent.cli.commands.config.get_config")  # Mock get_config to get a mock object
    def test_config_validate_valid_with_warnings_verbose(self, mock_get_config, runner):
        """Test config validate with warnings and verbose flag."""
        # Arrange
        mock_config_obj = MagicMock()
        # Mock the validate_dynamic method on the config object
        mock_config_obj.validate_dynamic.return_value = True  # Simulate valid config
        mock_get_config.return_value = mock_config_obj

        # Act
        result = runner.invoke(app, ["config", "validate", "--verbose"])

        # Assert
        assert result.exit_code == 0
        # Check that validate_dynamic was called with verbose=True
        mock_config_obj.validate_dynamic.assert_called_once_with(verbose=True)
        # Note: We don't assert specific print output here, as validate_dynamic handles it.
        # We just trust that if called with verbose=True, it prints what's needed.
        # We could potentially patch rich_print within validate_dynamic if needed,
        # but that becomes more complex.

    # --- Tests for config verbosity --- #
    @patch("code_agent.cli.commands.config.load_config_data")
    def test_config_verbosity_get(self, mock_load_config, runner):
        """Test getting the verbosity level."""
        mock_load_config.return_value = {"verbosity": 2}  # Simulate existing config

        result = runner.invoke(app, ["config", "verbosity"])

        assert result.exit_code == 0
        assert "Current verbosity level: 2 (VERBOSE)" in result.stdout
        mock_load_config.assert_called_once()

    @patch("code_agent.cli.commands.config.load_config_data")
    def test_config_verbosity_get_default(self, mock_load_config, runner):
        """Test getting verbosity when not explicitly set (uses default)."""
        mock_load_config.return_value = {}  # No verbosity in config

        result = runner.invoke(app, ["config", "verbosity"])

        assert result.exit_code == 0
        # Default verbosity is 1 (NORMAL) in CodeAgentSettings
        assert "Current verbosity level: 1 (NORMAL)" in result.stdout
        mock_load_config.assert_called_once()

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    @patch("code_agent.cli.commands.config.get_controller")  # Mock controller
    def test_config_verbosity_set_numeric(self, mock_get_controller, mock_load_config, mock_save_config, runner):
        """Test setting verbosity level using a number."""
        initial_config = {"default_provider": "test"}
        mock_load_config.return_value = initial_config
        mock_controller = MagicMock()
        mock_get_controller.return_value = mock_controller

        result = runner.invoke(app, ["config", "verbosity", "3"])

        assert result.exit_code == 0
        # Check for both output lines
        assert "Verbosity level set to 3 (DEBUG) in config file." in result.stdout
        assert "(Verbosity updated for current session)" in result.stdout
        mock_load_config.assert_called_once()
        expected_saved_config = initial_config.copy()
        expected_saved_config["verbosity"] = 3
        mock_save_config.assert_called_once_with(expected_saved_config, DEFAULT_CONFIG_PATH)
        # Check controller level was set
        assert mock_controller.level == VerbosityLevel.DEBUG

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    @patch("code_agent.cli.commands.config.get_controller")  # Mock controller
    def test_config_verbosity_set_string(self, mock_get_controller, mock_load_config, mock_save_config, runner):
        """Test setting verbosity level using a string name."""
        initial_config = {"api_keys": {"openai": "key"}}
        mock_load_config.return_value = initial_config
        mock_controller = MagicMock()
        mock_get_controller.return_value = mock_controller

        result = runner.invoke(app, ["config", "verbosity", "VERBOSE"])

        assert result.exit_code == 0
        # Check for both output lines
        assert "Verbosity level set to 2 (VERBOSE) in config file." in result.stdout
        assert "(Verbosity updated for current session)" in result.stdout
        mock_load_config.assert_called_once()
        expected_saved_config = initial_config.copy()
        expected_saved_config["verbosity"] = 2
        mock_save_config.assert_called_once_with(expected_saved_config, DEFAULT_CONFIG_PATH)
        # Check controller level was set
        assert mock_controller.level == VerbosityLevel.VERBOSE

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    def test_config_verbosity_set_invalid_string(self, mock_load_config, mock_save_config, runner):
        """Test setting verbosity level with an invalid string."""
        mock_load_config.return_value = {}

        result = runner.invoke(app, ["config", "verbosity", "SUPER_VERBOSE"])

        assert result.exit_code == 1  # Check for exit code 1
        assert "Invalid verbosity level" in result.stdout
        mock_load_config.assert_called_once()
        mock_save_config.assert_not_called()

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    def test_config_verbosity_set_invalid_number(self, mock_load_config, mock_save_config, runner):
        """Test setting verbosity level with an out-of-range number."""
        mock_load_config.return_value = {}

        result = runner.invoke(app, ["config", "verbosity", "5"])

        assert result.exit_code == 1  # Check for exit code 1
        assert "Invalid verbosity level" in result.stdout
        mock_load_config.assert_called_once()
        mock_save_config.assert_not_called()

    # --- Tests for config set-agent-path --- #
    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    @patch("code_agent.cli.commands.config.Path")  # Patch the Path class
    def test_config_set_agent_path_file_exists(self, mock_path_class, mock_load_config, mock_save_config, runner):
        """Test setting the agent path when the file exists."""
        initial_config = {"default_provider": "test"}
        mock_load_config.return_value = initial_config

        # Mock the Path object instance created within the command
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.resolve.return_value = Path("/absolute/path/to/my_agent.py")  # Mock resolve
        mock_path_class.return_value = mock_path_instance

        agent_path_str = "path/to/my_agent.py"
        result = runner.invoke(app, ["config", "set-agent-path", agent_path_str])

        assert result.exit_code == 0
        assert "Default agent path set to: /absolute/path/to/my_agent.py" in result.stdout
        mock_path_instance.exists.assert_called_once()
        mock_path_instance.resolve.assert_called_once()
        mock_load_config.assert_called_once_with(DEFAULT_CONFIG_PATH)
        expected_saved_config = initial_config.copy()
        expected_saved_config["default_agent_path"] = "/absolute/path/to/my_agent.py"
        mock_save_config.assert_called_once_with(expected_saved_config, DEFAULT_CONFIG_PATH)

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    @patch("code_agent.cli.commands.config.Path")  # Patch the Path class
    def test_config_set_agent_path_dir_exists(self, mock_path_class, mock_load_config, mock_save_config, runner):
        """Test setting the agent path when the directory exists."""
        initial_config = {"default_provider": "test"}
        mock_load_config.return_value = initial_config

        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.resolve.return_value = Path("/absolute/path/to/agent_dir")
        mock_path_class.return_value = mock_path_instance

        agent_path_str = "path/to/agent_dir"
        result = runner.invoke(app, ["config", "set-agent-path", agent_path_str])

        assert result.exit_code == 0
        assert "Default agent path set to: /absolute/path/to/agent_dir" in result.stdout
        mock_path_instance.exists.assert_called_once()
        mock_path_instance.resolve.assert_called_once()
        mock_load_config.assert_called_once_with(DEFAULT_CONFIG_PATH)
        expected_saved_config = initial_config.copy()
        expected_saved_config["default_agent_path"] = "/absolute/path/to/agent_dir"
        mock_save_config.assert_called_once_with(expected_saved_config, DEFAULT_CONFIG_PATH)

    @patch("code_agent.cli.commands.config.save_config_data")
    @patch("code_agent.cli.commands.config.load_config_data")
    @patch("code_agent.cli.commands.config.Path")  # Patch the Path class
    def test_config_set_agent_path_does_not_exist(self, mock_path_class, mock_load_config, mock_save_config, runner):
        """Test setting the agent path when the path does not exist."""
        # No need to mock initial_config or load_config as it shouldn't be called

        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = False  # Path doesn't exist
        # Set __str__ for the error message
        agent_path_str = "nonexistent/path/agent.py"
        mock_path_instance.__str__.return_value = agent_path_str
        mock_path_class.return_value = mock_path_instance

        result = runner.invoke(app, ["config", "set-agent-path", agent_path_str])

        assert result.exit_code == 1  # Should fail with exit code 1
        assert f"Error: Path not found: {agent_path_str}" in result.stdout
        mock_path_instance.exists.assert_called_once()
        mock_load_config.assert_not_called()
        mock_save_config.assert_not_called()


if __name__ == "__main__":
    pytest.main(["-v", "test_cli_config.py"])
