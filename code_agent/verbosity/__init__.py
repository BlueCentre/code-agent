"""
Verbosity control module for code-agent.

This module provides utilities for controlling the verbosity level
of output displayed to users.
"""

# Expose core components
# Re-export for easier access, but keep the definitions in controller.py
from .controller import VerbosityController, VerbosityLevel, get_controller

__all__ = ["VerbosityLevel", "VerbosityController", "get_controller"]
