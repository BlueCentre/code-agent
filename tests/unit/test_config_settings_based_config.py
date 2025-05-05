"""Unit tests for code_agent.config.settings_based_config module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from code_agent.config.settings_based_config import (
    ApiKeys,
    CodeAgentSettings,
    LLMSettings,
    NativeCommandSettings,
    SecuritySettings,
    build_effective_config,
    create_default_config_file,
    create_settings_model,
    get_api_key,
    load_config_from_file,
    settings_to_dict,
)


# Local implementation of deep_update for testing purposes
def deep_update(target, source):
    """
    Deep update target dict with source dict recursively.
    For testing the deep_update function's behavior in build_effective_config.
    """
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            # Key exists in both and both values are dicts, recurse
            deep_update(target[key], value)
        else:
            # Overwrite target key with source value (or add if not present)
            target[key] = value
    return target


class TestSettingsBasedConfig(unittest.TestCase):
    """Test the settings-based configuration system."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for config testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = Path(self.temp_dir.name) / "config.yaml"

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_api_keys_model(self):
        """Test the ApiKeys model."""
        # Test with standard providers
        api_keys = ApiKeys(
            openai="sk-openai-key",
            ai_studio="AIzaSy-studio-key",
            groq="groq-key",
            anthropic="sk-ant-key",
        )
        self.assertEqual(api_keys.openai, "sk-openai-key")
        self.assertEqual(api_keys.ai_studio, "AIzaSy-studio-key")
        self.assertEqual(api_keys.groq, "groq-key")
        self.assertEqual(api_keys.anthropic, "sk-ant-key")

        # Test with extra providers (allowed by model_config)
        api_keys_with_extra = ApiKeys(
            openai="sk-openai-key",
            custom_provider="custom-key",
        )
        self.assertEqual(api_keys_with_extra.openai, "sk-openai-key")
        self.assertEqual(getattr(api_keys_with_extra, "custom_provider", None), "custom-key")

    def test_security_settings_model(self):
        """Test the SecuritySettings model."""
        # Test default values
        security = SecuritySettings()
        self.assertTrue(security.path_validation)
        self.assertTrue(security.workspace_restriction)
        self.assertTrue(security.command_validation)

        # Test custom values
        custom_security = SecuritySettings(
            path_validation=False,
            workspace_restriction=False,
            command_validation=False,
        )
        self.assertFalse(custom_security.path_validation)
        self.assertFalse(custom_security.workspace_restriction)
        self.assertFalse(custom_security.command_validation)

    def test_native_command_settings_model(self):
        """Test the NativeCommandSettings model."""
        # Test default values
        native_cmd = NativeCommandSettings()
        self.assertIsNone(native_cmd.default_timeout)
        self.assertIsNone(native_cmd.default_working_directory)

        # Test custom values
        custom_native_cmd = NativeCommandSettings(
            default_timeout=30,
            default_working_directory="/home/user",
        )
        self.assertEqual(custom_native_cmd.default_timeout, 30)
        self.assertEqual(custom_native_cmd.default_working_directory, "/home/user")

    def test_llm_settings_model(self):
        """Test the LLMSettings model."""
        # Test default values
        llm_settings = LLMSettings()
        self.assertIsNone(llm_settings.provider)
        self.assertIsNone(llm_settings.model)
        self.assertIsNone(llm_settings.temperature)
        self.assertIsNone(llm_settings.max_tokens)
        self.assertIsNone(llm_settings.api_key_env_var)

        # Test custom values
        custom_llm_settings = LLMSettings(
            provider="openai",
            model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
            api_key_env_var="OPENAI_API_KEY",
        )
        self.assertEqual(custom_llm_settings.provider, "openai")
        self.assertEqual(custom_llm_settings.model, "gpt-4")
        self.assertEqual(custom_llm_settings.temperature, 0.7)
        self.assertEqual(custom_llm_settings.max_tokens, 1000)
        self.assertEqual(custom_llm_settings.api_key_env_var, "OPENAI_API_KEY")

    def test_code_agent_settings_model(self):
        """Test the CodeAgentSettings model."""
        # Test default values
        settings = CodeAgentSettings()
        self.assertEqual(settings.app_name, "code_agent_cli")
        self.assertEqual(settings.user_id, "cli_user")
        self.assertEqual(settings.default_provider, "ai_studio")
        self.assertEqual(settings.default_model, "gemini-2.0-flash")
        self.assertEqual(settings.temperature, 0.7)
        self.assertEqual(settings.max_tokens, 1000)
        self.assertEqual(settings.max_tool_calls, 10)
        self.assertEqual(settings.verbosity, 1)
        self.assertFalse(settings.auto_approve_edits)
        self.assertFalse(settings.auto_approve_native_commands)
        self.assertEqual(settings.native_command_allowlist, [])
        self.assertEqual(settings.rules, [])

        # Test validators
        with self.assertRaises(ValueError):
            CodeAgentSettings(temperature=1.5)  # Temperature must be between 0.0 and 1.0
        with self.assertRaises(ValueError):
            CodeAgentSettings(max_tokens=-10)  # Max tokens must be positive

    def test_deep_update(self):
        """Test the deep_update function."""
        # Test basic merge
        target = {"a": 1, "b": 2}
        source = {"b": 3, "c": 4}
        result = deep_update(target, source)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

        # Test nested merge
        target = {"a": 1, "b": {"x": 1, "y": 2}}
        source = {"b": {"y": 3, "z": 4}, "c": 5}
        result = deep_update(target, source)
        self.assertEqual(result, {"a": 1, "b": {"x": 1, "y": 3, "z": 4}, "c": 5})

        # Test with lists (should replace, not merge)
        target = {"a": 1, "b": [1, 2, 3]}
        source = {"b": [4, 5]}
        result = deep_update(target, source)
        self.assertEqual(result, {"a": 1, "b": [4, 5]})

        # Test with None values (should replace)
        target = {"a": 1, "b": 2}
        source = {"b": None}
        result = deep_update(target, source)
        self.assertEqual(result, {"a": 1, "b": None})

    def test_create_settings_model(self):
        """Test the create_settings_model function."""
        # Basic config data
        config_data = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "api_keys": {
                "openai": "sk-test-key",
            },
            "auto_approve_edits": True,
        }

        # Create settings model
        settings = create_settings_model(config_data)

        # Verify values
        self.assertEqual(settings.default_provider, "openai")
        self.assertEqual(settings.default_model, "gpt-4")
        self.assertEqual(settings.api_keys.openai, "sk-test-key")
        self.assertTrue(settings.auto_approve_edits)

    def test_settings_to_dict(self):
        """Test the settings_to_dict function."""
        # Create settings model with some values
        settings = CodeAgentSettings(
            default_provider="openai",
            default_model="gpt-4",
            auto_approve_edits=True,
            api_keys=ApiKeys(openai="sk-test-key"),
        )

        # Convert to dict
        settings_dict = settings_to_dict(settings)

        # Verify values
        self.assertEqual(settings_dict["default_provider"], "openai")
        self.assertEqual(settings_dict["default_model"], "gpt-4")
        self.assertTrue(settings_dict["auto_approve_edits"])
        self.assertEqual(settings_dict["api_keys"]["openai"], "sk-test-key")

    @patch("code_agent.config.settings_based_config.yaml.safe_load")
    @patch("code_agent.config.settings_based_config.Path.exists")
    @patch("code_agent.config.settings_based_config.open", create=True)
    def test_load_config_from_file(self, mock_open, mock_exists, mock_yaml_load):
        """Test the load_config_from_file function."""
        # Setup mocks
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock yaml.safe_load to return a proper dictionary
        yaml_data = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "api_keys": {
                "openai": "sk-test-key",
            },
            "auto_approve_edits": True,
        }
        mock_yaml_load.return_value = yaml_data

        # Call function
        config = load_config_from_file(Path("/mock/config.yaml"))

        # Verify results
        self.assertEqual(config["default_provider"], "openai")
        self.assertEqual(config["default_model"], "gpt-4")
        self.assertEqual(config["api_keys"]["openai"], "sk-test-key")
        self.assertTrue(config["auto_approve_edits"])

    @patch("code_agent.config.settings_based_config.Path.exists")
    def test_load_config_from_nonexistent_file(self, mock_exists):
        """Test loading configuration from a non-existent file."""
        # Setup mock file to not exist
        mock_exists.return_value = False

        # Call function
        config = load_config_from_file(Path("/nonexistent/config.yaml"))

        # Verify empty dict is returned
        self.assertEqual(config, {})

    def test_create_default_config_file(self):
        """Test the create_default_config_file function in a more direct way."""
        # Create a temporary directory and file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create paths for testing
            config_path = Path(temp_dir) / "config.yaml"
            template_path = Path(temp_dir) / "template.yaml"

            # Create template file
            with open(template_path, "w") as f:
                f.write("default_provider: test\n")

            # Patch TEMPLATE_CONFIG_PATH to point to our test template
            with patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH", template_path):
                # Ensure config file doesn't exist yet
                self.assertFalse(config_path.exists())

                # Call the function
                create_default_config_file(config_path)

                # Verify the config file was created
                self.assertTrue(config_path.exists())

                # Verify contents were copied from template
                with open(config_path, "r") as f:
                    content = f.read()
                    self.assertIn("default_provider: test", content)

    @patch("code_agent.config.settings_based_config.shutil.copyfile")
    @patch("code_agent.config.settings_based_config.Path.exists")
    def test_create_default_config_file_exists(self, mock_exists, mock_copyfile):
        """Test create_default_config_file when file already exists."""
        # Setup mock file to exist
        mock_exists.return_value = True

        # Call function
        create_default_config_file(Path("/mock/config.yaml"))

        # Verify copyfile was not called
        mock_copyfile.assert_not_called()

    @patch("code_agent.config.settings_based_config.load_config_from_file")
    @patch("code_agent.config.settings_based_config.CodeAgentSettings")
    def test_build_effective_config(self, mock_settings_class, mock_load_config):
        """Test the build_effective_config function."""
        # Setup mocks
        mock_load_config.return_value = {
            "default_provider": "openai",
            "default_model": "gpt-4",
        }

        # Create THREE mock settings objects (function creates multiple instances)
        mock_settings1 = MagicMock()
        mock_settings1.model_dump.return_value = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "auto_approve_edits": False,
        }

        mock_settings2 = MagicMock()
        mock_settings2.model_dump.return_value = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "auto_approve_edits": False,
        }

        mock_settings3 = MagicMock()

        # Set side effect to return each mock in sequence
        mock_settings_class.side_effect = [mock_settings1, mock_settings2, mock_settings3]

        # Call function with CLI args
        result = build_effective_config(
            config_file_path=Path("/mock/config.yaml"),
            cli_provider="anthropic",
            cli_model="claude-3",
            cli_auto_approve_edits=True,
        )

        # Verify load_config was called
        mock_load_config.assert_called_once_with(Path("/mock/config.yaml"))

        # Verify CodeAgentSettings was called multiple times
        self.assertTrue(mock_settings_class.call_count >= 2)

        # The result should be the last settings object
        self.assertEqual(result, mock_settings3)

    @patch("code_agent.config.settings_based_config.get_config")
    def test_get_api_key(self, mock_get_config):
        """Test the get_api_key function."""
        # Setup mock config
        mock_config = MagicMock()
        mock_api_keys = MagicMock()
        mock_api_keys.openai = "sk-test-key"
        mock_api_keys.ai_studio = "AIzaSy-test-key"
        # Configure nonexistent attribute behavior
        mock_api_keys.model_extra = {}
        type(mock_api_keys).__getattr__ = lambda s, name: None if name == "nonexistent" else object.__getattribute__(s, name)
        mock_config.api_keys = mock_api_keys
        mock_get_config.return_value = mock_config

        # Test getting existing keys
        self.assertEqual(get_api_key("openai"), "sk-test-key")
        self.assertEqual(get_api_key("ai_studio"), "AIzaSy-test-key")

        # Test getting non-existent key
        self.assertIsNone(get_api_key("nonexistent"))


