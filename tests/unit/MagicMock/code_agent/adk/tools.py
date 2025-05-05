"""
Mock implementations of classes from code_agent.adk.tools.
"""

import inspect
import json
from typing import Any, Callable, Dict, Optional


def parse_json(json_string: Optional[str]) -> Optional[Any]:
    """
    Parse a JSON string into a Python object.

    Args:
        json_string: The JSON string to parse

    Returns:
        The parsed object or None if parsing fails
    """
    if not json_string:
        return None

    try:
        return json.loads(json_string)
    except Exception:
        return None


def prepare_error_response(error: Exception) -> str:
    """
    Prepare a human-readable error response from an exception.

    Args:
        error: The exception to format

    Returns:
        A formatted error message
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Include cause if available
    if error.__cause__:
        cause_type = type(error.__cause__).__name__
        cause_message = str(error.__cause__)
        return f"Error ({error_type}): {error_message}\nCaused by {cause_type}: {cause_message}"

    return f"Error ({error_type}): {error_message}"


def get_tool_parameter_description(parameter_spec: Optional[Dict], parameter_name: str) -> Optional[str]:
    """
    Extract the description for a parameter from its spec.

    Args:
        parameter_spec: The parameter specification
        parameter_name: The name of the parameter

    Returns:
        The parameter description or None if not found
    """
    if not parameter_spec:
        return None

    properties = parameter_spec.get("properties", {})
    if not properties:
        return None

    param_info = properties.get(parameter_name, {})
    if not param_info:
        return None

    return param_info.get("description")


def wrap_function(func: Callable, name: str, description: str, param_descriptions: Dict[str, str]) -> Callable:
    """
    Wrap a function to handle parameter validation and error handling.

    Args:
        func: The function to wrap
        name: The name of the function
        description: The description of the function
        param_descriptions: Descriptions for each parameter

    Returns:
        A wrapped version of the function
    """
    signature = inspect.signature(func)
    param_names = list(signature.parameters.keys())

    def wrapped_func(params: Dict[str, Any]) -> Any:
        # Validate required parameters are present
        for param_name, param in signature.parameters.items():
            is_required = param.default == inspect.Parameter.empty
            if is_required and param_name not in params:
                raise ValueError(f"Missing required parameter: {param_name}")

        # Check for unexpected parameters
        for param_name in params:
            if param_name not in param_names:
                raise ValueError(f"Unexpected parameter: {param_name}")

        # Call the function only if all required parameters are present
        try:
            return func(**params)
        except TypeError as e:
            # Convert TypeError to ValueError with a clearer message
            if "missing" in str(e) and "required" in str(e):
                missing_param = str(e).split("'")[-2]
                raise ValueError(f"Missing required parameter: {missing_param}")  # noqa: B904
            raise

    return wrapped_func


class ADKToolCall:
    """Mock class for ADKToolCall."""

    def __init__(self, tool_call_id: str, tool: Any, parameters: Dict[str, Any]):
        """
        Initialize a new tool call.

        Args:
            tool_call_id: The ID of the tool call
            tool: The tool to call
            parameters: The parameters to pass to the tool
        """
        self.tool_call_id = tool_call_id
        self.tool = tool
        self.parameters = parameters
        self.json = json.dumps(parameters)


class ADKFunctionTool:
    """Mock class for ADKFunctionTool."""

    def __init__(self, name: str, description: str, wrapped_function: Callable):
        """
        Initialize a new function tool.

        Args:
            name: The name of the tool
            description: The description of the tool
            wrapped_function: The function to call
        """
        self.name = name
        self.description = description
        self.wrapped_function = wrapped_function

    def execute(self, tool_call: ADKToolCall) -> str:
        """
        Execute the tool with the given parameters.

        Args:
            tool_call: The tool call to execute

        Returns:
            The result of the execution as a string
        """
        try:
            return self.wrapped_function(tool_call.parameters)
        except Exception as e:
            return prepare_error_response(e)


class ADKCommandTool:
    """Mock class for ADKCommandTool."""

    def __init__(self, name: str, description: str, command_template: str):
        """
        Initialize a new command tool.

        Args:
            name: The name of the tool
            description: The description of the tool
            command_template: The template for the command
        """
        self.name = name
        self.description = description
        self.command_template = command_template

    def execute(self, tool_call: ADKToolCall) -> str:
        """
        Execute the command with the given parameters.

        Args:
            tool_call: The tool call to execute

        Returns:
            The result of the execution as a string
        """
        try:
            # Format the command template with the parameters
            command = self.command_template.format(**tool_call.parameters)

            # In a real implementation, we would execute the command here
            # For the mock, we'll just return a success message
            return f"Command executed: {command}"

        except KeyError as e:
            return prepare_error_response(e)
        except Exception as e:
            return prepare_error_response(e)
