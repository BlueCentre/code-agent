"""
Google ADK integration for Code Agent.

This package contains the integration code for the Google Agent Development Kit (ADK)
with the Code Agent framework. It provides adapters, configurations, and utilities for
using ADK in the Code Agent ecosystem.
"""

import google.adk

# Export version for convenience
__adk_version__ = google.adk.__version__

# Re-export common components
from code_agent.adk.session_config import (  # noqa
    SessionConfig,
    SessionPersistenceType,
    SessionMemoryType,
    create_default_session_config,
    create_persistent_session_config,
)
