"""Utility functions for formatting error messages in file operations, API calls, and other errors."""

from typing import Any, Callable, Dict, Optional, Type

# --- File Error Formatting Utilities ---

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
        suggestion = f"An unexpected error occurred when {operation} '{path}'.\nError details: {error_msg}"

    # Format the complete error message
    return f"Error: Failed when {operation} '{path}'.\n{suggestion}"


def format_path_restricted_error(path: str, reason: Optional[str] = None) -> str:
    """Formats an error message for a path that's restricted for security reasons."""
    base_message = (
        f"[bold red]Error:[/bold red] Path '{path}' is restricted for security reasons.\nOnly paths within the current working directory are allowed."
    )

    if reason:
        base_message += f"\nReason: {reason}"

    return base_message


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


# --- API Error Formatting Utilities ---


def format_api_error(error: Exception, provider: str, model: str) -> str:
    """
    Format an API error with helpful context and suggestions based on error type.

    Args:
        error: The exception that was raised
        provider: The LLM provider (e.g., "openai", "ai_studio")
        model: The model being used

    Returns:
        A formatted error message with context and suggestions
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Authentication errors
    if "AuthenticationError" in error_type or "api key" in error_msg.lower():
        return (
            f"Error: Authentication failed with {provider}.\n"
            f"Please check:\n"
            f"- If your API key is correct and not expired\n"
            f"- If your API key has been properly set in the configuration or environment\n"
            f"- If your API key has the necessary permissions\n"
            f"To set the API key, use one of these options:\n"
            f"1. Set the {provider.upper()}_API_KEY environment variable\n"
            f"2. Add it to your configuration file in ~/.config/code-agent/config.yaml"
        )

    # Rate limit errors
    elif "RateLimitError" in error_type or "rate limit" in error_msg.lower():
        return (
            f"Error: Rate limit exceeded when using {provider}/{model}.\n"
            f"Suggestions:\n"
            f"- Wait a few moments before trying again\n"
            f"- Upgrade your API usage tier if appropriate\n"
            f"- Consider using a different model with lower usage\n"
            f"- Implement request throttling in your workflow"
        )

    # Context length errors
    elif "ContextWindowExceededError" in error_type or "context length" in error_msg.lower():
        return (
            f"Error: Context length exceeded for {provider}/{model}.\n"
            f"Your input is too large for this model's context window.\n"
            f"Suggestions:\n"
            f"- Reduce the amount of text or code in your prompt\n"
            f"- Split your request into smaller pieces\n"
            f"- Try a model with a larger context window, if available"
        )

    # Model not found errors
    elif "NotFoundError" in error_type or "model not found" in error_msg.lower() or "is not found" in error_msg.lower():
        return (
            f"Error: Model '{model}' not found for provider '{provider}'.\n"
            f"Possible reasons:\n"
            f"- The model name may be incorrect or misspelled\n"
            f"- The model may not be available from this provider\n"
            f"- The model may have been deprecated or renamed\n"
            f"Try checking the provider's documentation for available models."
        )

    # Service unavailable errors
    elif "ServiceUnavailableError" in error_type or "service unavailable" in error_msg.lower():
        return (
            f"Error: {provider} service is currently unavailable.\n"
            f"This may be due to:\n"
            f"- Temporary service outage\n"
            f"- Scheduled maintenance\n"
            f"- Regional access issues\n"
            f"Suggestions:\n"
            f"- Check {provider}'s status page for known issues\n"
            f"- Try again later\n"
            f"- Consider using an alternative provider in the meantime"
        )

    # Handle other generic errors
    else:
        return (
            f"Error: An unexpected error occurred when calling {provider}/{model}.\n"
            f"Error type: {error_type}\n"
            f"Details: {error_msg}\n"
            f"Please check the provider's documentation and status page for more information."
        )


# --- Configuration Error Formatting Utilities ---


def format_config_error(error: Exception, config_item: Optional[str] = None) -> str:
    """
    Format a configuration error with helpful context and suggestions.

    Args:
        error: The exception that was raised
        config_item: The specific configuration item causing the error, if applicable

    Returns:
        A formatted error message with context and suggestions
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if config_item:
        context = f"Configuration error with '{config_item}'.\n"
    else:
        context = "Configuration error.\n"

    # Handle validation errors (from Pydantic)
    if "ValidationError" in error_type:
        # Parse and format Pydantic validation errors for better readability
        formatted_errors = ""
        try:
            # Try to extract individual validation errors if possible
            if hasattr(error, "errors") and callable(error.errors):
                errors_list = error.errors()
                for err in errors_list:
                    field = ".".join(str(loc) for loc in err["loc"]) if "loc" in err else "unknown"
                    msg = err.get("msg", "Invalid value")
                    formatted_errors += f"- Field '{field}': {msg}\n"
            else:
                formatted_errors = f"{error_msg}"
        except Exception:
            # Fall back to raw error message if parsing fails
            formatted_errors = f"{error_msg}"

        return (
            f"{context}"
            f"Validation failed with the following issues:\n"
            f"{formatted_errors}\n"
            f"Please check your configuration file at ~/.config/code-agent/config.yaml\n"
            f"or run 'code-agent config validate' to identify issues."
        )

    # Handle file not found errors
    elif isinstance(error, FileNotFoundError):
        return (
            f"{context}"
            f"Configuration file not found.\n"
            f"Looks like you haven't created a configuration file yet.\n\n"
            f"To create one, run:\n"
            f"code-agent config init\n\n"
            f"Or manually create a file at ~/.config/code-agent/config.yaml"
        )

    # Handle permission errors
    elif isinstance(error, PermissionError):
        return (
            f"{context}"
            f"Permission denied when accessing configuration file.\n"
            f"Check the file permissions on your configuration file and directory.\n"
            f"Make sure you have read/write access to ~/.config/code-agent/"
        )

    # Handle JSON/YAML parsing errors
    elif "JSONDecodeError" in error_type or "YAMLError" in error_type:
        return (
            f"{context}"
            f"Invalid configuration file format.\n"
            f"Your configuration file contains syntax errors.\n"
            f"Details: {error_msg}\n\n"
            f"Try checking the YAML syntax in your config file."
        )

    # Handle environment variable issues
    elif "EnvVariableError" in error_type or "environment variable" in error_msg.lower():
        return (
            f"{context}"
            f"Environment variable issue detected.\n"
            f"Details: {error_msg}\n\n"
            f"Check that all required environment variables are set correctly.\n"
            f"You can also set these values in your config.yaml file instead."
        )

    # Handle import errors (if config is trying to use unavailable modules)
    elif isinstance(error, ImportError) or "ImportError" in error_type or "ModuleNotFoundError" in error_type:
        return (
            f"{context}"
            f"Failed to import required module.\n"
            f"Details: {error_msg}\n\n"
            f"Make sure all required dependencies are installed:\n"
            f"pip install -U code-agent[all]"
        )

    # Handle invalid path configurations
    elif "Invalid path" in error_msg or "path" in error_msg.lower() and ("invalid" in error_msg.lower() or "not found" in error_msg.lower()):
        return (
            f"{context}"
            f"Invalid path configuration detected.\n"
            f"Details: {error_msg}\n\n"
            f"Check that all paths in your configuration are valid and accessible."
        )

    # Generic error fallback
    else:
        return (
            f"{context}"
            f"An unexpected error occurred: {error_msg}\n"
            f"Error type: {error_type}\n\n"
            f"Try checking your configuration settings or running with --debug for more information.\n"
            f"You can also try resetting to default configuration with 'code-agent config reset'."
        )


