"""Utility functions for formatting error messages in file operations."""

from pathlib import Path
from typing import Callable, Dict, Optional, Type

# --- Error Formatting Utilities ---

ERROR_SUGGESTIONS: Dict[Type[Exception], Callable[[str, Optional[str]], str]] = {
    FileNotFoundError: lambda path, _: (
        f"The file '{path}' could not be found. Please check:\n"
        f"- If the file name is spelled correctly\n"
        f"- If the file exists in the specified location\n"
        f"- If you have the correct path"
    ),
    IsADirectoryError: lambda path, _: (f"'{path}' is a directory, not a file. Please specify a file path instead."),
    NotADirectoryError: lambda path, _: (f"'{path}' is not a directory. A directory path was expected."),
    PermissionError: lambda path, _: (
        f"You don't have permission to access '{path}'. Please check:\n"
        f"- If you have the necessary permissions\n"
        f"- If the file is locked by another process\n"
        f"- If you need elevated privileges"
    ),
    OSError: lambda path, err_msg: (
        f"Operating system error when accessing '{path}'.\n"
        f"Details: {err_msg}\n"
        f"This could be due to:\n"
        f"- Disk I/O errors\n"
        f"- Network file system issues\n"
        f"- Resource limitations"
    ),
}


def format_file_error(error: Exception, path: str, operation: str) -> str:
    """
    Format a file operation error with helpful context and suggestions.

    Args:
        error: The exception that was raised
        path: The path to the file that caused the error
        operation: A description of the operation being performed (e.g., "reading", "writing")

    Returns:
        A formatted error message with context and suggestions
    """
    error_type = type(error)
    error_msg = str(error)

    # Get the base suggestion for this error type or fall back to a generic message
    if error_type in ERROR_SUGGESTIONS:
        suggestion = ERROR_SUGGESTIONS[error_type](path, error_msg)
    else:
        suggestion = f"An unexpected error occurred when {operation} '{path}'.\n" f"Error details: {error_msg}"

    # Format the complete error message
    return f"Error: Failed when {operation} '{path}'.\n{suggestion}"


def format_path_restricted_error(path: str) -> str:
    """
    Format an error message for path restriction violations.

    Args:
        path: The path that was attempted to be accessed

    Returns:
        A formatted error message
    """
    return (
        f"Error: Path access restricted.\n"
        f"Can only access files within the current working directory "
        f"or its subdirectories.\n"
        f"Attempted path: '{path}'\n"
        f"Current working directory: '{Path.cwd()}'"
    )


def format_file_size_error(path: str, actual_size: float, max_size: float) -> str:
    """
    Format an error message for files that exceed the maximum allowed size.

    Args:
        path: The path to the file
        actual_size: The actual size of the file in bytes
        max_size: The maximum allowed size in bytes

    Returns:
        A formatted error message
    """
    actual_mb = actual_size / 1024 / 1024
    max_mb = max_size / 1024 / 1024

    return (
        f"Error: File '{path}' is too large ({actual_mb:.2f} MB).\n"
        f"Maximum allowed size is {max_mb:.2f} MB.\n"
        f"Consider:\n"
        f"- Using a smaller file\n"
        f"- Reading only a portion of the file\n"
        f"- Splitting the file into smaller chunks"
    )
