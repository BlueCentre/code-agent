"""Unit tests for ADK tool wrappers."""

import os
from pathlib import Path
from unittest import mock

import pytest

from code_agent.adk.tools import (
    create_apply_edit_tool,
    create_delete_file_tool,
    create_list_dir_tool,
    create_read_file_tool,
    create_run_terminal_cmd_tool,
)


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.info_messages = []
        self.error_messages = []
        self.warning_messages = []

    def info(self, msg):
        self.info_messages.append(msg)

    def error(self, msg):
        self.error_messages.append(msg)

    def warning(self, msg):
        self.warning_messages.append(msg)


class MockToolContext:
    """Mock ToolContext for testing."""

    def __init__(self):
        self.logger = MockLogger()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("This is a test file.\nIt has multiple lines.\nFor testing purposes.")
    relative_path = file_path.relative_to(Path.cwd())
    return str(relative_path)


@pytest.fixture
def mock_tool_context():
    """Create a mock tool context."""
    return MockToolContext()


@pytest.mark.parametrize(
    "file_exists,expected_status",
    [
        (True, "success"),
        (False, "error"),
    ],
)
def test_read_file_tool(tmp_path, mock_tool_context, file_exists, expected_status):
    """Test the read_file tool."""
    # Arrange
    tool = create_read_file_tool()

    if file_exists:
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("Test content")
        test_path = str(file_path)
    else:
        test_path = str(tmp_path / "nonexistent.txt")

    # Mock security check to avoid path restrictions
    with mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        # Act
        result = tool.func(mock_tool_context, test_path)

        # Assert
        if expected_status == "success":
            assert "Test content" in result
            assert "Error:" not in result
            assert len(mock_tool_context.logger.info_messages) >= 1
        else:
            assert "Error:" in result
            assert len(mock_tool_context.logger.error_messages) >= 1


def test_delete_file_tool(tmp_path, mock_tool_context):
    """Test the delete_file tool."""
    # Arrange
    tool = create_delete_file_tool()
    file_path = tmp_path / "test_delete.txt"
    file_path.write_text("Test content to delete")
    test_path = str(file_path)

    # Mock security check to avoid path restrictions
    with mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        # Act
        result = tool.func(mock_tool_context, test_path)

        # Assert
        assert "successfully" in result.lower()
        assert not os.path.exists(file_path)
        assert len(mock_tool_context.logger.info_messages) >= 1


def test_delete_nonexistent_file_tool(tmp_path, mock_tool_context):
    """Test the delete_file tool with a nonexistent file."""
    # Arrange
    tool = create_delete_file_tool()
    test_path = str(tmp_path / "nonexistent.txt")

    # Mock security check to avoid path restrictions
    with mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        # Act
        result = tool.func(mock_tool_context, test_path)

        # Assert
        assert "Error:" in result
        assert len(mock_tool_context.logger.error_messages) >= 1


def test_apply_edit_tool(tmp_path, mock_tool_context):
    """Test the apply_edit tool."""
    # Arrange
    tool = create_apply_edit_tool()
    file_path = tmp_path / "test_edit.txt"
    file_path.write_text("Original content")
    test_path = str(file_path)
    new_content = "Modified content"

    # We need to mock both file_tools.is_path_safe and simple_tools.is_path_within_cwd
    # since apply_edit implementation could be from either module
    with (
        mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)),
        mock.patch("code_agent.tools.simple_tools.is_path_within_cwd", return_value=True),
        mock.patch("code_agent.tools.simple_tools.Confirm.ask", return_value=True),
    ):
        # Act
        result = tool.func(mock_tool_context, test_path, new_content)

        # Assert
        assert "successfully" in result.lower() or "applied" in result.lower()
        assert file_path.read_text() == "Modified content"
        assert len(mock_tool_context.logger.info_messages) >= 1


