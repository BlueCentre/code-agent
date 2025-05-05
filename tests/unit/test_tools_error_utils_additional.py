"""Additional unit tests for code_agent.tools.error_utils module to improve coverage."""

import unittest

from code_agent.tools.error_utils import (
    format_api_error,
    format_config_error,
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
    format_tool_error,
)


class TestErrorUtils(unittest.TestCase):
    """Test the error utils functions."""

    def test_format_file_error_with_custom_error(self):
        """Test format_file_error with a custom error type."""

        class CustomError(Exception):
            pass

        error = CustomError("Custom error message")
        path = "/path/to/file.txt"
        operation = "processing"

        result = format_file_error(error, path, operation)

        # Verify the result contains the expected components
        self.assertIn("Error: Failed when processing '/path/to/file.txt'", result)
        self.assertIn("unexpected error", result)
        self.assertIn("Custom error message", result)

    def test_format_path_restricted_error_with_reason(self):
        """Test format_path_restricted_error with a reason."""
        path = "/etc/passwd"
        reason = "Accessing system files is not allowed"

        result = format_path_restricted_error(path, reason)

        self.assertIn(path, result)
        self.assertIn(reason, result)
        self.assertIn("Path '/etc/passwd' is restricted", result)

    def test_format_path_restricted_error_without_reason(self):
        """Test format_path_restricted_error without a reason."""
        path = "/var/log/system.log"

        result = format_path_restricted_error(path)

        self.assertIn(path, result)
        self.assertIn("restricted for security reasons", result)
        self.assertNotIn("Reason:", result)

    def test_format_file_size_error_with_additional_message(self):
        """Test format_file_size_error with an additional message."""
        path = "/path/to/large_file.txt"
        actual_size = 10 * 1024 * 1024  # 10 MB
        max_size = 5 * 1024 * 1024  # 5 MB
        additional_message = "Please try again with a smaller file"

        result = format_file_size_error(path, actual_size, max_size, additional_message)

        self.assertIn(path, result)
        self.assertIn("10.00 MB", result)
        self.assertIn("5.00 MB", result)
        self.assertIn(additional_message, result)

    def test_format_api_error_authentication_error(self):
        """Test format_api_error with authentication error."""

        class AuthenticationError(Exception):
            pass

        error = AuthenticationError("Invalid API key")
        provider = "openai"
        model = "gpt-4"

        result = format_api_error(error, provider, model)

        self.assertIn("Authentication failed", result)
        self.assertIn("API key", result)
        self.assertIn("OPENAI_API_KEY", result)

    def test_format_api_error_rate_limit_error(self):
        """Test format_api_error with rate limit error."""
        error = Exception("Too many requests. Rate limit exceeded")
        provider = "anthropic"
        model = "claude-3-opus"

        result = format_api_error(error, provider, model)

        self.assertIn("Rate limit exceeded", result)
        self.assertIn("anthropic/claude-3-opus", result)
        self.assertIn("Wait a few moments", result)

    def test_format_api_error_context_length_error(self):
        """Test format_api_error with context length error."""

        class ContextWindowExceededError(Exception):
            pass

        error = ContextWindowExceededError("Input too long")
        provider = "ai_studio"
        model = "gemini-1.5-pro"

        result = format_api_error(error, provider, model)

        self.assertIn("Context length exceeded", result)
        self.assertIn("ai_studio/gemini-1.5-pro", result)
        self.assertIn("Reduce the amount", result)

    def test_format_config_error_validation_error(self):
        """Test format_config_error with a validation error."""

        class ValidationError(Exception):
            def errors(self):
                return [{"loc": ["provider"], "msg": "Invalid provider name"}, {"loc": ["model", "name"], "msg": "Unknown model"}]

        error = ValidationError("Invalid configuration")
        config_item = "model_settings"

        result = format_config_error(error, config_item)

        self.assertIn(f"Configuration error with '{config_item}'", result)
        self.assertIn("Field 'provider': Invalid provider name", result)
        self.assertIn("Field 'model.name': Unknown model", result)

    def test_format_tool_error_basic(self):
        """Test format_tool_error with basic parameters."""
        error = ValueError("Invalid parameter value")
        tool_name = "read_file"
        args = {"path": "/path/to/file.txt"}

        result = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'read_file'", result)
        self.assertIn("Error type: ValueError", result)
        self.assertIn("Details: Invalid parameter value", result)
        self.assertIn("Arguments: {'path': '/path/to/file.txt'}", result)
        self.assertIn("Check if the file path is correct", result)


if __name__ == "__main__":
    unittest.main()
