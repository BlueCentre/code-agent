"""
Verbosity controller for code-agent tools.

This module provides a proxy to the main verbosity controller,
allowing tools to import verbosity utilities consistently.
"""

# Re-export the verbosity controller from the main module
from code_agent.verbosity import get_controller, VerbosityController, VerbosityLevel
