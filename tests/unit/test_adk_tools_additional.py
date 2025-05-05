"""
Additional unit tests for code_agent.adk.tools module to increase coverage.

These tests focus on edge cases and error handling in the tools module.
"""

import unittest
from unittest.mock import MagicMock, patch

from google.adk.tools import FunctionTool
from google.adk.tools.google_search_tool import GoogleSearchTool

from code_agent.adk.tools import (
    create_apply_edit_tool,
    create_delete_file_tool,
    create_google_search_tool,
    create_list_dir_tool,
    create_read_file_tool,
    create_run_terminal_cmd_tool,
    get_all_tools,
    get_file_tools,
)


class TestCreateReadFileTool(unittest.TestCase):
    """Test the create_read_file_tool function."""

    def test_create_read_file_tool(self):
        """Test creating a read file tool."""
        tool = create_read_file_tool()

        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "read_file")
        self.assertTrue(callable(tool.func))


class TestCreateDeleteFileTool(unittest.TestCase):
    """Test the create_delete_file_tool function."""

    def test_create_delete_file_tool(self):
        """Test creating a delete file tool."""
        tool = create_delete_file_tool()

        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "delete_file")
        self.assertTrue(callable(tool.func))


class TestCreateApplyEditTool(unittest.TestCase):
    """Test the create_apply_edit_tool function."""

    def test_create_apply_edit_tool(self):
        """Test creating an apply edit tool."""
        tool = create_apply_edit_tool()

        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "apply_edit")
        self.assertTrue(callable(tool.func))


class TestCreateListDirTool(unittest.TestCase):
    """Test the create_list_dir_tool function."""

    def test_create_list_dir_tool(self):
        """Test creating a list directory tool."""
        tool = create_list_dir_tool()

        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "list_dir")
        self.assertTrue(callable(tool.func))


class TestCreateRunTerminalCmdTool(unittest.TestCase):
    """Test the create_run_terminal_cmd_tool function."""

    def test_create_run_terminal_cmd_tool(self):
        """Test creating a run terminal command tool."""
        tool = create_run_terminal_cmd_tool()

        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "run_terminal_cmd")
        self.assertTrue(callable(tool.func))


class TestCreateGoogleSearchTool(unittest.TestCase):
    """Test the create_google_search_tool function."""

    def test_create_google_search_tool(self):
        """Test creating a Google search tool."""
        tool = create_google_search_tool()

        self.assertIsInstance(tool, GoogleSearchTool)
        self.assertEqual(tool.name, "google_search")


class TestGetFileTool(unittest.TestCase):
    """Test the get_file_tools function."""

    def test_get_file_tools(self):
        """Test getting all file tools."""
        tools = get_file_tools()

        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 4)  # read_file, delete_file, apply_edit, list_dir
        tool_names = [tool.name for tool in tools]
        self.assertIn("read_file", tool_names)
        self.assertIn("delete_file", tool_names)
        self.assertIn("apply_edit", tool_names)
        self.assertIn("list_dir", tool_names)


class TestGetAllTools(unittest.TestCase):
    """Test the get_all_tools function."""

    def test_get_all_tools(self):
        """Test getting all tools."""
        tools = get_all_tools()

        self.assertIsInstance(tools, list)
        self.assertTrue(len(tools) >= 5)  # At least basic tools
        tool_names = [tool.name for tool in tools]
        self.assertIn("read_file", tool_names)
        self.assertIn("delete_file", tool_names)
        self.assertIn("apply_edit", tool_names)
        self.assertIn("list_dir", tool_names)
        self.assertIn("run_terminal_cmd", tool_names)


class TestReadFileToolExecution(unittest.TestCase):
    """Test the read_file function execution."""

    @patch("code_agent.adk.tools.original_read_file")
    async def test_read_file_tool_execution(self, mock_read_file):
        """Test execution of the read file tool."""
        # Set up mock to return a file content
        mock_read_file.return_value = "File content"

        # Create tool context
        tool_context = MagicMock()
        tool_context.logger = MagicMock()

        # Create read file tool
        tool = create_read_file_tool()  # noqa: F841

        # Call the function
        from code_agent.adk.tools import read_file

        result = await read_file(tool_context, path="test.txt", offset=0, limit=100)

        # Verify function was called with the correct arguments
        self.assertEqual(result, "File content")
        tool_context.logger.info.assert_any_call("Reading file: test.txt")
        tool_context.logger.info.assert_any_call("Successfully read file: test.txt (12 bytes)")

        # Don't return anything from the test method
        return None


class TestDeleteFileToolExecution(unittest.TestCase):
    """Test the delete_file function execution."""

    @patch("code_agent.adk.tools.original_delete_file")
    async def test_delete_file_tool_execution(self, mock_delete_file):
        """Test execution of the delete file tool."""
        # Set up mock to return a success message
        mock_delete_file.return_value = "Successfully deleted file: test.txt"

        # Create tool context
        tool_context = MagicMock()
        tool_context.logger = MagicMock()

        # Create delete file tool
        tool = create_delete_file_tool()  # noqa: F841

        # Call the function
        from code_agent.adk.tools import delete_file

        result = await delete_file(tool_context, path="test.txt")

        # Verify function was called with the correct arguments
        self.assertEqual(result, "Successfully deleted file: test.txt")
        tool_context.logger.info.assert_any_call("Deleting file: test.txt")
        tool_context.logger.info.assert_any_call("Successfully deleted file: test.txt")

        # Don't return anything from the test method
        return None


class TestApplyEditToolExecution(unittest.TestCase):
    """Test the apply_edit function execution."""

    @patch("code_agent.adk.tools.original_apply_edit")
    async def test_apply_edit_tool_execution(self, mock_apply_edit):
        """Test execution of the apply edit tool."""
        # Set up mock to return a success message
        mock_apply_edit.return_value = "Successfully edited file: test.txt"

        # Create tool context
        tool_context = MagicMock()
        tool_context.logger = MagicMock()

        # Create apply edit tool
        tool = create_apply_edit_tool()  # noqa: F841

        # Call the function
        from code_agent.adk.tools import apply_edit

        result = await apply_edit(tool_context, target_file="test.txt", code_edit="New content")

        # Verify function was called with the correct arguments
        self.assertEqual(result, "Successfully edited file: test.txt")
        tool_context.logger.info.assert_any_call("Applying edit to file: test.txt")
        tool_context.logger.info.assert_any_call("Successfully edited file: test.txt")

        # Don't return anything from the test method
        return None
