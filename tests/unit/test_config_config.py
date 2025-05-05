"""Unit tests for code_agent.config.config module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from code_agent.config.config import (
    DEFAULT_CONFIG_DIR,
    TEMPLATE_CONFIG_PATH,
    get_api_key,
    get_config,
    initialize_config,
    validate_config,
)


class TestConfigModule(unittest.TestCase):
    """Test the config module functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global _config before each test
        self._reset_config_patcher = patch("code_agent.config.config._config", None)
        self._reset_config_patcher.start()
        self.addCleanup(self._reset_config_patcher.stop)

    def test_default_paths(self):
        """Test the default path constants."""
        # Verify DEFAULT_CONFIG_DIR
        self.assertEqual(DEFAULT_CONFIG_DIR, Path.home() / ".config" / "code-agent")

        # Verify TEMPLATE_CONFIG_PATH
        self.assertEqual(TEMPLATE_CONFIG_PATH, Path(__file__).parent.parent.parent / "code_agent" / "config" / "config_template.yaml")
        self.assertTrue(TEMPLATE_CONFIG_PATH.exists(), "Template config file should exist")

    @patch("code_agent.config.config.build_effective_config")
    @patch("code_agent.config.config.rich_print")
    def test_initialize_config(self, mock_rich_print, mock_build_config):
        """Test initializing configuration."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.validate_dynamic.return_value = True
        mock_build_config.return_value = mock_config

        # Call initialize_config
        initialize_config()

        # Verify build_effective_config was called with the default args
        mock_build_config.assert_called_once()

        # Verify validation was called
        mock_config.validate_dynamic.assert_called_once_with(verbose=False)

        # Verify rich_print was not called (no warnings)
        mock_rich_print.assert_not_called()

    @patch("code_agent.config.config.build_effective_config")
    def test_initialize_config_with_params(self, mock_build_config):
        """Test initializing configuration with parameters."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.validate_dynamic.return_value = True
        mock_build_config.return_value = mock_config

        # Call initialize_config with parameters
        custom_path = Path("/custom/config.yaml")
        initialize_config(
            config_file_path=custom_path,
            cli_provider="test_provider",
            cli_model="test_model",
            cli_agent_path=Path("/custom/agent"),
            cli_auto_approve_edits=True,
            cli_auto_approve_native_commands=True,
            cli_log_level="DEBUG",
            cli_verbose=True,
            force_reinit=True,
            validate=True,
        )

        # Verify build_effective_config was called with the custom args
        mock_build_config.assert_called_once_with(
            config_file_path=custom_path,
            cli_provider="test_provider",
            cli_model="test_model",
            cli_agent_path=Path("/custom/agent"),
            cli_auto_approve_edits=True,
            cli_auto_approve_native_commands=True,
            cli_log_level="DEBUG",
            cli_verbose=True,
        )

        # Verify validation was called
        mock_config.validate_dynamic.assert_called_once_with(verbose=False)

    @patch("code_agent.config.config.build_effective_config")
    def test_initialize_config_without_validation(self, mock_build_config):
        """Test initializing configuration without validation."""
        # Setup mock config
        mock_config = MagicMock()
        mock_build_config.return_value = mock_config

        # Call initialize_config with validate=False
        initialize_config(validate=False)

        # Verify validation was not called
        mock_config.validate_dynamic.assert_not_called()

    @patch("code_agent.config.config.build_effective_config")
    @patch("code_agent.config.config._config", MagicMock())  # Already initialized
    def test_initialize_config_already_initialized(self, mock_build_config):
        """Test initializing configuration when already initialized."""
        # Call initialize_config
        initialize_config()

        # Verify build_effective_config was not called
        mock_build_config.assert_not_called()

    @patch("code_agent.config.config.build_effective_config")
    @patch("code_agent.config.config._config", MagicMock())  # Already initialized
    def test_initialize_config_force_reinit(self, mock_build_config):
        """Test forcing reinitialization of configuration."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.validate_dynamic.return_value = True
        mock_build_config.return_value = mock_config

        # Call initialize_config with force_reinit=True
        initialize_config(force_reinit=True)

        # Verify build_effective_config was called
        mock_build_config.assert_called_once()

    @patch("code_agent.config.config.initialize_config")
    @patch("code_agent.config.config.rich_print")
    @patch("code_agent.config.config._config", None)  # Not initialized
    def test_get_config_not_initialized(self, mock_rich_print, mock_initialize_config):
        """Test getting configuration when not initialized."""
        # Setup mock config
        mock_config = MagicMock()

        # Make initialize_config actually set the _config global
        def set_config(*args, **kwargs):
            import code_agent.config.config

            code_agent.config.config._config = mock_config
            return mock_config

        mock_initialize_config.side_effect = set_config

        # Call get_config
        result = get_config()

        # Verify it was initialized properly
        mock_initialize_config.assert_called_once()
        self.assertIs(result, mock_config)

    @patch("code_agent.config.config._config", MagicMock())  # Already initialized
    def test_get_config_already_initialized(self):
        """Test getting configuration when already initialized."""
        # Get the mock config object
        mock_config = get_config.__globals__["_config"]

        # Call get_config
        result = get_config()

        # Verify result
        self.assertEqual(result, mock_config)

    @patch("code_agent.config.config.initialize_config")
    @patch("code_agent.config.config._config", None)  # Not initialized
    def test_get_config_initialization_failure(self, mock_initialize_config):
        """Test getting configuration when initialization fails."""
        # Setup initialization to not set _config
        mock_initialize_config.return_value = None

        # Call get_config and expect RuntimeError
        with self.assertRaises(RuntimeError):
            get_config()

    @patch("code_agent.config.config.get_config")
    def test_get_api_key_valid_provider(self, mock_get_config):
        """Test getting API key for a valid provider."""
        # Setup mock config with a properly structured ApiKeys object
        mock_config = MagicMock()
        # Create a properly mocked api_keys with the correct property behavior
        api_keys_instance = MagicMock()

        # Instead of trying to modify __name__ attribute of immutable type
        # Check for isinstance directly in the code
        # Mock the behavior of isinstance check
        mock_config.api_keys = api_keys_instance

        # Define the openai property directly
        type(api_keys_instance).openai = PropertyMock(return_value="sk-test-key")
        mock_get_config.return_value = mock_config

        # Mock the isinstance check to return True for ApiKeys
        with patch("code_agent.config.config.isinstance", lambda obj, cls: True if obj is api_keys_instance else isinstance(obj, cls)):
            # Call get_api_key
            result = get_api_key("openai")

            # Verify result
            self.assertEqual(result, "sk-test-key")

    @patch("code_agent.config.config.get_config")
    def test_get_api_key_invalid_provider(self, mock_get_config):
        """Test getting API key for an invalid provider."""
        # Setup mock config
        mock_config = MagicMock()
        mock_api_keys = MagicMock()
        # No attribute for 'invalid_provider'
        mock_api_keys.openai = "sk-test-key"
        # getattr will return None for non-existent attribute
        mock_config.api_keys = mock_api_keys
        mock_get_config.return_value = mock_config

        # Call get_api_key
        result = get_api_key("invalid_provider")

        # Verify result
        self.assertIsNone(result)

    @patch("code_agent.config.config.get_config")
    @patch("code_agent.config.config.rich_print")
    def test_get_api_key_invalid_api_keys(self, mock_rich_print, mock_get_config):
        """Test getting API key when api_keys is not an ApiKeys instance."""
        # Setup mock config with invalid api_keys
        mock_config = MagicMock()
        mock_config.api_keys = "not_an_ApiKeys_instance"
        mock_get_config.return_value = mock_config

        # Call get_api_key
        result = get_api_key("openai")

        # Verify warning was printed
        mock_rich_print.assert_called_once()
        self.assertIn("Warning", mock_rich_print.call_args[0][0])
        self.assertIn("not an ApiKeys instance", mock_rich_print.call_args[0][0])

        # Verify result
        self.assertIsNone(result)

    @patch("code_agent.config.config.get_config")
    def test_validate_config(self, mock_get_config):
        """Test validating configuration."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.validate_dynamic.return_value = True
        mock_get_config.return_value = mock_config

        # Call validate_config
        result = validate_config(verbose=True)

        # Verify validation was called
        mock_config.validate_dynamic.assert_called_once_with(verbose=True)

        # Verify result
        self.assertTrue(result)
