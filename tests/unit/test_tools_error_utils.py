"""Unit tests for code_agent.tools.error_utils module."""

import unittest
from unittest.mock import MagicMock

from code_agent.tools.error_utils import (
    format_api_error,
    format_config_error,
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
    format_tool_error,
)


class TestErrorUtils(unittest.TestCase):
    """Test error formatting utility functions."""

    def test_format_file_error_file_not_found(self):
        """Test formatting a FileNotFoundError."""
        error = FileNotFoundError("No such file or directory")
        path = "/test/file.txt"
        operation = "reading"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when reading '/test/file.txt'", result)
        self.assertIn("The file '/test/file.txt' could not be found", result)
        self.assertIn("If the file name is spelled correctly", result)

    def test_format_file_error_is_a_directory(self):
        """Test formatting an IsADirectoryError."""
        error = IsADirectoryError("Is a directory")
        path = "/test/dir"
        operation = "writing to"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when writing to '/test/dir'", result)
        self.assertIn("'/test/dir' is a directory, not a file", result)

    def test_format_file_error_not_a_directory(self):
        """Test formatting a NotADirectoryError."""
        error = NotADirectoryError("Not a directory")
        path = "/test/file.txt"
        operation = "listing"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when listing '/test/file.txt'", result)
        self.assertIn("'/test/file.txt' is not a directory", result)

    def test_format_file_error_permission_error(self):
        """Test formatting a PermissionError."""
        error = PermissionError("Permission denied")
        path = "/test/file.txt"
        operation = "accessing"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when accessing '/test/file.txt'", result)
        self.assertIn("You don't have permission to access '/test/file.txt'", result)
        self.assertIn("If you have the necessary permissions", result)

    def test_format_file_error_os_error(self):
        """Test formatting an OSError."""
        error = OSError("Disk I/O error")
        path = "/test/file.txt"
        operation = "reading"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when reading '/test/file.txt'", result)
        self.assertIn("Operating system error when accessing '/test/file.txt'", result)
        self.assertIn("Details: Disk I/O error", result)
        self.assertIn("Disk I/O errors", result)

    def test_format_file_error_unexpected_error(self):
        """Test formatting an unexpected error type."""
        error = ValueError("Invalid value")
        path = "/test/file.txt"
        operation = "processing"

        result = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when processing '/test/file.txt'", result)
        self.assertIn("An unexpected error occurred when processing '/test/file.txt'", result)
        self.assertIn("Error details: Invalid value", result)

    def test_format_path_restricted_error_without_reason(self):
        """Test formatting a path restricted error without a reason."""
        path = "/etc/passwd"

        result = format_path_restricted_error(path)

        self.assertIn("Path '/etc/passwd' is restricted for security reasons", result)
        self.assertIn("Only paths within the current working directory are allowed", result)

    def test_format_path_restricted_error_with_reason(self):
        """Test formatting a path restricted error with a reason."""
        path = "/etc/passwd"
        reason = "System files cannot be accessed"

        result = format_path_restricted_error(path, reason)

        self.assertIn("Path '/etc/passwd' is restricted for security reasons", result)
        self.assertIn("Only paths within the current working directory are allowed", result)
        self.assertIn("Reason: System files cannot be accessed", result)

    def test_format_file_size_error_without_additional_message(self):
        """Test formatting a file size error without an additional message."""
        path = "/test/large_file.txt"
        actual_size = 10 * 1024 * 1024  # 10 MB in bytes
        max_size = 5 * 1024 * 1024  # 5 MB in bytes

        result = format_file_size_error(path, actual_size, max_size)

        self.assertIn("Error: File '/test/large_file.txt' is too large (10.00 MB)", result)
        self.assertIn("Maximum allowed size is 5.00 MB", result)
        self.assertIn("Using a smaller file", result)

    def test_format_file_size_error_with_additional_message(self):
        """Test formatting a file size error with an additional message."""
        path = "/test/large_file.txt"
        actual_size = 10 * 1024 * 1024  # 10 MB in bytes
        max_size = 5 * 1024 * 1024  # 5 MB in bytes
        additional_message = "This file requires special processing"

        result = format_file_size_error(path, actual_size, max_size, additional_message)

        self.assertIn("Error: File '/test/large_file.txt' is too large (10.00 MB)", result)
        self.assertIn("Maximum allowed size is 5.00 MB", result)
        self.assertIn("This file requires special processing", result)

    def test_format_api_error_authentication_error(self):
        """Test formatting an API authentication error."""
        error = Exception("Invalid API key")
        provider = "openai"
        model = "gpt-4"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: Authentication failed with openai", result)
        self.assertIn("If your API key is correct and not expired", result)
        self.assertIn("Set the OPENAI_API_KEY environment variable", result)

    def test_format_api_error_rate_limit_error(self):
        """Test formatting an API rate limit error."""
        error = Exception("Rate limit exceeded")
        provider = "ai_studio"
        model = "gemini-pro"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: Rate limit exceeded when using ai_studio/gemini-pro", result)
        self.assertIn("Wait a few moments before trying again", result)
        self.assertIn("Upgrade your API usage tier if appropriate", result)

    def test_format_api_error_context_length_error(self):
        """Test formatting an API context length error."""
        error = Exception("context length exceeded")
        provider = "anthropic"
        model = "claude-3-opus"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: Context length exceeded for anthropic/claude-3-opus", result)
        self.assertIn("Your input is too large for this model's context window", result)
        self.assertIn("Reduce the amount of text or code in your prompt", result)

    def test_format_api_error_model_not_found_error(self):
        """Test formatting an API model not found error."""
        error = Exception("Model not found")
        provider = "groq"
        model = "llama-3"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: Model 'llama-3' not found for provider 'groq'", result)
        self.assertIn("The model name may be incorrect or misspelled", result)
        self.assertIn("Try checking the provider's documentation for available models", result)

    def test_format_api_error_service_unavailable_error(self):
        """Test formatting an API service unavailable error."""
        error = Exception("Service unavailable")
        provider = "mistral"
        model = "mistral-medium"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: mistral service is currently unavailable", result)
        self.assertIn("Temporary service outage", result)
        self.assertIn("Check mistral's status page for known issues", result)

    def test_format_api_error_generic_error(self):
        """Test formatting a generic API error."""
        error = Exception("Unknown error occurred")
        provider = "cohere"
        model = "command"

        result = format_api_error(error, provider, model)

        self.assertIn("Error: An unexpected error occurred when calling cohere/command", result)
        self.assertIn("Error type: Exception", result)
        self.assertIn("Details: Unknown error occurred", result)

    def test_format_config_error_validation_error_with_errors_method(self):
        """Test formatting a config validation error with errors method."""
        # Create a mock ValidationError with errors method
        error = MagicMock()
        error.__class__.__name__ = "ValidationError"
        error.errors.return_value = [
            {"loc": ["api_key"], "msg": "field required", "type": "value_error.missing"},
            {"loc": ["model", "temperature"], "msg": "value must be between 0 and 1", "type": "value_error.number.not_gt"},
        ]

        result = format_config_error(error, "model.temperature")

        self.assertIn("Configuration error with 'model.temperature'", result)
        self.assertIn("Field 'api_key': field required", result)
        self.assertIn("Field 'model.temperature': value must be between 0 and 1", result)
        self.assertIn("Please check your configuration file", result)

    def test_format_config_error_validation_error_without_errors_method(self):
        """Test formatting a config validation error without errors method."""
        # Create a mock ValidationError without errors method
        error = MagicMock()
        error.__class__.__name__ = "ValidationError"
        error.__str__ = MagicMock(return_value="Invalid configuration: api_key is required")

        result = format_config_error(error)

        self.assertIn("Configuration validation error", result)
        self.assertIn("Validation failed with the following issues", result)

    def test_format_config_error_file_not_found(self):
        """Test formatting a config file not found error."""
        error = FileNotFoundError("No such file or directory")

        result = format_config_error(error)

        self.assertIn("Configuration error", result)
        self.assertIn("Configuration file not found", result)
        self.assertIn("Looks like you haven't created a configuration file yet", result)
        self.assertIn("To create one, run:", result)
        self.assertIn("code-agent config init", result)

    def test_format_config_error_permission_error(self):
        """Test formatting a config permission error."""
        error = PermissionError("Permission denied")

        result = format_config_error(error, "config.yaml")

        self.assertIn("Configuration error with 'config.yaml'", result)
        self.assertIn("Permission denied when accessing configuration", result)
        self.assertIn("permissions on your configuration", result)

    def test_format_config_error_unknown_error(self):
        """Test formatting an unknown config error."""
        error = ValueError("Invalid value")

        result = format_config_error(error)

        self.assertIn("Configuration error", result)
        self.assertIn("An unexpected error occurred:", result)
        self.assertIn("Invalid value", result)
        self.assertIn("ValueError", result)

    def test_format_tool_error_without_args(self):
        """Test formatting a tool error without args."""
        error = ValueError("Invalid parameter")
        tool_name = "read_file"

        result = format_tool_error(error, tool_name)

        self.assertIn("Error executing tool 'read_file'", result)
        self.assertIn("Error type: ValueError", result)
        self.assertIn("Invalid parameter", result)

    def test_format_tool_error_with_args(self):
        """Test formatting a tool error with args."""
        error = FileNotFoundError("No such file or directory")
        tool_name = "read_file"
        args = {"path": "/test/file.txt", "offset": 0, "limit": 100}

        result = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'read_file'", result)
        self.assertIn("Error type: FileNotFoundError", result)
        self.assertIn("No such file or directory", result)
        self.assertIn("/test/file.txt", result)

    def test_format_tool_error_with_complex_args(self):
        """Test formatting a tool error with complex args including nested structures."""
        error = ValueError("Invalid parameter")
        tool_name = "complex_tool"
        args = {
            "path": "/test/file.txt",
            "options": {"recursive": True, "follow_symlinks": False},
            "filters": ["*.py", "*.js"],
        }

        result = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'complex_tool'", result)
        self.assertIn("Error type: ValueError", result)
        self.assertIn("Invalid parameter", result)
        self.assertIn("filters", str(result))
