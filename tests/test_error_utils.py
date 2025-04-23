"""Tests for the error_utils.py functionality."""

from code_agent.tools.error_utils import (
    format_api_error,
    format_config_error,
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
    format_tool_error,
)


def test_format_file_error_file_not_found():
    """Test formatting FileNotFoundError."""
    error = FileNotFoundError("No such file or directory")
    path = "nonexistent.txt"
    operation = "reading"

    result = format_file_error(error, path, operation)

    assert "Error: Failed when reading 'nonexistent.txt'" in result
    assert "file name is spelled correctly" in result
    assert "file exists in the specified location" in result


def test_format_file_error_permission_denied():
    """Test formatting PermissionError."""
    error = PermissionError("Permission denied")
    path = "protected.txt"
    operation = "writing to"

    result = format_file_error(error, path, operation)

    assert "Error: Failed when writing to 'protected.txt'" in result
    assert "necessary permissions" in result
    assert "file is locked" in result


def test_format_file_error_os_error():
    """Test formatting OSError."""
    error = OSError("Disk full")
    path = "large_file.txt"
    operation = "writing to"

    result = format_file_error(error, path, operation)

    assert "Error: Failed when writing to 'large_file.txt'" in result
    assert "Operating system error" in result
    assert "Disk I/O errors" in result


def test_format_file_error_generic_error():
    """Test formatting a generic exception."""
    error = Exception("Unknown error")
    path = "file.txt"
    operation = "processing"

    result = format_file_error(error, path, operation)

    assert "Error: Failed when processing 'file.txt'" in result
    assert "unexpected error" in result
    assert "Error details: Unknown error" in result


def test_format_path_restricted_error():
    """Test formatting path restriction error."""
    path = "/etc/passwd"

    result = format_path_restricted_error(path)

    assert "[bold red]Error:[/bold red] Path" in result
    assert "restricted for security reasons" in result


def test_format_path_restricted_error_with_reason():
    """Test formatting path restriction error with a reason."""
    path = "/etc/passwd"
    reason = "System files are not accessible"

    result = format_path_restricted_error(path, reason)

    assert "[bold red]Error:[/bold red] Path" in result
    assert "restricted for security reasons" in result
    assert "Reason: System files are not accessible" in result


def test_format_file_size_error():
    """Test formatting file size error."""
    path = "large_file.txt"
    size = 5 * 1024 * 1024  # 5 MB
    max_size = 1 * 1024 * 1024  # 1 MB

    result = format_file_size_error(path, size, max_size)

    assert f"Error: File '{path}' is too large (5.00 MB)" in result
    assert "Maximum allowed size is 1.00 MB" in result
    assert "Consider" in result
    assert "Reading only a portion of the file" in result


def test_format_file_size_error_with_additional_message():
    """Test formatting file size error with additional message."""
    path = "large_file.txt"
    size = 5 * 1024 * 1024  # 5 MB
    max_size = 1 * 1024 * 1024  # 1 MB
    additional_message = "Try using a different file format"

    result = format_file_size_error(path, size, max_size, additional_message)

    assert f"Error: File '{path}' is too large (5.00 MB)" in result
    assert "Maximum allowed size is 1.00 MB" in result
    assert "Try using a different file format" in result


# Additional tests for API error formatting


def test_format_api_error_authentication():
    """Test formatting API authentication error."""

    class AuthenticationError(Exception):
        pass

    error = AuthenticationError("Invalid API key")
    provider = "openai"
    model = "gpt-4"

    result = format_api_error(error, provider, model)

    assert "Error: Authentication failed with openai" in result
    assert "API key is correct" in result
    assert "OPENAI_API_KEY environment variable" in result


def test_format_api_error_rate_limit():
    """Test formatting API rate limit error."""
    error = Exception("Rate limit exceeded")
    provider = "anthropic"
    model = "claude-3-opus"

    result = format_api_error(error, provider, model)

    assert "Error: Rate limit exceeded" in result
    assert "Wait a few moments" in result
    assert "Upgrade your API usage tier" in result


def test_format_api_error_context_length():
    """Test formatting context length error."""
    error = Exception("context length exceeded maximum")
    provider = "openai"
    model = "gpt-4"

    result = format_api_error(error, provider, model)

    assert "Error: Context length exceeded" in result
    assert "Reduce the amount of text" in result
    assert "larger context window" in result


def test_format_api_error_model_not_found():
    """Test formatting model not found error."""
    error = Exception("model not found")
    provider = "anthropic"
    model = "nonexistent-model"

    result = format_api_error(error, provider, model)

    assert "Error: Model 'nonexistent-model' not found" in result
    assert "model name may be incorrect" in result
    assert "Try checking the provider's documentation" in result


def test_format_api_error_service_unavailable():
    """Test formatting service unavailable error."""
    error = Exception("service unavailable")
    provider = "groq"
    model = "llama3-8b"

    result = format_api_error(error, provider, model)

    assert "Error: groq service is currently unavailable" in result
    assert "Temporary service outage" in result
    assert "status page for known issues" in result


