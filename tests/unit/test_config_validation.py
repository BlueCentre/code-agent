"""Unit tests for code_agent.config.validation module."""

import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from code_agent.config.validation import (
    ValidationResult,
    print_validation_result,
    validate_api_keys,
    validate_config,
    validate_model_compatibility,
    validate_native_command_allowlist,
    validate_native_command_settings,
)


class TestValidationResult(unittest.TestCase):
    """Test the ValidationResult class."""

    def test_init(self):
        """Test the initializer."""
        result = ValidationResult()
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertTrue(result.valid)

    def test_add_error(self):
        """Test adding an error."""
        result = ValidationResult()
        result.add_error("Error message")
        self.assertEqual(result.errors, ["Error message"])
        self.assertFalse(result.valid)

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("Warning message")
        self.assertEqual(result.warnings, ["Warning message"])
        self.assertTrue(result.valid)  # Warnings don't affect validity

    def test_str_valid_no_warnings(self):
        """Test the string representation with a valid result and no warnings."""
        result = ValidationResult()
        self.assertEqual(str(result), "Configuration is valid.")

    def test_str_with_errors(self):
        """Test the string representation with errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")
        self.assertIn("Found 2 error(s):", str(result))
        self.assertIn("1. Error 1", str(result))
        self.assertIn("2. Error 2", str(result))

    def test_str_with_warnings(self):
        """Test the string representation with warnings."""
        result = ValidationResult()
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")
        self.assertIn("Found 2 warning(s):", str(result))
        self.assertIn("1. Warning 1", str(result))
        self.assertIn("2. Warning 2", str(result))

    def test_str_with_errors_and_warnings(self):
        """Test the string representation with both errors and warnings."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        self.assertIn("Found 1 error(s):", str(result))
        self.assertIn("1. Error 1", str(result))
        self.assertIn("Found 1 warning(s):", str(result))
        self.assertIn("1. Warning 1", str(result))


class TestModelCompatibilityValidation(unittest.TestCase):
    """Test the validate_model_compatibility function."""

    def test_validate_known_provider_and_model(self):
        """Test validating a known provider and model."""
        result = ValidationResult()
        # Choose a known provider and model from PROVIDER_MODEL_MAP
        provider = "openai"
        model = "gpt-4"

        validate_model_compatibility(provider, model, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_unknown_provider(self):
        """Test validating an unknown provider."""
        result = ValidationResult()
        provider = "unknown_provider"
        model = "some_model"

        validate_model_compatibility(provider, model, result)

        self.assertTrue(result.valid)  # Unknown provider is just a warning
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("Unknown provider", result.warnings[0])

    def test_validate_unknown_model(self):
        """Test validating an unknown model for a known provider."""
        result = ValidationResult()
        provider = "openai"
        model = "unknown_model"

        validate_model_compatibility(provider, model, result)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Model 'unknown_model' is not recognized for provider 'openai'", result.errors[0])

    def test_validate_openai_special_models(self):
        """Test validating special OpenAI models (fine-tuned, vision, etc.)."""
        result = ValidationResult()
        provider = "openai"

        # Test fine-tuned model
        validate_model_compatibility(provider, "ft:model-123", result)
        self.assertTrue(result.valid)

        # Test vision model
        result = ValidationResult()
        validate_model_compatibility(provider, "gpt-4-vision-123", result)
        self.assertTrue(result.valid)

        # Test 32k model
        result = ValidationResult()
        validate_model_compatibility(provider, "gpt-4-32k", result)
        self.assertTrue(result.valid)


class TestApiKeysValidation(unittest.TestCase):
    """Test the validate_api_keys function."""

    def test_validate_empty_api_keys(self):
        """Test validating empty API keys."""
        result = ValidationResult()
        api_keys = {}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("API key for default provider 'openai' is missing", result.errors[0])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("No API keys found", result.warnings[0])

    def test_validate_missing_default_provider_key(self):
        """Test validating API keys with missing default provider key."""
        result = ValidationResult()
        api_keys = {"anthropic": "sk-ant-1234567890abcdef1234567890abcdef"}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("API key for default provider 'openai' is missing", result.errors[0])

    def test_validate_api_keys_with_dict(self):
        """Test validating API keys with a dictionary."""
        result = ValidationResult()
        api_keys = {"openai": "sk-1234567890abcdef1234567890abcdef", "ai_studio": "AIzaSyCDa123456789012345678901234567890123"}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_api_keys_with_pydantic_model(self):
        """Test validating API keys with a Pydantic-like model."""
        result = ValidationResult()
        api_keys = MagicMock()
        api_keys.model_dump.return_value = {"openai": "sk-1234567890abcdef1234567890abcdef", "ai_studio": "AIzaSyCDa123456789012345678901234567890123"}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_api_keys_with_fallback(self):
        """Test validating API keys with fallback to vars."""
        result = ValidationResult()
        api_keys = MagicMock()
        # Make model_dump raise AttributeError to trigger fallback
        api_keys.model_dump.side_effect = AttributeError()
        # Set up attributes for vars() fallback
        api_keys.openai = "sk-1234567890abcdef1234567890abcdef"
        api_keys.ai_studio = "AIzaSyCDa123456789012345678901234567890123"
        api_keys.some_attr = None  # Should be excluded
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_invalid_api_key_format(self):
        """Test validating API keys with invalid format."""
        result = ValidationResult()
        api_keys = {"openai": "invalid-format", "ai_studio": "AIzaSyCDa123456789012345678901234567890123"}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertTrue(result.valid)  # Invalid format is just a warning
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("API key for openai doesn't match the expected format", result.warnings[0])

    def test_validate_unknown_provider_key(self):
        """Test validating API keys with an unknown provider."""
        result = ValidationResult()
        api_keys = {"openai": "sk-1234567890abcdef1234567890abcdef", "unknown_provider": "some-key"}
        default_provider = "openai"

        validate_api_keys(api_keys, default_provider, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])  # No warnings for unknown providers


