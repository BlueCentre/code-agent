"""
Verbosity controller for code-agent.

This module defines the VerbosityController class and related utilities
for managing output verbosity in the application.
"""

import inspect
import os
from enum import Enum
from typing import Any, Optional

from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel


class VerbosityLevel(Enum):
    """Enumeration of verbosity levels."""

    QUIET = 0  # Only show errors and critical information
    NORMAL = 1  # Standard user output (default)
    VERBOSE = 2  # Additional information and warnings
    DEBUG = 3  # Detailed diagnostic information

    @classmethod
    def from_string(cls, level_str: str) -> "VerbosityLevel":
        """Convert a string level to VerbosityLevel enum."""
        try:
            # Try to match the name (case-insensitive)
            return cls[level_str.upper()]
        except KeyError:
            # Try to parse as an integer
            try:
                level_num = int(level_str)
                for level in cls:
                    if level.value == level_num:
                        return level
                # Fall back to NORMAL if number is out of range
                return cls.NORMAL
            except ValueError:
                # Neither a valid name nor a number, fall back to NORMAL
                return cls.NORMAL


class VerbosityController:
    """
    Controls the verbosity level of the application output.

    This singleton class provides methods to display output at different
    verbosity levels and to change the current verbosity setting.
    """

    _instance: Optional["VerbosityController"] = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(VerbosityController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, initial_level: VerbosityLevel = VerbosityLevel.NORMAL):
        """Initialize the controller with a default verbosity level."""
        if self._initialized:
            return

        self.console = Console()
        self._level = initial_level
        self._initialized = True

        # Environment variable override
        env_verbosity = os.environ.get("CODE_AGENT_VERBOSITY")
        if env_verbosity:
            self.set_level(VerbosityLevel.from_string(env_verbosity))

    def start(self):
        """Initialize and start the verbosity controller.

        This method is called at the beginning of CLI commands to prepare
        the controller for use.
        """
        # Nothing to do here currently but it's included for future expansion
        # and to maintain compatibility with current code calling it
        if self.is_level_enabled(VerbosityLevel.DEBUG):
            self.show_debug("VerbosityController started")

    def stop(self):
        """Clean up and stop the verbosity controller.

        This method is called at the end of CLI commands to perform any necessary
        cleanup before exiting.
        """
        # Nothing to do here currently but it's included for future expansion
        # and to maintain compatibility with current code calling it
        if self.is_level_enabled(VerbosityLevel.DEBUG):
            self.show_debug("VerbosityController stopped")

    @property
    def level(self) -> VerbosityLevel:
        """Get the current verbosity level."""
        return self._level

    @property
    def level_value(self) -> int:
        """Get the current verbosity level as an integer."""
        return self._level.value

    @property
    def level_name(self) -> str:
        """Get the current verbosity level name."""
        return self._level.name

    def set_level(self, level: VerbosityLevel) -> str:
        """Set the verbosity level and return confirmation message."""
        old_level = self._level
        self._level = level
        return f"Verbosity changed from {old_level.name} to {level.name}"

    def set_level_from_string(self, level_str: str) -> str:
        """Set the verbosity level from a string and return confirmation."""
        level = VerbosityLevel.from_string(level_str)
        return self.set_level(level)

    def is_level_enabled(self, level: VerbosityLevel) -> bool:
        """Check if the specified verbosity level is enabled."""
        return self._level.value >= level.value

    def show(self, message: str, level: VerbosityLevel = VerbosityLevel.NORMAL, **kwargs):
        """
        Show a message if the current verbosity level is sufficient.
        Additional kwargs are passed to rich_print.
        """
        if self.is_level_enabled(level):
            rich_print(message, **kwargs)

    def show_quiet(self, message: str, **kwargs):
        """Show a message at QUIET level (always shown)."""
        self.show(message, VerbosityLevel.QUIET, **kwargs)

    def show_normal(self, message: str, **kwargs):
        """Show a message at NORMAL level."""
        self.show(message, VerbosityLevel.NORMAL, **kwargs)

    def show_verbose(self, message: str, **kwargs):
        """Show a message at VERBOSE level."""
        self.show(message, VerbosityLevel.VERBOSE, **kwargs)

    def show_debug(self, message: str, **kwargs):
        """Show a message at DEBUG level."""
        self.show(message, VerbosityLevel.DEBUG, **kwargs)

    def show_error(self, message: str, **kwargs):
        """Show an error message (always shown regardless of verbosity)."""
        self.show(f"[bold red]Error:[/bold red] {message}", VerbosityLevel.QUIET, **kwargs)

    def show_warning(self, message: str, **kwargs):
        """Show a warning message (shown at VERBOSE and above)."""
        self.show(f"[bold yellow]Warning:[/bold yellow] {message}", VerbosityLevel.VERBOSE, **kwargs)

    def show_info(self, message: str, **kwargs):
        """Show an info message (shown at NORMAL and above)."""
        self.show(f"[bold blue]Info:[/bold blue] {message}", VerbosityLevel.NORMAL, **kwargs)

    def show_success(self, message: str, **kwargs):
        """Show a success message (shown at NORMAL and above)."""
        self.show(f"[bold green]Success:[/bold green] {message}", VerbosityLevel.NORMAL, **kwargs)

    def show_debug_info(self, obj: Any = None, **kwargs):
        """
        Show detailed debug information about the calling context and optionally an object.
        Only shown at DEBUG level.
        """
        if not self.is_level_enabled(VerbosityLevel.DEBUG):
            return

        # Get caller information
        frame = inspect.currentframe().f_back
        caller_info = inspect.getframeinfo(frame)

        debug_panel = Panel(
            f"File: {caller_info.filename}\nFunction: {caller_info.function}\nLine: {caller_info.lineno}\n" + (f"Object: {obj!r}\n" if obj is not None else ""),
            title="[bold]Debug Info[/bold]",
            border_style="blue",
        )

        self.console.print(debug_panel)


def get_controller() -> VerbosityController:
    """Get or create the singleton VerbosityController instance."""
    return VerbosityController()