def test_apply_edit_cancelled_tool(tmp_path, mock_tool_context):
    """Test the apply_edit tool when edit is cancelled."""
    # Arrange
    tool = create_apply_edit_tool()
    file_path = tmp_path / "test_edit_cancel.txt"
    file_path.write_text("Original content")
    test_path = str(file_path)
    new_content = "Modified content"

    # We need to mock both file_tools.is_path_safe and simple_tools.is_path_within_cwd
    # since apply_edit implementation could be from either module
    with (
        mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)),
        mock.patch("code_agent.tools.simple_tools.is_path_within_cwd", return_value=True),
        mock.patch("code_agent.tools.simple_tools.Confirm.ask", return_value=False),
    ):
        # Act
        result = tool.func(mock_tool_context, test_path, new_content)

        # Assert
        assert "cancelled" in result.lower()
        assert file_path.read_text() == "Original content"  # Content should not change
        # Either warning or error messages should be logged when cancelled
        assert len(mock_tool_context.logger.warning_messages) + len(mock_tool_context.logger.error_messages) >= 1


def test_list_dir_tool(tmp_path, mock_tool_context):
    """Test the list_dir tool."""
    # Arrange
    tool = create_list_dir_tool()

    # Create test directory structure
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    test_file1 = tmp_path / "test1.txt"
    test_file1.write_text("Test file 1")

    test_file2 = tmp_path / "test2.txt"
    test_file2.write_text("Test file 2")

    subfile = subdir / "subfile.txt"
    subfile.write_text("File in subdirectory")

    # Act
    result = tool.func(mock_tool_context, str(tmp_path))

    # Assert
    assert "Contents of directory" in result
    assert "Directories:" in result
    assert "subdir" in result
    assert "Files:" in result
    assert "test1.txt" in result
    assert "test2.txt" in result
    assert len(mock_tool_context.logger.info_messages) >= 1


def test_list_dir_nonexistent_path(mock_tool_context):
    """Test the list_dir tool with a nonexistent directory."""
    # Arrange
    tool = create_list_dir_tool()
    nonexistent_path = "/path/that/does/not/exist"

    # Act
    result = tool.func(mock_tool_context, nonexistent_path)

    # Assert
    assert "Error:" in result
    assert "does not exist" in result
    assert len(mock_tool_context.logger.error_messages) >= 1


def test_list_dir_not_a_directory(tmp_path, mock_tool_context):
    """Test the list_dir tool with a path that's a file, not a directory."""
    # Arrange
    tool = create_list_dir_tool()

    # Create a test file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("This is not a directory")

    # Act
    result = tool.func(mock_tool_context, str(test_file))

    # Assert
    assert "Error:" in result
    assert "not a directory" in result
    assert len(mock_tool_context.logger.error_messages) >= 1


def test_list_dir_empty_directory(tmp_path, mock_tool_context):
    """Test the list_dir tool with an empty directory."""
    # Arrange
    tool = create_list_dir_tool()
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    # Act
    result = tool.func(mock_tool_context, str(empty_dir))

    # Assert
    assert "Directory is empty" in result
    assert len(mock_tool_context.logger.info_messages) >= 1


def test_list_dir_exception_handling(mock_tool_context):
    """Test exception handling in the list_dir tool."""
    # Arrange
    tool = create_list_dir_tool()

    # Mock Path.resolve to raise an exception
    with mock.patch("pathlib.Path.resolve", side_effect=PermissionError("Permission denied")):
        # Act
        result = tool.func(mock_tool_context, "/test/path")

        # Assert
        assert "Error listing directory" in result
        assert "Permission denied" in result
        assert len(mock_tool_context.logger.error_messages) >= 1


def test_run_terminal_cmd_tool(mock_tool_context):
    """Test the run_terminal_cmd tool."""
    # Arrange
    tool = create_run_terminal_cmd_tool()
    command = "echo 'Hello, world!'"

    # Mock the security checks, confirmations, and all Rich components
    with (
        mock.patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False)),
        mock.patch("code_agent.tools.native_tools.Confirm.ask", return_value=True),
        mock.patch("code_agent.tools.native_tools.console"),
        mock.patch("code_agent.tools.native_tools.Panel"),
        mock.patch("code_agent.tools.native_tools.Text") as mock_text,
        mock.patch("code_agent.tools.native_tools.print"),
        mock.patch("code_agent.tools.progress_indicators.print"),
        mock.patch("subprocess.run") as mock_run,
    ):
        # Setup mock subprocess.run
        mock_run.return_value = mock.MagicMock(stdout="Hello, world!", stderr="", returncode=0)

        # Setup mock Text to return a string-like object
        mock_text.return_value = "EXECUTE COMMAND"

        # Act
        tool.func(mock_tool_context, command)

        # Assert
        assert mock_run.called
        assert len(mock_tool_context.logger.info_messages) >= 1