def test_format_api_error_generic():
    """Test formatting generic API error."""
    error = Exception("Unknown server error")
    provider = "gemini"
    model = "pro"

    result = format_api_error(error, provider, model)

    assert "Error: An unexpected error occurred when calling gemini/pro" in result
    assert "Error type: Exception" in result
    assert "Details: Unknown server error" in result


# Tests for configuration error formatting


def test_format_config_error_validation():
    """Test formatting validation error."""

    class ValidationError(Exception):
        def errors(self):
            return [{"loc": ["model", "name"], "msg": "field required"}]

    error = ValidationError("Validation error")

    result = format_config_error(error, "model configuration")

    assert "Configuration error with 'model configuration'" in result
    assert "Validation failed" in result
    assert "Field 'model.name': field required" in result


def test_format_config_error_validation_non_callable_errors():
    """Test formatting validation error with errors attribute that is not callable."""

    class ValidationError(Exception):
        pass

    error = ValidationError("Validation error")
    error.errors = "This is not a callable but an attribute"

    result = format_config_error(error, "model configuration")

    assert "Configuration error with 'model configuration'" in result
    assert "Validation failed" in result
    assert "Validation error" in result


def test_format_config_error_validation_exception():
    """Test formatting validation error when errors() method fails."""

    class ValidationError(Exception):
        def errors(self):
            raise Exception("Error extracting validation errors")

    error = ValidationError("Validation error")

    result = format_config_error(error, "model configuration")

    assert "Configuration error with 'model configuration'" in result
    assert "Validation failed" in result
    assert "Validation error" in result


def test_format_config_error_file_not_found():
    """Test formatting configuration file not found error."""
    error = FileNotFoundError("No such file or directory")

    result = format_config_error(error)

    assert "Configuration file not found" in result
    assert "haven't created a configuration file yet" in result
    assert "code-agent config init" in result


def test_format_config_error_permission():
    """Test formatting configuration permission error."""
    error = PermissionError("Permission denied")

    result = format_config_error(error)

    assert "Permission denied when accessing configuration file" in result
    assert "Check the file permissions" in result
    assert "read/write access" in result


def test_format_config_error_json_decode():
    """Test formatting JSON decode error."""

    class JSONDecodeError(Exception):
        pass

    error = JSONDecodeError("Invalid JSON")

    result = format_config_error(error)

    assert "Configuration error" in result
    assert "Invalid configuration file format" in result
    assert "Try checking the YAML syntax" in result


def test_format_config_error_env_variable():
    """Test formatting environment variable error."""
    error = Exception("Missing environment variable API_KEY")

    result = format_config_error(error, "API configuration")

    assert "Configuration error with 'API configuration'" in result
    assert "Environment variable issue detected" in result
    assert "Check that all required environment variables" in result


def test_format_config_error_import():
    """Test formatting import error."""
    error = ImportError("No module named 'missing_module'")

    result = format_config_error(error)

    assert "Configuration error" in result
    assert "Failed to import required module" in result
    assert "Make sure all required dependencies are installed" in result


def test_format_config_error_invalid_path():
    """Test formatting invalid path error."""
    error = Exception("Invalid path: /nonexistent/path")

    result = format_config_error(error)

    assert "Configuration error" in result
    assert "Invalid path configuration detected" in result
    assert "Check that all paths in your configuration" in result


def test_format_config_error_generic():
    """Test formatting generic configuration error."""
    error = Exception("Unknown error")

    result = format_config_error(error)

    assert "Configuration error" in result
    assert "An unexpected error occurred" in result
    assert "Error type: Exception" in result


# Tests for tool error formatting


def test_format_tool_error_read_file():
    """Test formatting read_file tool error."""
    error = FileNotFoundError("No such file")
    tool_name = "read_file"
    args = {"target_file": "nonexistent.txt"}

    result = format_tool_error(error, tool_name, args)

    assert "Error executing tool 'read_file'" in result
    assert "Arguments: {'target_file': 'nonexistent.txt'}" in result
    assert "Check if the file path is correct" in result


def test_format_tool_error_apply_edit():
    """Test formatting apply_edit tool error."""
    error = PermissionError("Permission denied")
    tool_name = "apply_edit"
    args = {"target_file": "protected.txt", "code_edit": "This is a very long edit content that should be truncated in the error message..."}

    result = format_tool_error(error, tool_name, args)

    assert "Error executing tool 'apply_edit'" in result
    assert "truncated" in result
    assert "Ensure the target file location is valid" in result


def test_format_tool_error_run_native_command():
    """Test formatting run_native_command tool error."""
    error = Exception("Command failed")
    tool_name = "run_native_command"
    args = {"command": "unknown_command"}

    result = format_tool_error(error, tool_name, args)

    assert "Error executing tool 'run_native_command'" in result
    assert "Arguments: {'command': 'unknown_command'}" in result
    assert "Check if the command exists on your system" in result


def test_format_tool_error_without_args():
    """Test formatting tool error without arguments."""
    error = Exception("Unknown error")
    tool_name = "generic_tool"

    result = format_tool_error(error, tool_name)

    assert "Error executing tool 'generic_tool'" in result
    assert "Error type: Exception" in result
    assert "Details: Unknown error" in result
