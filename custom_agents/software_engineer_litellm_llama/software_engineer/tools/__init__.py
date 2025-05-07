# ruff: noqa: I001, F401
"""Tools for the Software Engineer Multi-Agent."""

from . import (
    analysis_state,
    code_analysis,
    code_search,
    filesystem,
    search,
    shell_command,
    system_info,
)

# Export code analysis tools
from .code_analysis import (
    analyze_code_tool,
    get_analysis_issues_by_severity_tool,
    suggest_code_fixes_tool,
)

# Export the code search tool for easier imports
from .code_search import codebase_search_tool

# Export filesystem tools
from .filesystem import (
    read_file_tool,
    list_dir_tool,
    edit_file_tool,
    configure_file_edit_approval_tool,
    configure_approval_tool,
)

# Export shell command tools
from .shell_command import (
    check_command_exists_tool,
    check_shell_command_safety_tool,
    configure_shell_approval_tool,
    configure_shell_whitelist_tool,
    execute_vetted_shell_command_tool,
)

# Export search tools
from .search import google_search_grounding

# Export system info tools
from .system_info import (
    get_os_info_tool,
    list_available_tools_tool,
    list_tools_tool,
    available_tools_tool,
)

# Import system info tools

# Import the placeholder memory persistence tools
from .persistent_memory_tool import (
    save_current_session_to_file_tool,
    load_memory_from_file_tool,
)

__all__ = [
    # Filesystem Tools
    "read_file_tool",
    "list_dir_tool",
    "edit_file_tool",
    "configure_file_edit_approval_tool",
    "configure_approval_tool",
    # Shell Command Tools
    "check_command_exists_tool",
    "check_shell_command_safety_tool",
    "configure_shell_approval_tool",
    "configure_shell_whitelist_tool",
    "execute_vetted_shell_command_tool",
    # Code Analysis Tools (add if needed by root agent, or keep in sub-agent)
    # "analyze_code_tool",
    # "get_analysis_issues_by_severity_tool",
    # "suggest_code_fixes_tool",
    # Search Tools
    "google_search_grounding",
    "codebase_search_tool",
    # System Info Tools
    "get_os_info_tool",
    "list_available_tools_tool",
    "list_tools_tool",  # Alias
    "available_tools_tool",  # Alias
    # Placeholder Persistent Memory Tools
    "save_current_session_to_file_tool",
    "load_memory_from_file_tool",
]
