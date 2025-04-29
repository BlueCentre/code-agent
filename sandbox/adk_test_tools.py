#!/usr/bin/env python
"""ADK Tools Testing Sandbox.

This script allows testing the ADK tool implementations in a sandbox environment.
"""

import sys
from pathlib import Path

# First, modify path to include the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Then import the modules after path is set up
import google.adk as adk

from code_agent.adk.tools import create_apply_edit_tool, create_delete_file_tool, create_read_file_tool


def create_mock_tool_context():
    """Create a mock ToolContext for testing."""

    # This is a simple mock implementation for testing
    class MockLogger:
        def info(self, msg):
            print(f"INFO: {msg}")

        def error(self, msg):
            print(f"ERROR: {msg}")

        def warning(self, msg):
            print(f"WARNING: {msg}")

    class MockToolContext:
        def __init__(self):
            self.logger = MockLogger()

    return MockToolContext()


def create_test_file(filename, content):
    """Create a test file in the current working directory."""
    path = Path.cwd() / filename
    path.write_text(content)
    return path


def test_read_file():
    """Test the read_file tool."""
    print("\n=== Testing read_file tool ===")

    # Create a test file in the current directory
    test_file = "test_read_file_temp.txt"
    test_content = "This is a test file.\nIt has multiple lines.\nFor testing purposes."
    file_path = create_test_file(test_file, test_content)

    try:
        # Get the tool function
        tool = create_read_file_tool()
        ctx = create_mock_tool_context()

        # Test the tool
        result = tool.func(ctx, test_file)
        print(f"Tool result:\n{result}")

        # Test with an invalid file
        invalid_result = tool.func(ctx, f"{test_file}_nonexistent")
        print(f"Invalid file result:\n{invalid_result}")

    finally:
        # Clean up
        if file_path.exists():
            file_path.unlink()


def test_apply_edit():
    """Test the apply_edit tool."""
    print("\n=== Testing apply_edit tool ===")

    # Create a test file in the current directory
    test_file = "test_apply_edit_temp.txt"
    test_content = "This is a test file.\nIt has multiple lines.\nFor testing purposes."
    file_path = create_test_file(test_file, test_content)

    try:
        # Get the tool function
        tool = create_apply_edit_tool()
        ctx = create_mock_tool_context()

        # Create modified content
        new_content = "This is a modified test file.\nIt has multiple lines.\nFor testing purposes.\nWith an added line."

        # Normally, this would show a diff and prompt for confirmation
        # For testing, we'll just print what would happen
        print(f"Would apply edit to {test_file}")
        print(f"Old content: {file_path.read_text()}")
        print(f"New content: {new_content}")

        # This would typically require user confirmation
        print("NOTE: This test may require user confirmation. Enter 'y' if prompted.")
        result = tool.func(ctx, test_file, new_content)
        print(f"Tool result:\n{result}")

        # Verify the file was edited
        if "successfully" in result:
            print(f"Updated content: {file_path.read_text()}")

    finally:
        # Clean up
        if file_path.exists():
            file_path.unlink()


def test_delete_file():
    """Test the delete_file tool."""
    print("\n=== Testing delete_file tool ===")

    # Create a test file in the current directory
    test_file = "test_delete_file_temp.txt"
    test_content = "This is a test file that will be deleted."
    file_path = create_test_file(test_file, test_content)

    # Get the tool function
    tool = create_delete_file_tool()
    ctx = create_mock_tool_context()

    # Verify file exists
    print(f"File exists before deletion: {file_path.exists()}")

    # Test the tool
    result = tool.func(ctx, test_file)
    print(f"Tool result:\n{result}")

    # Verify file was deleted
    print(f"File exists after deletion: {file_path.exists()}")

    # Test with an already deleted file
    result2 = tool.func(ctx, test_file)
    print(f"Deleting non-existent file result:\n{result2}")


def main():
    """Run tests for ADK tools."""
    print("ADK Tools Testing Sandbox")
    print("=" * 80)

    print(f"ADK Version: {adk.__version__}")

    # Test individual tools
    test_read_file()
    test_apply_edit()
    test_delete_file()

    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
