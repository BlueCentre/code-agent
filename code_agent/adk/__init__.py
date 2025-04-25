"""
Google ADK integration for Code Agent.

This package contains the integration code for the Google Agent Development Kit (ADK)
with the Code Agent framework. It provides adapters, configurations, and utilities for
using ADK in the Code Agent ecosystem.
"""

import google.adk

# Export version for convenience
__adk_version__ = google.adk.__version__

# Re-export tool wrappers
from code_agent.adk.tools import (  # noqa
    create_read_file_tool,
    create_delete_file_tool,
    create_apply_edit_tool,
    create_list_dir_tool,
    create_run_terminal_cmd_tool,
    get_file_tools,
    get_all_tools,
)

# Re-export model implementations
from code_agent.adk.models import (  # noqa
    LiteLlm,
    OllamaLlm,
    create_model,
    get_model_providers,
    get_default_models_by_provider,
)
