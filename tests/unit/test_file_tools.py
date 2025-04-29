"""
Tests for code_agent.adk.tools file operation functions.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from google.adk.tools import ToolContext

from code_agent.adk.tools import (
    create_apply_edit_tool,
    create_delete_file_tool,
    create_list_dir_tool,
    create_read_file_tool,
    get_file_tools,
    list_dir,
)


@pytest.fixture
def mock_tool_context():
    """Create a mock tool context for testing."""
    context = MagicMock(spec=ToolContext)
    # Add logger with tracking for messages
    context.logger = MagicMock()
    context.logger.info_messages = []
    context.logger.error_messages = []

    def track_info(msg):
        context.logger.info_messages.append(msg)

    def track_error(msg):
        context.logger.error_messages.append(msg)

    context.logger.info.side_effect = track_info
    context.logger.error.side_effect = track_error
    return context


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test files and directories
        os.makedirs(os.path.join(temp_dir, "subdir1"))
        os.makedirs(os.path.join(temp_dir, "subdir2"))

        # Create files with content
        with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
            f.write("This is file 1\nWith multiple lines\nand test content")

        with open(os.path.join(temp_dir, "file2.py"), "w") as f:
            f.write("def test_function():\n    return 'test'\n\n# Comment line")

        yield temp_dir


class TestListDirectory:
    """Test the list_dir function."""

    @pytest.mark.asyncio
    async def test_list_dir_success(self, temp_dir, mock_tool_context):
        """Test listing directory contents successfully."""
        result = await list_dir(mock_tool_context, temp_dir)

        # Should contain information about the directory contents
        assert "Contents of directory" in result
        assert "Directories:" in result
        assert "subdir1" in result
        assert "subdir2" in result
        assert "Files:" in result
        assert "file1.txt" in result
        assert "file2.py" in result

        # Should log success
        assert len(mock_tool_context.logger.info_messages) >= 1

    @pytest.mark.asyncio
    async def test_list_dir_nonexistent(self, mock_tool_context):
        """Test listing a directory that doesn't exist."""
        result = await list_dir(mock_tool_context, "/nonexistent/path")

        assert "Error: Path does not exist" in result
        assert len(mock_tool_context.logger.error_messages) >= 1

    @pytest.mark.asyncio
    async def test_list_dir_not_a_directory(self, temp_dir, mock_tool_context):
        """Test listing a path that isn't a directory."""
        file_path = os.path.join(temp_dir, "file1.txt")

        result = await list_dir(mock_tool_context, file_path)

        assert "Error: Path is not a directory" in result
        assert len(mock_tool_context.logger.error_messages) >= 1

    @pytest.mark.asyncio
    async def test_list_dir_empty(self, mock_tool_context):
        """Test listing an empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            result = await list_dir(mock_tool_context, empty_dir)

            assert "Directory is empty" in result
            assert len(mock_tool_context.logger.info_messages) >= 1

    @pytest.mark.asyncio
    async def test_list_dir_exception_handling(self, mock_tool_context):
        """Test exception handling in list_dir function."""
        # Mock Path.resolve to raise an exception
        with patch("pathlib.Path.resolve", side_effect=PermissionError("Permission denied")):
            result = await list_dir(mock_tool_context, "/test/path")

            assert "Error listing directory" in result
            assert "Permission denied" in result
            assert len(mock_tool_context.logger.error_messages) >= 1


class TestReadFile:
    """Test the read_file function."""

    @pytest.mark.asyncio
    async def test_read_file_tool_creation(self):
        """Test creating the read_file tool."""
        tool = create_read_file_tool()

        assert tool.name == "read_file"
        assert callable(tool.func)

    @pytest.mark.asyncio
    async def test_delete_file_tool_creation(self):
        """Test creating the delete_file tool."""
        tool = create_delete_file_tool()

        assert tool.name == "delete_file"
        assert callable(tool.func)

    @pytest.mark.asyncio
    async def test_apply_edit_tool_creation(self):
        """Test creating the apply_edit tool."""
        tool = create_apply_edit_tool()

        assert tool.name == "apply_edit"
        assert callable(tool.func)

    @pytest.mark.asyncio
    async def test_list_dir_tool_creation(self):
        """Test creating the list_dir tool."""
        tool = create_list_dir_tool()

        assert tool.name == "list_dir"
        assert callable(tool.func)


class TestFileTools:
    """Test the get_file_tools function."""

    def test_get_file_tools_returns_tools(self):
        """Test that get_file_tools returns a list of tools."""
        tools = get_file_tools()

        assert len(tools) >= 4
        # Verify tool names are present
        tool_names = [tool.name for tool in tools]
        assert "read_file" in tool_names
        assert "delete_file" in tool_names
        assert "apply_edit" in tool_names
        assert "list_dir" in tool_names
