"""
Tests for the file_tools module to improve coverage.

These tests focus on edge cases and error handling in the file_tools module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.simple_tools import (
    MAX_FILE_SIZE_BYTES,
    apply_edit,
    is_path_within_cwd,
    read_file,
)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return file_path


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    # Use module-level patch for get_config to handle internal imports
    with patch("code_agent.config.config.get_config") as mock_get_config:
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config
        yield config


# For test purposes, we'll mock is_path_within_cwd to always return True during tests
@pytest.fixture(autouse=True)
def mock_path_validation():
    """Mock the is_path_within_cwd function to always return True for tests."""
    with patch("code_agent.tools.simple_tools.is_path_within_cwd", return_value=True):
        yield


class TestReadFile:
    """Tests for the read_file function."""

    def test_read_file_path_outside_cwd(self):
        """Test that read_file rejects paths outside current working directory."""
        # Override the fixture for this specific test
        with patch("code_agent.tools.simple_tools.is_path_within_cwd", return_value=False):
            result = read_file("/some/absolute/path")
            assert "Error: Path access restricted" in result

    def test_read_file_not_a_file(self):
        """Test read_file with a path that exists but is not a file."""
        with patch("pathlib.Path.is_file", return_value=False):
            result = read_file("some_directory")
            assert "Error: File not found or is not a regular file" in result

    def test_read_file_too_large(self):
        """Test read_file with a file that exceeds the size limit."""
        with patch("pathlib.Path.is_file", return_value=True):
            # Create a stat_result-like object
            stat_result = type("MockStatResult", (), {"st_size": MAX_FILE_SIZE_BYTES + 1})
            with patch("pathlib.Path.stat", return_value=stat_result):
                result = read_file("large_file.txt")
                assert "Error: File is too large" in result

    def test_read_file_stat_error(self):
        """Test read_file when an error occurs getting file statistics."""
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.stat", side_effect=OSError("stat error")):
                result = read_file("problem_file.txt")
                assert "Error getting file size" in result

    def test_read_file_not_found(self):
        """Test read_file with a nonexistent file."""
        with patch("pathlib.Path.is_file", return_value=True):
            # Create a stat_result-like object
            stat_result = type("MockStatResult", (), {"st_size": 100})
            with patch("pathlib.Path.stat", return_value=stat_result):
                with patch("pathlib.Path.read_text", side_effect=FileNotFoundError("Not found")):
                    result = read_file("nonexistent.txt")
                    assert "Error: File not found" in result

    def test_read_file_permission_error(self):
        """Test read_file with a file that causes a permission error."""
        with patch("pathlib.Path.is_file", return_value=True):
            # Create a stat_result-like object
            stat_result = type("MockStatResult", (), {"st_size": 100})
            with patch("pathlib.Path.stat", return_value=stat_result):
                with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                    result = read_file("protected.txt")
                    assert "Error: Permission denied" in result

    def test_read_file_generic_error(self):
        """Test read_file with a file that causes a generic error."""
        with patch("pathlib.Path.is_file", return_value=True):
            # Create a stat_result-like object
            stat_result = type("MockStatResult", (), {"st_size": 100})
            with patch("pathlib.Path.stat", return_value=stat_result):
                with patch("pathlib.Path.read_text", side_effect=Exception("Generic error")):
                    result = read_file("error.txt")
                    assert "Error reading file" in result

    def test_read_file_success(self):
        """Test reading a file successfully."""
        # Create a test content
        test_content = "line 1\nline 2\nline 3\nline 4\nline 5\n"

        # Mock the read_text method to return our test content
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.stat", return_value=type("MockStatResult", (), {"st_size": 100})):
                with patch("pathlib.Path.read_text", return_value=test_content):
                    result = read_file("test_file.txt")
                    assert "line 1" in result
                    assert "line 5" in result

    def test_read_file_nonexistent(self):
        """Test reading a nonexistent file."""
        with patch("pathlib.Path.is_file", side_effect=FileNotFoundError("No such file or directory")):
            result = read_file("/nonexistent/file.txt")
            assert "Error:" in result
            assert "File not found" in result

    def test_read_file_directory(self):
        """Test reading a directory."""
        with patch("pathlib.Path.is_file", return_value=False):
            result = read_file("/some/directory")
            assert "Error:" in result
            assert "not a regular file" in result

    @patch("builtins.open")
    def test_read_file_permission_error_with_mock(self, mock_open):
        """Test reading a file with permission errors using mock."""
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.stat", return_value=type("MockStatResult", (), {"st_size": 100})):
                with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                    result = read_file("protected_file.txt")
                    assert "Error:" in result
                    assert "Permission denied" in result


class TestEditFile:
    """Tests for the edit_file function."""

    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_success(self, mock_confirm, mock_get_config):
        """Test editing a file successfully."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value="line 1\nline 2\nline 3\n"):
                with patch("pathlib.Path.write_text") as mock_write:
                    result = apply_edit("test_file.txt", "line 1\nline 2\nline 3\nline 4\n")
                    assert "successfully" in result
                    mock_write.assert_called_once()

    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_create_new(self, mock_confirm, mock_get_config):
        """Test creating a new file with edit_file."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations for a new file
        with patch("pathlib.Path.is_file", return_value=False):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.parent") as mock_parent:
                    mock_parent.mkdir = MagicMock()
                    with patch("pathlib.Path.write_text") as mock_write:
                        result = apply_edit("new_file.txt", "New content")
                        assert "successfully" in result
                        mock_write.assert_called_once()

    @patch("code_agent.config.config.get_config")
    def test_edit_file_no_changes(self, mock_get_config):
        """Test editing a file with no changes."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        content = "unchanged content\n"

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value=content):
                result = apply_edit("unchanged_file.txt", content)
                assert "No changes" in result

    @patch("code_agent.config.config.get_config")
    @patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied"))
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_error(self, mock_confirm, mock_write, mock_get_config):
        """Test error handling in edit_file."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value="Original content"):
                result = apply_edit("file.txt", "New content")
                assert "Error" in result
                assert "Permission denied" in result


class TestIsPathWithinCwd:
    """Tests for the is_path_within_cwd function."""

    def test_path_within_cwd(self):
        """Test a path within the current directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/home/user")
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path("/home/user/file.txt")
                with patch("pathlib.Path.is_relative_to", return_value=True):
                    assert is_path_within_cwd("file.txt") is True

    def test_path_outside_cwd(self):
        """Test a path outside the current directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/home/user")
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path("/tmp/file.txt")
                with patch("pathlib.Path.is_relative_to", return_value=False):
                    assert is_path_within_cwd("/tmp/file.txt") is False

    def test_path_error(self):
        """Test when path resolution causes an error."""
        with patch("pathlib.Path.cwd"):
            with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
                assert is_path_within_cwd("invalid://path") is False
