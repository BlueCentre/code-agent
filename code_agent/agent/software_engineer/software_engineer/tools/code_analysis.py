"""Code analysis tool for the software engineer agent."""

import os
from typing import Annotated, Any, Dict

from google.adk.tools import FunctionTool, ToolContext
from pydantic import Field


def _analyze_code(file_path: Annotated[str, Field(description="Path to the file to analyze")], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Analyze code in a file for quality issues.

    Args:
        file_path: Path to the file to analyze.
        tool_context: The tool context from ADK.

    Returns:
        Dict containing analysis results.
    """
    # In a real implementation, this would use static analysis tools
    # or other code analysis libraries. For this example, we'll simulate
    # the analysis.

    try:
        if not os.path.exists(file_path):
            return {"error": f"File {file_path} does not exist"}

        with open(file_path, "r") as file:
            code = file.read()

        # Store the code in the state for the agent to access
        tool_context.state["analyzed_code"] = code
        tool_context.state["analyzed_file"] = file_path

        # In a real implementation, we would run static analysis here
        # For now, just return basic information
        return {"file_path": file_path, "lines_of_code": len(code.split("\n")), "status": "Analysis complete"}
    except Exception as e:
        return {"error": f"Error analyzing file: {e!s}"}


# Define the tool using FunctionTool
analyze_code_tool = FunctionTool(
    func=_analyze_code,
    # Description comes from func docstring
    # input_model=AnalyzeCodeInput, # Input schema inferred from func signature
)