# --- Tool Execution Error Formatting Utilities ---


def format_tool_error(error: Exception, tool_name: str, args: Dict[str, Any] | None = None) -> str:
    """
    Format a tool execution error with helpful context and suggestions.

    Args:
        error: The exception that was raised
        tool_name: The name of the tool that failed
        args: The arguments passed to the tool, if available

    Returns:
        A formatted error message with context and suggestions
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # Format args summary if available
    args_summary = ""
    if args:
        # Don't show the entire content for 'code_edit' as it could be very large
        if "code_edit" in args and len(str(args["code_edit"])) > 50:
            safe_args = args.copy()
            safe_args["code_edit"] = f"{str(args['code_edit'])[:50]}... (truncated)"
            args_summary = f"\nArguments: {safe_args}"
        else:
            args_summary = f"\nArguments: {args}"

    # Default error message
    message = f"Error executing tool '{tool_name}'.\n" f"Error type: {error_type}\n" f"Details: {error_msg}{args_summary}"

    # Add specific suggestions based on the tool type
    if tool_name == "read_file":
        message += (
            "\n\nSuggestions for read_file issues:\n"
            "- Check if the file path is correct\n"
            "- Ensure the file exists and is accessible\n"
            "- Verify you have permission to read the file"
        )
    elif tool_name == "apply_edit":
        message += (
            "\n\nSuggestions for apply_edit issues:\n"
            "- Ensure the target file location is valid and writable\n"
            "- Check if you have permission to modify the file\n"
            "- Verify the edit content is valid for the file type"
        )
    elif tool_name == "run_native_command":
        message += (
            "\n\nSuggestions for run_native_command issues:\n"
            "- Check if the command exists on your system\n"
            "- Ensure the command is in your PATH\n"
            "- Verify the command is allowed by your configuration\n"
            "- Check for proper command syntax"
        )

    return message
