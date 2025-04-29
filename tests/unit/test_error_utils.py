"""
Unit tests for code_agent.tools.error_utils module.
"""

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
    """Tests for error_utils formatting functions."""

    def test_format_file_error_file_not_found(self):
        """Test formatting a FileNotFoundError."""
        error = FileNotFoundError("No such file or directory")
        path = "/path/to/nonexistent/file.txt"
        operation = "reading"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when reading", message)
        self.assertIn(path, message)
        self.assertIn("could not be found", message)

    def test_format_file_error_permission_error(self):
        """Test formatting a PermissionError."""
        error = PermissionError("Permission denied")
        path = "/path/to/protected/file.txt"
        operation = "writing"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when writing", message)
        self.assertIn(path, message)
        self.assertIn("don't have permission", message)

    def test_format_file_error_is_a_directory(self):
        """Test formatting an IsADirectoryError."""
        error = IsADirectoryError("Is a directory")
        path = "/path/to/dir"
        operation = "writing"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when writing", message)
        self.assertIn(path, message)
        self.assertIn("is a directory, not a file", message)

    def test_format_file_error_not_a_directory(self):
        """Test formatting a NotADirectoryError."""
        error = NotADirectoryError("Not a directory")
        path = "/path/to/file.txt"
        operation = "listing"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when listing", message)
        self.assertIn(path, message)
        self.assertIn("is not a directory", message)

    def test_format_file_error_os_error(self):
        """Test formatting an OSError."""
        error = OSError("Disk full")
        path = "/path/to/file.txt"
        operation = "writing"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when writing", message)
        self.assertIn(path, message)
        self.assertIn("Operating system error", message)
        self.assertIn("Disk full", message)

    def test_format_file_error_unknown_error(self):
        """Test formatting an unknown error type."""
        error = ValueError("Invalid value")
        path = "/path/to/file.txt"
        operation = "processing"

        message = format_file_error(error, path, operation)

        self.assertIn("Error: Failed when processing", message)
        self.assertIn(path, message)
        self.assertIn("unexpected error", message)
        self.assertIn("Invalid value", message)

    def test_format_path_restricted_error(self):
        """Test formatting a path restricted error."""
        path = "/etc/passwd"

        message = format_path_restricted_error(path)

        self.assertIn("Path '/etc/passwd' is restricted", message)
        self.assertIn("security reasons", message)

    def test_format_path_restricted_error_with_reason(self):
        """Test formatting a path restricted error with a reason."""
        path = "/etc/passwd"
        reason = "System files are not accessible"

        message = format_path_restricted_error(path, reason)

        self.assertIn("Path '/etc/passwd' is restricted", message)
        self.assertIn("Reason: System files are not accessible", message)

    def test_format_file_size_error(self):
        """Test formatting a file size error."""
        path = "/path/to/large/file.txt"
        actual_size = 15 * 1024 * 1024  # 15 MB
        max_size = 10 * 1024 * 1024  # 10 MB

        message = format_file_size_error(path, actual_size, max_size)

        self.assertIn("Error: File '/path/to/large/file.txt' is too large", message)
        self.assertIn("15.00 MB", message)
        self.assertIn("Maximum allowed size is 10.00 MB", message)

    def test_format_file_size_error_with_additional_message(self):
        """Test formatting a file size error with additional message."""
        path = "/path/to/large/file.txt"
        actual_size = 15 * 1024 * 1024  # 15 MB
        max_size = 10 * 1024 * 1024  # 10 MB
        additional_message = "Try using a different file format"

        message = format_file_size_error(path, actual_size, max_size, additional_message)

        self.assertIn("Error: File '/path/to/large/file.txt' is too large", message)
        self.assertIn("Try using a different file format", message)

    def test_format_api_error_authentication(self):
        """Test formatting an API authentication error."""
        error = Exception("Invalid API key provided")
        provider = "openai"
        model = "gpt-4"

        message = format_api_error(error, provider, model)

        self.assertIn("Authentication failed with openai", message)
        self.assertIn("API key", message)

    def test_format_api_error_rate_limit(self):
        """Test formatting an API rate limit error."""
        error = Exception("Rate limit exceeded")
        provider = "anthropic"
        model = "claude-3"

        message = format_api_error(error, provider, model)

        self.assertIn("Rate limit exceeded", message)
        self.assertIn("anthropic/claude-3", message)

    def test_format_api_error_context_length(self):
        """Test formatting a context length error."""
        error = Exception("This model's maximum context length is 4097 tokens")
        provider = "openai"
        model = "gpt-3.5-turbo"

        message = format_api_error(error, provider, model)

        self.assertIn("Context length exceeded", message)
        self.assertIn("openai/gpt-3.5-turbo", message)

    def test_format_api_error_model_not_found(self):
        """Test formatting a model not found error."""
        error = Exception("The model 'gpt-5' is not found")
        provider = "openai"
        model = "gpt-5"

        message = format_api_error(error, provider, model)

        self.assertIn("Model 'gpt-5' not found", message)
        self.assertIn("provider 'openai'", message)

    def test_format_api_error_service_unavailable(self):
        """Test formatting a service unavailable error."""
        error = Exception("Service unavailable. Try again later")
        provider = "groq"
        model = "llama3-70b"

        message = format_api_error(error, provider, model)

        self.assertIn("groq service is currently unavailable", message)

    def test_format_api_error_unknown(self):
        """Test formatting an unknown API error."""
        error = Exception("Unknown error occurred")
        provider = "cohere"
        model = "command"

        message = format_api_error(error, provider, model)

        self.assertIn("unexpected error occurred when calling cohere/command", message)
        self.assertIn("Unknown error occurred", message)

    def test_format_config_error_validation(self):
        """Test formatting a validation error."""
        # Create a mock validation error similar to Pydantic's
        error = MagicMock(spec=["errors"])
        error.errors.return_value = [
            {"loc": ["provider"], "msg": "field required", "type": "value_error.missing"},
            {"loc": ["temperature"], "msg": "value must be between 0 and 1", "type": "value_error.number.not_gt"},
        ]
        error_type = type(error)
        error_type.__name__ = "ValidationError"

        message = format_config_error(error, "model_settings")

        self.assertIn("Configuration error with 'model_settings'", message)
        self.assertIn("Field 'provider': field required", message)
        self.assertIn("Field 'temperature': value must be between 0 and 1", message)

    def test_format_config_error_file_not_found(self):
        """Test formatting a config file not found error."""
        error = FileNotFoundError("No such file or directory")

        message = format_config_error(error)

        self.assertIn("Configuration file not found", message)
        self.assertIn("code-agent config init", message)

    def test_format_config_error_permission(self):
        """Test formatting a config permission error."""
        error = PermissionError("Permission denied")

        message = format_config_error(error, "config.yaml")

        self.assertIn("Configuration error with 'config.yaml'", message)
        self.assertIn("Permission denied", message)
        self.assertIn("file permissions", message)

    def test_format_config_error_json_decode(self):
        """Test formatting a JSON decode error."""

        class JSONDecodeError(Exception):
            pass

        error = JSONDecodeError("Invalid JSON at line 10")

        message = format_config_error(error, "config.json")

        self.assertIn("Configuration error with 'config.json'", message)
        self.assertIn("Invalid configuration file format", message)
        self.assertIn("Invalid JSON at line 10", message)

    def test_format_config_error_env_variable(self):
        """Test formatting an environment variable error."""

        class EnvVariableError(Exception):
            pass

        error = EnvVariableError("Environment variable OPENAI_API_KEY not set")

        message = format_config_error(error)

        self.assertIn("Environment variable issue detected", message)
        self.assertIn("Environment variable OPENAI_API_KEY not set", message)

    def test_format_config_error_import_error(self):
        """Test formatting an import error."""
        error = ImportError("No module named 'some_module'")

        message = format_config_error(error, "plugins")

        self.assertIn("Configuration error with 'plugins'", message)
        self.assertIn("Failed to import required module", message)
        self.assertIn("No module named 'some_module'", message)

    def test_format_config_error_invalid_path(self):
        """Test formatting an invalid path error."""
        error = ValueError("Invalid path: /nonexistent/path")

        message = format_config_error(error)

        self.assertIn("Configuration error", message)
        self.assertIn("Invalid path configuration detected", message)

    def test_format_config_error_generic(self):
        """Test formatting a generic config error."""
        error = Exception("Something went wrong")

        message = format_config_error(error)

        self.assertIn("Configuration error", message)
        self.assertIn("An unexpected error occurred: Something went wrong", message)

    def test_format_tool_error(self):
        """Test formatting a tool error."""
        error = ValueError("Invalid argument")
        tool_name = "run_terminal_cmd"
        args = {"command": "ls -la", "is_background": True}

        message = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'run_terminal_cmd'", message)
        self.assertIn("Error type: ValueError", message)
        self.assertIn("Details: Invalid argument", message)
        self.assertIn("Arguments: {'command': 'ls -la', 'is_background': True}", message)

    def test_format_tool_error_read_file(self):
        """Test formatting a read_file tool error."""
        error = FileNotFoundError("File not found")
        tool_name = "read_file"
        args = {"target_file": "/path/to/nonexistent.txt"}

        message = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'read_file'", message)
        self.assertIn("File not found", message)
        self.assertIn("Check if the file path is correct", message)
        self.assertIn("Arguments: {'target_file': '/path/to/nonexistent.txt'}", message)

    def test_format_tool_error_apply_edit(self):
        """Test formatting an apply_edit tool error."""
        error = PermissionError("Permission denied")
        tool_name = "apply_edit"
        args = {"target_file": "/path/to/file.txt"}

        message = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'apply_edit'", message)
        self.assertIn("Permission denied", message)
        self.assertIn("Check if you have permission to modify the file", message)

    def test_format_tool_error_run_native_command(self):
        """Test formatting a run_native_command tool error."""
        error = OSError("Command not found")
        tool_name = "run_native_command"
        args = {"command": "nonexistent_command"}

        message = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'run_native_command'", message)
        self.assertIn("Command not found", message)
        self.assertIn("Check if the command exists on your system", message)

    def test_format_tool_error_with_large_code_edit(self):
        """Test formatting a tool error with large code_edit argument."""
        error = ValueError("Invalid code")
        tool_name = "edit_file"
        args = {"target_file": "file.py", "code_edit": "x" * 1000}  # Large code edit

        message = format_tool_error(error, tool_name, args)

        self.assertIn("Error executing tool 'edit_file'", message)
        self.assertIn("(truncated)", message)  # Code should be truncated

    def test_format_tool_error_without_args(self):
        """Test formatting a tool error without args."""
        error = Exception("Unknown error")
        tool_name = "unknown_tool"

        message = format_tool_error(error, tool_name)

        self.assertIn("Error executing tool 'unknown_tool'", message)
        self.assertIn("Unknown error", message)
        self.assertNotIn("Arguments", message)  # No arguments section


if __name__ == "__main__":
    unittest.main()
