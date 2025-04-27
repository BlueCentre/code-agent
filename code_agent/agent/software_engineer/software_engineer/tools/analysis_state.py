# software_engineer/tools/analysis_state.py
"""Tool to access analysis results stored in session state."""

from typing import Any, Dict

from google.adk.tools import FunctionTool, ToolContext


def get_analysis_issues(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves code analysis issues from the session state.

    Args:
        tool_context: The tool context from ADK.

    Returns:
        A dictionary containing the list of analysis issues under the key 'issues',
        or an empty list if no issues are found in the state.
    """
    issues = tool_context.state.get("analysis_issues", [])
    return {"issues": issues}


# Define the tool using FunctionTool
get_analysis_issues_tool = FunctionTool(
    func=get_analysis_issues,
    # Description comes from func docstring
)
