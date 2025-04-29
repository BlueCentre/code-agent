"""Unit tests for configuration validation functions in code_agent/config/validation.py.

Tests cover validation of:
1. Model compatibility with providers
2. API key format and presence
3. Command allowlist patterns
4. Native command settings
5. Complete configuration validation
"""

from unittest.mock import MagicMock, patch

from code_agent.config.validation import (
    ValidationResult,
    print_validation_result,
    validate_api_keys,
    validate_config,
    validate_model_compatibility,
    validate_native_command_allowlist,
    validate_native_command_settings,
)


class TestValidationResult:
    """Tests for the ValidationResult class."""

    def test_validation_result_initialization(self):
        """Test that ValidationResult initializes with correct defaults."""
        result = ValidationResult()
        assert result.errors == []
        assert result.warnings == []
        assert result.valid is True

    def test_add_error(self):
        """Test adding an error sets valid to False."""
        result = ValidationResult()
        result.add_error("Test error")
        assert "Test error" in result.errors
        assert result.valid is False

    def test_add_warning(self):
        """Test adding a warning doesn't affect valid flag."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert "Test warning" in result.warnings
        assert result.valid is True

    def test_str_representation_valid(self):
        """Test string representation of a valid result."""
        result = ValidationResult()
        assert str(result) == "Configuration is valid."

    def test_str_representation_with_errors(self):
        """Test string representation with errors."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")
        assert "Found 2 error(s)" in str(result)
        assert "1. Error 1" in str(result)
        assert "2. Error 2" in str(result)

    def test_str_representation_with_warnings(self):
        """Test string representation with warnings."""
        result = ValidationResult()
        result.add_warning("Warning 1")
        assert "Found 1 warning(s)" in str(result)
        assert "1. Warning 1" in str(result)

    def test_str_representation_with_errors_and_warnings(self):
        """Test string representation with both errors and warnings."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        assert "Found 1 error(s)" in str(result)
        assert "Found 1 warning(s)" in str(result)
        assert "1. Error 1" in str(result)
        assert "1. Warning 1" in str(result)


class TestModelCompatibilityValidation:
    """Tests for validate_model_compatibility function."""

    def test_valid_model_compatibility(self):
        """Test with a valid provider and model combination."""
        result = ValidationResult()
        validate_model_compatibility("openai", "gpt-4", result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_unknown_provider(self):
        """Test with an unknown provider."""
        result = ValidationResult()
        validate_model_compatibility("unknown_provider", "some_model", result)
        assert result.valid is True
        assert not result.errors
        assert len(result.warnings) == 1
        assert "Unknown provider 'unknown_provider'" in result.warnings[0]

    def test_invalid_model(self):
        """Test with a valid provider but invalid model."""
        result = ValidationResult()
        validate_model_compatibility("openai", "invalid_model", result)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Model 'invalid_model' is not recognized for provider 'openai'" in result.errors[0]

    def test_openai_special_models(self):
        """Test with valid OpenAI special model naming patterns."""
        result = ValidationResult()

        with patch(
            "code_agent.config.validation.PROVIDER_MODEL_MAP",
            {
                "openai": set()  # Empty set to ensure model not found in allowed models
            },
        ):
            # Test fine-tuned model pattern - should return early without adding errors
            validate_model_compatibility("openai", "ft:gpt-3.5-turbo:my-org:custom_suffix:id", result)
            assert result.valid is True
            assert not result.errors

            # Test vision model - should return early without adding errors
            validate_model_compatibility("openai", "gpt-4-vision-preview", result)
            assert result.valid is True
            assert not result.errors

            # Test 32k model - should return early without adding errors
            validate_model_compatibility("openai", "gpt-4-32k", result)
            assert result.valid is True
            assert not result.errors

            # Confirm the early return by checking a non-special model adds error
            validate_model_compatibility("openai", "not-special-model", result)
            assert not result.valid
            assert len(result.errors) == 1

    def test_openai_model_with_complex_condition_coverage(self):
        """Test specifically to cover the complex if condition in line 131 with various inputs."""
        # We need to test a special case that will evaluate the entire condition
        # In this test we create a model name that doesn't start with any of the expected prefixes
        # but still needs to evaluate the full condition, covering line 131 completely
        result = ValidationResult()

        # This will cause the condition to be fully evaluated but still return False
        with patch(
            "code_agent.config.validation.PROVIDER_MODEL_MAP",
            {
                "openai": {"gpt-4"}  # Only gpt-4 as valid model
            },
        ):
            # Test with a non-special model name - should add an error
            custom_model = "gpt-custom-model"  # doesn't match any special prefix
            validate_model_compatibility("openai", custom_model, result)
            assert not result.valid
            assert len(result.errors) == 1
            assert f"Model '{custom_model}' is not recognized for provider 'openai'" in result.errors[0]


class TestApiKeysValidation:
    """Tests for validate_api_keys function."""

    def test_valid_api_keys_dict(self):
        """Test with valid API keys as a dictionary."""
        result = ValidationResult()
        api_keys = {
            "openai": "sk-abcdefghijklmnopqrstuvwxyz123456",
            "anthropic": "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        }
        validate_api_keys(api_keys, "openai", result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_valid_api_keys_object(self):
        """Test with valid API keys as an object."""
        result = ValidationResult()

        class ApiKeys:
            def __init__(self):
                self.openai = "sk-abcdefghijklmnopqrstuvwxyz123456"
                self.anthropic = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"

            def model_dump(self, exclude_none=True):
                return {"openai": self.openai, "anthropic": self.anthropic}

        api_keys = ApiKeys()
        validate_api_keys(api_keys, "openai", result)
        assert result.valid is True
        assert not result.errors

    def test_missing_default_provider_key(self):
        """Test with missing key for default provider."""
        result = ValidationResult()
        api_keys = {
            "anthropic": "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        }
        validate_api_keys(api_keys, "openai", result)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "API key for default provider 'openai' is missing" in result.errors[0]

    def test_empty_default_provider_key(self):
        """Test with empty key for default provider."""
        result = ValidationResult()
        api_keys = {
            "openai": "",
            "anthropic": "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        }
        validate_api_keys(api_keys, "openai", result)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "API key for default provider 'openai' is missing or empty" in result.errors[0]

    def test_no_api_keys(self):
        """Test with no API keys provided."""
        result = ValidationResult()
        api_keys = {}
        validate_api_keys(api_keys, "openai", result)
        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert "No API keys found" in result.warnings[0]
        assert "API key for default provider 'openai' is missing" in result.errors[0]

    def test_invalid_format_api_key(self):
        """Test with invalid format for API key."""
        result = ValidationResult()
        api_keys = {
            "openai": "invalid-key-format",
            "anthropic": "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        }
        validate_api_keys(api_keys, "openai", result)
        # The API key format check only adds warnings, not errors
        assert result.valid is True
        assert len(result.warnings) >= 1
        assert "API key for openai doesn't match the expected format" in result.warnings[0]

    def test_pydantic_model_fallback(self):
        """Test the fallback for older Pydantic models."""
        result = ValidationResult()

        class OldApiKeys:
            def __init__(self):
                self.openai = "sk-abcdefghijklmnopqrstuvwxyz123456"
                self.anthropic = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"
                self._private = "should_be_ignored"

            # No model_dump method

        api_keys = OldApiKeys()
        with patch("code_agent.config.validation.re.match", return_value=True):  # Mock regex check
            validate_api_keys(api_keys, "openai", result)
        assert result.valid is True
        assert not result.errors


class TestCommandAllowlistValidation:
    """Tests for validate_native_command_allowlist function."""

    def test_empty_allowlist(self):
        """Test with an empty allowlist."""
        result = ValidationResult()
        validate_native_command_allowlist([], result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_valid_allowlist(self):
        """Test with a valid allowlist."""
        result = ValidationResult()
        allowlist = ["git status", "npm install", "python -m pytest"]
        validate_native_command_allowlist(allowlist, result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_short_command_pattern(self):
        """Test with overly short command patterns."""
        result = ValidationResult()
        allowlist = ["git status", "ls", "a", "python -m pytest"]
        validate_native_command_allowlist(allowlist, result)
        assert result.valid is True
        assert not result.errors
        assert len(result.warnings) == 1
        assert "Potentially insecure command patterns" in result.warnings[0]
        assert "'ls'" in result.warnings[0] and "'a'" in result.warnings[0]

    def test_command_chaining_patterns(self):
        """Test with command patterns that enable command chaining."""
        result = ValidationResult()
        allowlist = ["git status", "ls | grep file", "python; rm -rf /", "echo `date`"]
        validate_native_command_allowlist(allowlist, result)
        assert result.valid is True
        assert not result.errors
        assert len(result.warnings) == 1
        assert "Potentially insecure command patterns" in result.warnings[0]
        assert "'ls | grep file'" in result.warnings[0]
        assert "'python; rm -rf /'" in result.warnings[0]
        assert "'echo `date`'" in result.warnings[0]


class TestNativeCommandSettingsValidation:
    """Tests for validate_native_command_settings function."""

    def test_none_settings(self):
        """Test with None settings."""
        result = ValidationResult()
        validate_native_command_settings(None, result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_valid_settings(self):
        """Test with valid native command settings."""
        result = ValidationResult()

        class NativeCommands:
            def __init__(self):
                self.default_timeout = 30
                self.default_working_directory = "."  # Current directory

        settings = NativeCommands()
        with patch("pathlib.Path.exists", return_value=True):
            validate_native_command_settings(settings, result)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_negative_timeout(self):
        """Test with a negative timeout value."""
        result = ValidationResult()

        class NativeCommands:
            def __init__(self):
                self.default_timeout = -10

        settings = NativeCommands()
        validate_native_command_settings(settings, result)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Invalid default_timeout value" in result.errors[0]

    def test_nonexistent_working_directory(self):
        """Test with a non-existent working directory."""
        result = ValidationResult()

        class NativeCommands:
            def __init__(self):
                self.default_timeout = 30
                self.default_working_directory = "/path/that/does/not/exist"

        settings = NativeCommands()
        with patch("pathlib.Path.exists", return_value=False):
            validate_native_command_settings(settings, result)
        assert result.valid is True  # Not critical error
        assert not result.errors
        assert len(result.warnings) == 1
        assert "Default working directory does not exist" in result.warnings[0]


class TestFullConfigValidation:
    """Tests for validate_config function."""

    def setup_mock_config(self):
        """Create a mock configuration for testing."""
        config = MagicMock()
        config.default_provider = "openai"
        config.default_model = "gpt-4"
        config.api_keys.openai = "sk-abcdefghijklmnopqrstuvwxyz123456"
        config.native_command_allowlist = ["git status", "npm install"]
        config.auto_approve_native_commands = False
        config.auto_approve_edits = False
        config.native_commands = MagicMock()
        config.native_commands.default_timeout = 30
        return config

    def test_valid_config(self):
        """Test with a valid configuration."""
        config = self.setup_mock_config()

        # Patch individual validation functions
        with (
            patch("code_agent.config.validation.validate_model_compatibility"),
            patch("code_agent.config.validation.validate_api_keys"),
            patch("code_agent.config.validation.validate_native_command_allowlist"),
            patch("code_agent.config.validation.validate_native_command_settings"),
        ):
            result = validate_config(config)
            assert result.valid is True
            assert not result.errors
            assert not result.warnings

    def test_security_risks_warnings(self):
        """Test security risk warnings for auto-approve settings."""
        config = self.setup_mock_config()
        config.auto_approve_native_commands = True
        config.auto_approve_edits = True

        # Patch individual validation functions
        with (
            patch("code_agent.config.validation.validate_model_compatibility"),
            patch("code_agent.config.validation.validate_api_keys"),
            patch("code_agent.config.validation.validate_native_command_allowlist"),
            patch("code_agent.config.validation.validate_native_command_settings"),
        ):
            result = validate_config(config)
            assert result.valid is True  # Warnings don't make config invalid
            assert not result.errors
            assert len(result.warnings) == 2
            assert "SECURITY RISK: auto_approve_native_commands is enabled" in result.warnings[0]
            assert "SECURITY RISK: auto_approve_edits is enabled" in result.warnings[1]

    def test_validation_errors_propagation(self):
        """Test that errors from individual validations are propagated."""
        config = self.setup_mock_config()

        # Mock validate_model_compatibility to add an error
        def mock_validate_model_compatibility(*args):
            args[2].add_error("Model compatibility error")

        # Patch individual validation functions
        with (
            patch("code_agent.config.validation.validate_model_compatibility", side_effect=mock_validate_model_compatibility),
            patch("code_agent.config.validation.validate_api_keys"),
            patch("code_agent.config.validation.validate_native_command_allowlist"),
            patch("code_agent.config.validation.validate_native_command_settings"),
        ):
            result = validate_config(config)
            assert result.valid is False
            assert len(result.errors) == 1
            assert "Model compatibility error" in result.errors[0]


class TestPrintValidationResult:
    """Tests for print_validation_result function."""

    def test_print_valid_result_verbose(self, capsys):
        """Test printing a valid result with verbose flag."""
        result = ValidationResult()
        print_validation_result(result, verbose=True)
        captured = capsys.readouterr()
        assert "✅ Configuration is valid." in captured.out

    def test_print_valid_result_not_verbose(self, capsys):
        """Test printing a valid result without verbose flag."""
        result = ValidationResult()
        print_validation_result(result, verbose=False)
        captured = capsys.readouterr()
        assert captured.out == ""  # Nothing should be printed

    def test_print_result_with_errors(self, capsys):
        """Test printing a result with errors."""
        result = ValidationResult()
        result.add_error("Test error 1")
        result.add_error("Test error 2")
        print_validation_result(result)
        captured = capsys.readouterr()
        assert "❌ Found 2 error(s):" in captured.out
        assert "1. Test error 1" in captured.out
        assert "2. Test error 2" in captured.out

    def test_print_result_with_warnings(self, capsys):
        """Test printing a result with warnings."""
        result = ValidationResult()
        result.add_warning("Test warning")
        print_validation_result(result)
        captured = capsys.readouterr()
        assert "⚠️  Found 1 warning(s):" in captured.out
        assert "1. Test warning" in captured.out

    def test_print_result_with_errors_and_warnings(self, capsys):
        """Test printing a result with both errors and warnings."""
        result = ValidationResult()
        result.add_error("Test error")
        result.add_warning("Test warning")
        print_validation_result(result)
        captured = capsys.readouterr()
        assert "❌ Found 1 error(s):" in captured.out
        assert "1. Test error" in captured.out
        assert "⚠️  Found 1 warning(s):" in captured.out
        assert "1. Test warning" in captured.out