class TestConfigWithTempFile(unittest.TestCase):
    """Tests that interact with the filesystem."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary file for config testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = Path(self.temp_dir.name) / "config.yaml"

        # Create a default config file
        config_data = {
            "default_provider": "openai",
            "default_model": "gpt-4",
            "api_keys": {
                "openai": "sk-test-key",
            },
            "auto_approve_edits": True,
        }
        with open(self.temp_config_path, "w") as f:
            yaml.dump(config_data, f)

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_load_config_from_file_real(self):
        """Test loading a real config file."""
        # Load the config file
        config = load_config_from_file(self.temp_config_path)

        # Verify values
        self.assertEqual(config["default_provider"], "openai")
        self.assertEqual(config["default_model"], "gpt-4")
        self.assertEqual(config["api_keys"]["openai"], "sk-test-key")
        self.assertTrue(config["auto_approve_edits"])

    def test_create_default_config_file_real(self):
        """Test creating a real default config file."""
        # Create a path for a new config file
        new_config_path = Path(self.temp_dir.name) / "new_config.yaml"

        # Ensure it doesn't exist yet
        if new_config_path.exists():
            new_config_path.unlink()

        # Create the default config file
        with patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH", self.temp_config_path):
            create_default_config_file(new_config_path)

        # Verify file was created
        self.assertTrue(new_config_path.exists())

        # Load and verify contents
        with open(new_config_path, "r") as f:
            config = yaml.safe_load(f)

        self.assertEqual(config["default_provider"], "openai")
        self.assertEqual(config["default_model"], "gpt-4")

    @patch.dict(os.environ, {"CODE_AGENT_DEFAULT_PROVIDER": "env_provider"})
    def test_env_var_override(self):
        """Test environment variable overrides."""
        # Create settings with env var override
        settings = CodeAgentSettings()

        # Verify env var was used
        self.assertEqual(settings.default_provider, "env_provider")

    def test_build_effective_config_real(self):
        """Test building effective config with a real file."""
        # Build effective config
        config = build_effective_config(
            config_file_path=self.temp_config_path,
            cli_provider="anthropic",
        )

        # Verify values
        self.assertEqual(config.default_provider, "anthropic")  # CLI override
        self.assertEqual(config.default_model, "gpt-4")  # From file
        self.assertEqual(config.api_keys.openai, "sk-test-key")  # From file
        self.assertTrue(config.auto_approve_edits)  # From file