class TestNativeCommandAllowlistValidation(unittest.TestCase):
    """Test the validate_native_command_allowlist function."""

    def test_validate_empty_allowlist(self):
        """Test validating an empty allowlist."""
        result = ValidationResult()
        allowlist = []

        validate_native_command_allowlist(allowlist, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_safe_allowlist(self):
        """Test validating a safe allowlist."""
        result = ValidationResult()
        allowlist = ["git ", "npm ", "python "]

        validate_native_command_allowlist(allowlist, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_short_patterns(self):
        """Test validating allowlist with short patterns."""
        result = ValidationResult()
        allowlist = ["git ", "ls", "a"]  # "ls" and "a" are too short

        validate_native_command_allowlist(allowlist, result)

        self.assertTrue(result.valid)  # Short patterns are just a warning
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("Potentially insecure command patterns", result.warnings[0])
        self.assertIn("'ls'", result.warnings[0])
        self.assertIn("'a'", result.warnings[0])

    def test_validate_dangerous_patterns(self):
        """Test validating allowlist with dangerous patterns (command chaining)."""
        result = ValidationResult()
        allowlist = ["git ", "npm; ls", "python | grep"]  # Patterns with command chaining

        validate_native_command_allowlist(allowlist, result)

        self.assertTrue(result.valid)  # Dangerous patterns are just a warning
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("Potentially insecure command patterns", result.warnings[0])
        self.assertIn("'npm; ls'", result.warnings[0])
        self.assertIn("'python | grep'", result.warnings[0])


class TestNativeCommandSettingsValidation(unittest.TestCase):
    """Test the validate_native_command_settings function."""

    def test_validate_none_settings(self):
        """Test validating None native command settings."""
        result = ValidationResult()

        validate_native_command_settings(None, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_valid_settings(self):
        """Test validating valid native command settings."""
        result = ValidationResult()
        settings = MagicMock()
        settings.default_timeout = 30
        settings.default_working_directory = None

        validate_native_command_settings(settings, result)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_validate_negative_timeout(self):
        """Test validating settings with negative timeout."""
        result = ValidationResult()
        settings = MagicMock()
        settings.default_timeout = -10
        settings.default_working_directory = None

        validate_native_command_settings(settings, result)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Invalid default_timeout value", result.errors[0])
        self.assertEqual(result.warnings, [])

    def test_validate_zero_timeout(self):
        """Test validating settings with zero timeout."""
        result = ValidationResult()
        settings = MagicMock()
        settings.default_timeout = 0
        settings.default_working_directory = None

        validate_native_command_settings(settings, result)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Invalid default_timeout value", result.errors[0])
        self.assertEqual(result.warnings, [])

    @patch("pathlib.Path")
    def test_validate_nonexistent_working_directory(self, mock_path_class):
        """Test validating nonexistent working directory."""
        # Create mock path for working directory
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        # Create test settings with nonexistent working directory and a proper timeout value
        settings = MagicMock()
        # Use a real integer instead of a MagicMock for default_timeout
        type(settings).default_timeout = PropertyMock(return_value=30)
        settings.default_working_directory = "/nonexistent/path"

        # Validate settings
        result = ValidationResult()
        validate_native_command_settings(settings, result)

        # Check that validation added a warning
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("working directory", result.warnings[0])


class TestConfigValidation(unittest.TestCase):
    """Test the validate_config function."""

    def test_validate_config(self):
        """Test validating a complete configuration."""
        # Create a mock config with everything needed
        config = MagicMock()
        config.default_provider = "openai"
        config.default_model = "gpt-4"
        config.api_keys = {"openai": "sk-1234567890abcdef1234567890abcdef"}
        config.native_command_allowlist = ["git ", "npm "]
        config.native_commands = MagicMock()
        config.native_commands.default_timeout = 30
        config.native_commands.default_working_directory = None
        config.auto_approve_native_commands = False
        config.auto_approve_edits = False

        # Patch the individual validation functions
        with (
            patch("code_agent.config.validation.validate_model_compatibility") as mock_validate_model,
            patch("code_agent.config.validation.validate_api_keys") as mock_validate_api_keys,
            patch("code_agent.config.validation.validate_native_command_allowlist") as mock_validate_allowlist,
            patch("code_agent.config.validation.validate_native_command_settings") as mock_validate_settings,
        ):
            result = validate_config(config)

            # Check that each validation function was called with the correct arguments
            mock_validate_model.assert_called_once_with("openai", "gpt-4", result)
            mock_validate_api_keys.assert_called_once_with(config.api_keys, "openai", result)
            mock_validate_allowlist.assert_called_once_with(["git ", "npm "], result)
            mock_validate_settings.assert_called_once_with(config.native_commands, result)

            # Check that no security warnings were added
            self.assertTrue(result.valid)
            self.assertEqual(result.errors, [])
            self.assertEqual(result.warnings, [])

    def test_validate_config_with_security_risks(self):
        """Test validating a configuration with security risks."""
        # Create a mock config with auto-approve enabled (security risk)
        config = MagicMock()
        config.default_provider = "openai"
        config.default_model = "gpt-4"
        config.api_keys = {"openai": "sk-1234567890abcdef1234567890abcdef"}
        config.native_command_allowlist = ["git ", "npm "]
        config.native_commands = MagicMock()
        config.native_commands.default_timeout = 30
        config.native_commands.default_working_directory = None
        config.auto_approve_native_commands = True  # Security risk
        config.auto_approve_edits = True  # Security risk

        # Patch the individual validation functions to do nothing
        with (
            patch("code_agent.config.validation.validate_model_compatibility"),
            patch("code_agent.config.validation.validate_api_keys"),
            patch("code_agent.config.validation.validate_native_command_allowlist"),
            patch("code_agent.config.validation.validate_native_command_settings"),
        ):
            result = validate_config(config)

            # Check that security warnings were added
            self.assertTrue(result.valid)  # Security risks are just warnings
            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.warnings), 2)
            self.assertIn("auto_approve_native_commands", result.warnings[0])
            self.assertIn("auto_approve_edits", result.warnings[1])


class TestPrintValidationResult(unittest.TestCase):
    """Test the print_validation_result function."""

    @patch("builtins.print")
    def test_print_valid_result_verbose(self, mock_print):
        """Test printing a valid result with verbose=True."""
        result = ValidationResult()

        print_validation_result(result, verbose=True)

        mock_print.assert_called_once_with("✅ Configuration is valid.")

    @patch("builtins.print")
    def test_print_valid_result_non_verbose(self, mock_print):
        """Test printing a valid result with verbose=False."""
        result = ValidationResult()

        print_validation_result(result, verbose=False)

        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_print_result_with_errors(self, mock_print):
        """Test printing a result with errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")

        print_validation_result(result)

        # Check that print was called with the correct error messages
        mock_print.assert_any_call("❌ Found 2 error(s):")
        mock_print.assert_any_call("  1. Error 1")
        mock_print.assert_any_call("  2. Error 2")
        self.assertEqual(mock_print.call_count, 3)  # One call for header, two for errors

    @patch("builtins.print")
    def test_print_result_with_warnings(self, mock_print):
        """Test printing a result with warnings."""
        result = ValidationResult()
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")

        print_validation_result(result)

        # Check that print was called with the correct warning messages
        mock_print.assert_any_call("⚠️  Found 2 warning(s):")
        mock_print.assert_any_call("  1. Warning 1")
        mock_print.assert_any_call("  2. Warning 2")
        mock_print.assert_any_call("✅ Configuration is valid (with warnings).")

    @patch("builtins.print")
    def test_print_result_with_errors_and_warnings(self, mock_print):
        """Test printing a result with both errors and warnings."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")

        print_validation_result(result)

        # Check that print was called with both error and warning messages
        mock_print.assert_any_call("❌ Found 1 error(s):")
        mock_print.assert_any_call("  1. Error 1")
        mock_print.assert_any_call("⚠️  Found 1 warning(s):")
        mock_print.assert_any_call("  1. Warning 1")
