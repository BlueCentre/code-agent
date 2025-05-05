"""
Mock implementations of exception classes from google.genai.exceptions.
"""


class GenAiException(Exception):
    """Base exception for GenAI-related errors."""

    pass


class LimitExceededException(GenAiException):
    """Exception raised when API limits are exceeded."""

    pass


class InvalidArgumentException(GenAiException):
    """Exception raised for invalid arguments."""

    pass


class AuthenticationException(GenAiException):
    """Exception raised for authentication errors."""

    pass


class UnknownException(GenAiException):
    """Exception raised for unknown errors."""

    pass