def test_run_terminal_cmd_with_background(mock_tool_context):
    """Test the run_terminal_cmd tool with background option."""
    # Arrange
    tool = create_run_terminal_cmd_tool()
    command = "echo 'Hello, world!'"

    # Mock the security checks, confirmations, and all Rich components
    with (
        mock.patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False)),
        mock.patch("code_agent.tools.native_tools.Confirm.ask", return_value=True),
        mock.patch("code_agent.tools.native_tools.console"),
        mock.patch("code_agent.tools.native_tools.Panel"),
        mock.patch("code_agent.tools.native_tools.Text") as mock_text,
        mock.patch("code_agent.tools.native_tools.print"),
        mock.patch("code_agent.tools.progress_indicators.print"),
        mock.patch("subprocess.run") as mock_run,
    ):
        # Setup mock subprocess.run
        mock_run.return_value = mock.MagicMock(stdout="Hello, world!", stderr="", returncode=0)

        # Setup mock Text to return a string-like object
        mock_text.return_value = "EXECUTE COMMAND"

        # Act
        tool.func(mock_tool_context, command, is_background=True)

        # Assert
        assert mock_run.called
        assert len(mock_tool_context.logger.warning_messages) >= 1  # Should warn about background not supported


def test_read_file_with_pagination(tmp_path, mock_tool_context):
    """Test the read_file tool with pagination enabled."""
    # Arrange
    tool = create_read_file_tool()
    file_path = tmp_path / "large_file.txt"

    # Create a large file with 100 lines
    file_path.write_text("\n".join([f"Line {i}" for i in range(1, 101)]))

    # Mock security check
    with mock.patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        # Act with pagination enabled, offset and limit
        result = tool.func(mock_tool_context, str(file_path), offset=10, limit=20, enable_pagination=True)

        # Assert
        assert "Line 11" in result  # 0-indexed, so line 11 is the first line after offset 10
        assert "Line 30" in result  # Should include up to line 30 (offset 10 + limit 20)
        assert "Line 31" not in result  # Should not include line 31
        assert len(mock_tool_context.logger.info_messages) >= 2


def test_run_terminal_cmd_error(mock_tool_context):
    """Test the run_terminal_cmd tool with a failing command."""
    # Arrange
    tool = create_run_terminal_cmd_tool()
    command = "invalid_command"

    # Mock security checks and functions
    with (
        mock.patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, None, False)),
        mock.patch("code_agent.tools.native_tools.Confirm.ask", return_value=True),
        mock.patch("code_agent.tools.native_tools.console"),
        mock.patch("code_agent.tools.native_tools.Panel"),
        mock.patch("code_agent.tools.native_tools.Text"),
        mock.patch("code_agent.tools.native_tools.print"),
        mock.patch("code_agent.tools.progress_indicators.print"),
        mock.patch("subprocess.run", side_effect=Exception("Command failed")),
    ):
        # Act
        result = tool.func(mock_tool_context, command)

        # Assert
        assert "Error executing command" in result
        assert len(mock_tool_context.logger.error_messages) >= 1


def test_get_file_tools():
    """Test the get_file_tools function returns the expected list of tools."""
    from code_agent.adk.tools import get_file_tools

    # Act
    tools = get_file_tools()

    # Assert
    assert len(tools) >= 4  # Should include read_file, delete_file, apply_edit, and list_dir

    # Check that all returned items are FunctionTool instances
    from google.adk.tools import FunctionTool

    for tool in tools:
        assert isinstance(tool, FunctionTool)


def test_get_all_tools():
    """Test the get_all_tools function returns all the expected tools."""
    from code_agent.adk.tools import get_all_tools

    # Act
    tools = get_all_tools()

    # Assert
    assert len(tools) >= 5  # Should include all file tools plus terminal cmd

    # Check that all returned items are FunctionTool instances
    from google.adk.tools import FunctionTool

    for tool in tools:
        assert isinstance(tool, FunctionTool)
