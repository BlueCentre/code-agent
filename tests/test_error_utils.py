"""Tests for the error_utils.py functionality."""

from code_agent.tools.error_utils import (
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
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
