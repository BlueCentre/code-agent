"""
Progress indicator utilities for Code Agent.

This module provides standardized thinking indicators and step-by-step
progress tracking for various operations in the Code Agent.
"""

from contextlib import contextmanager

from rich.console import Console
from rich.status import Status

# Console instance for consistent styling
console = Console()

# Standard spinner style
DEFAULT_SPINNER = "dots"
DEFAULT_STYLE = "bold green"


@contextmanager
def thinking_indicator(message: str = "Agent is thinking...", spinner: str = DEFAULT_SPINNER, style: str = DEFAULT_STYLE):
    """
    Context manager that displays an animated thinking indicator.

    Args:
        message: The message to display
        spinner: The spinner style to use (dots, line, etc.)
        style: The rich style to apply to the message
    """
    with Status(f"[{style}]{message}[/{style}]", spinner=spinner) as status:
        yield status


@contextmanager
def file_operation_indicator(operation: str, filepath: str, spinner: str = DEFAULT_SPINNER):
    """
    Context manager for file operations with appropriate styling.

    Args:
        operation: The operation being performed (reading, writing, etc.)
        filepath: The path to the file being operated on
        spinner: The spinner style to use
    """
    message = f"{operation} {filepath}..."
    with Status(f"[bold blue]{message}[/bold blue]", spinner=spinner) as status:
        yield status


@contextmanager
def command_execution_indicator(command: str, spinner: str = DEFAULT_SPINNER):
    """
    Context manager for command execution with appropriate styling.

    Args:
        command: The command being executed
        spinner: The spinner style to use
    """
    # Truncate command if too long for display
    display_command = command
    if len(display_command) > 50:
        display_command = command[:47] + "..."

    message = f"Executing: {display_command}"
    with Status(f"[bold yellow]{message}[/bold yellow]", spinner=spinner) as status:
        yield status


def step_progress(step_name: str, color: str = "blue", completed: bool = False):
    """
    Display a step in a multi-step process.

    Args:
        step_name: The name of the step
        color: The color to use for the step indicator
        completed: Whether the step is completed
    """
    icon = "✓" if completed else "◆"
    console.print(f"[bold {color}]{icon} {step_name}[/bold {color}]")


def operation_complete(message: str):
    """Display a completion message with green checkmark."""
    console.print(f"[bold green]✓ {message}[/bold green]")


def operation_warning(message: str):
    """Display a warning message with yellow triangle."""
    console.print(f"[bold yellow]⚠ {message}[/bold yellow]")


def operation_error(message: str):
    """Display an error message with red X."""
    console.print(f"[bold red]✗ {message}[/bold red]")
