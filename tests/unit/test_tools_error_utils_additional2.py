"""Additional unit tests for code_agent.tools.error_utils module to improve coverage."""

import unittest
from unittest.mock import MagicMock

from code_agent.tools.error_utils import (
    format_api_error,
    format_config_error,
    format_file_error,
    format_tool_error,
)


class TestErrorUtilsAdditional2(unittest.TestCase):
    """Additional tests for error formatting utility functions to improve coverage."""

    def test_format_file_error_with_os_error(self):
        """Test format_file_error with an OSError."""
        error = OSError("Disk I/O error")
        path = "/path/to/file.txt"
        operation = "processing"

        result = format_file_error(error, path, operation)

        # Verify the result contains the expected components
        self.assertIn(f"Error: Failed when {operation} '{path}'", result)
        self.assertIn("Operating system error", result)
        self.assertIn("Disk I/O error", result)
        self.assertIn("Resource limitations", result)

    def test_format_file_error_with_is_a_directory_error(self):
        """Test format_file_error with an IsADirectoryError."""
        error = IsADirectoryError()
        path = "/path/to/directory"
        operation = "reading"

        result = format_file_error(error, path, operation)

        # Verify the result contains the expected components
        self.assertIn(f"Error: Failed when {operation} '{path}'", result)
        self.assertIn("is a directory, not a file", result)
        self.assertIn("specify a file path instead", result)

    def test_format_file_error_with_not_a_directory_error(self):
        """Test format_file_error with a NotADirectoryError."""
        error = NotADirectoryError()
        path = "/path/to/file.txt"
        operation = "listing"

        result = format_file_error(error, path, operation)

        # Verify the result contains the expected components
        self.assertIn(f"Error: Failed when {operation} '{path}'", result)
        self.assertIn("is not a directory", result)
        self.assertIn("A directory path was expected", result)

    def test_format_file_error_with_permission_error(self):
        """Test format_file_error with a PermissionError."""
        error = PermissionError("Permission denied")
        path = "/root/system_file.txt"
        operation = "writing to"

        result = format_file_error(error, path, operation)

        # Verify the result contains the expected components
        self.assertIn(f"Error: Failed when {operation} '{path}'", result)
        self.assertIn("don't have permission", result)
        self.assertIn("necessary permissions", result)
        self.assertIn("elevated privileges", result)

    def test_format_api_error_with_service_unavailable(self):
        """Test format_api_error with a service unavailable error."""
        error = MagicMock()
        error.__class__.__name__ = "ServiceUnavailableError"
        error.__str__ = MagicMock(return_value="Service temporarily unavailable")

        provider = "groq"
        model = "llama-3"

        result = format_api_error(error, provider, model)

        self.assertIn("groq service is currently unavailable", result)
        self.assertIn("Temporary service outage", result)
        self.assertIn("alternative provider", result)

    def test_format_api_error_with_service_unavailable_in_message(self):
        """Test format_api_error with service unavailable in the error message."""
        error = Exception("The service is unavailable at this time")
        provider = "mistral"
        model = "mistral-medium"

        result = format_api_error(error, provider, model)

        # This should match what the actual implementation returns for a generic error
        self.assertIn("Error: An unexpected error occurred when calling mistral/mistral-medium", result)
        self.assertIn("Error type: Exception", result)
        self.assertIn("Details: The service is unavailable at this time", result)

    def test_format_config_error_with_file_not_found(self):
        """Test format_config_error with FileNotFoundError."""
        error = FileNotFoundError("No such file or directory")
        config_item = "config.yaml"

        result = format_config_error(error, config_item)

        self.assertIn("Configuration error with 'config.yaml'", result)
        self.assertIn("Configuration file not found", result)
        self.assertIn("code-agent config init", result)

    def test_format_config_error_with_permission_error(self):
        """Test format_config_error with PermissionError."""
        error = PermissionError("Permission denied")

        result = format_config_error(error)

        self.assertIn("Configuration error", result)
        self.assertIn("Permission denied when accessing", result)
        self.assertIn("Check the file permissions", result)

    def test_format_config_error_with_yaml_error(self):
        """Test format_config_error with a YAML syntax error."""

        class YAMLError(Exception):
            pass

        error = YAMLError("Mapping values are not allowed here")

        result = format_config_error(error)

        self.assertIn("Configuration error", result)
        self.assertIn("Invalid configuration file format", result)
        self.assertIn("Mapping values are not allowed here", result)

    def test_format_config_error_with_generic_error(self):
        """Test format_config_error with a generic error."""
        error = Exception("Unknown error")

        result = format_config_error(error)

        self.assertIn("Configuration error", result)
        self.assertIn("Unknown error", result)
        self.assertIn("unexpected error", result)

    def test_format_tool_error_with_no_args(self):
        """Test format_tool_error with no args."""
        error = ValueError("Tool execution failed")
        tool_name = "execute_command"

        result = format_tool_error(error, tool_name)

        self.assertIn(f"Error executing tool '{tool_name}'", result)
        self.assertIn("Error type: ValueError", result)
        self.assertIn("Details: Tool execution failed", result)
        # The implementation doesn't include "No arguments provided" message
        self.assertNotIn("Arguments", result)

    def test_format_tool_error_with_nested_args(self):
        """Test format_tool_error with nested arguments structure."""
        error = ValueError("Invalid value for parameter")
        tool_name = "complex_tool"
        args = {"param1": "value1", "nested": {"subparam1": 123, "subparam2": True}, "list_param": [1, 2, 3]}

        result = format_tool_error(error, tool_name, args)

        self.assertIn(f"Error executing tool '{tool_name}'", result)
        self.assertIn("Error type: ValueError", result)
        self.assertIn("Details: Invalid value for parameter", result)
        # The args are shown as a dictionary, not individual entries
        self.assertIn("Arguments: {'param1': 'value1', 'nested': {'subparam1': 123, 'subparam2': True}, 'list_param': [1, 2, 3]}", result)


if __name__ == "__main__":
    unittest.main()
