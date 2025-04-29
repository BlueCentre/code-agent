"""
Google ADK integration for Code Agent.

This package contains the integration code for the Google Agent Development Kit (ADK)
with the Code Agent framework. It provides adapters, configurations, and utilities for
using ADK in the Code Agent ecosystem.
"""

import logging

# import sys # Removed F401
# from enum import Enum # Removed F401
# from typing import Any, Dict, List, Optional, Union # Removed F401
import google.adk

# Export version for convenience
__adk_version__ = google.adk.__version__

# Conditionally import ADK components to avoid errors if not installed
try:
    from code_agent.adk.models import (  # noqa
        LiteLlm,
        OllamaLlm,
        create_model,
        get_default_models_by_provider,
        get_model_providers,
    )
    from code_agent.adk.tools import (
        create_apply_edit_tool,  # noqa: F401
        create_delete_file_tool,  # noqa: F401
        create_list_dir_tool,  # noqa: F401
        create_read_file_tool,  # noqa: F401
        create_run_terminal_cmd_tool,  # noqa: F401
        get_all_tools,  # noqa: F401
        get_file_tools,  # noqa: F401
    )
except ImportError:
    pass

from .memory import BaseMemoryService, InMemoryMemoryService, MemoryResult, MemoryType, SearchMemoryResponse
from .services import CodeAgentADKSessionManager, get_adk_session_service, get_memory_service
from .session_config import IN_MEMORY_SESSION_CONFIG, CodeAgentSessionConfig

logger = logging.getLogger(__name__)

__all__ = [
    "IN_MEMORY_SESSION_CONFIG",
    "BaseMemoryService",
    "CodeAgentADKSessionManager",
    "CodeAgentSessionConfig",
    "InMemoryMemoryService",
    "MemoryResult",
    "MemoryType",
    "SearchMemoryResponse",
    "get_adk_session_service",
    "get_memory_service",
]
