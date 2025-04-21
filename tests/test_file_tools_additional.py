"""
Tests for the file_tools module to improve coverage.

These tests focus on edge cases and error handling in the file_tools module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.file_tools import (
    MAX_FILE_SIZE_BYTES,
    codebase_search,
    edit_file,
    file_search,
    is_path_within_cwd,
    read_file,
    write_file,
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
    with patch("code_agent.config.get_config") as mock_get_config:
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config
        yield config


class TestReadFile:
    """Tests for the read_file function."""

    def test_read_file_path_outside_cwd(self):
        """Test that read_file rejects paths outside current working directory."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=False):
            result = read_file("/some/absolute/path")
            assert "Error: Path access restricted" in result

    def test_read_file_not_a_file(self):
        """Test read_file with a path that exists but is not a file."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=False):
                result = read_file("some_directory")
                assert "Error: File not found or is not a regular file" in result

    def test_read_file_too_large(self):
        """Test read_file with a file that exceeds the size limit."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                # Create a stat_result-like object
                stat_result = type("MockStatResult", (), {"st_size": MAX_FILE_SIZE_BYTES + 1})
                with patch("pathlib.Path.stat", return_value=stat_result):
                    result = read_file("large_file.txt")
                    assert "Error: File is too large" in result

    def test_read_file_stat_error(self):
        """Test read_file when an error occurs getting file statistics."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.stat", side_effect=OSError("stat error")):
                    result = read_file("problem_file.txt")
                    assert "Error getting file size" in result

    def test_read_file_not_found(self):
        """Test read_file with a nonexistent file."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                # Create a stat_result-like object
                stat_result = type("MockStatResult", (), {"st_size": 100})
                with patch("pathlib.Path.stat", return_value=stat_result):
                    with patch("pathlib.Path.read_text", side_effect=FileNotFoundError("Not found")):
                        result = read_file("nonexistent.txt")
                        assert "Error: File not found" in result

    def test_read_file_permission_error(self):
        """Test read_file with a file that causes a permission error."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                # Create a stat_result-like object
                stat_result = type("MockStatResult", (), {"st_size": 100})
                with patch("pathlib.Path.stat", return_value=stat_result):
                    with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                        result = read_file("protected.txt")
                        assert "Error: Permission denied" in result

    def test_read_file_generic_error(self):
        """Test read_file with a file that causes a generic error."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                # Create a stat_result-like object
                stat_result = type("MockStatResult", (), {"st_size": 100})
                with patch("pathlib.Path.stat", return_value=stat_result):
                    with patch("pathlib.Path.read_text", side_effect=Exception("Generic error")):
                        result = read_file("error.txt")
                        assert "Error reading file" in result

    def test_read_file_success(self):
        """Test reading a file successfully."""
        # Create a temporary file with some content
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("line 1\nline 2\nline 3\nline 4\nline 5\n")
            file_path = temp_file.name

        try:
            # Read the entire file
            result = read_file(file_path)
            assert "line 1" in result
            assert "line 5" in result

            # Read with offset and limit
            result = read_file(file_path, offset=1, limit=2)
            assert "line 2" in result
            assert "line 3" in result
            assert "line 1" not in result
            assert "line 4" not in result
        finally:
            # Clean up
            os.unlink(file_path)

    def test_read_file_nonexistent(self):
        """Test reading a nonexistent file."""
        result = read_file("/nonexistent/file.txt")
        assert "Error:" in result
        assert "No such file or directory" in result

    def test_read_file_directory(self):
        """Test reading a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = read_file(temp_dir)
            assert "Error:" in result
            assert "Is a directory" in result

    @patch("builtins.open")
    def test_read_file_permission_error_with_mock(self, mock_open):
        """Test reading a file with permission errors using mock."""
        mock_open.side_effect = PermissionError("Permission denied")

        result = read_file("protected_file.txt")
        assert "Error:" in result
        assert "Permission denied" in result


class TestWriteFile:
    """Tests for the write_file function."""

    def test_write_file_success(self):
        """Test writing to a file successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test_file.txt")
            content = "Test content\nLine 2"

            result = write_file(file_path, content)

            assert "successfully saved" in result
            assert os.path.exists(file_path)

            with open(file_path, "r") as f:
                saved_content = f.read()
                assert saved_content == content

    def test_write_file_create_directories(self):
        """Test writing to a file in nonexistent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "subdir1", "subdir2", "test_file.txt")
            content = "Test content"

            result = write_file(file_path, content)

            assert "successfully saved" in result
            assert os.path.exists(file_path)

    @patch("builtins.open")
    @patch("os.makedirs")
    def test_write_file_permission_error(self, mock_makedirs, mock_open):
        """Test writing to a file with permission errors."""
        mock_open.side_effect = PermissionError("Permission denied")

        result = write_file("/protected/file.txt", "Content")

        assert "Error:" in result
        assert "Permission denied" in result


class TestEditFile:
    """Tests for the edit_file function."""

    def test_edit_file_success(self):
        """Test editing a file successfully."""
        # Create a temporary file with some content
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("line 1\nline 2\nline 3\n")
            file_path = temp_file.name

        try:
            # Edit the file
            result = edit_file(file_path, "line 1\nline 2\nline 3\nline 4\n")

            assert "successfully updated" in result

            # Verify the content
            with open(file_path, "r") as f:
                content = f.read()
                assert content == "line 1\nline 2\nline 3\nline 4\n"
        finally:
            # Clean up
            os.unlink(file_path)

    def test_edit_file_create_new(self):
        """Test creating a new file with edit_file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "new_file.txt")

            result = edit_file(file_path, "New content")

            assert "successfully created" in result
            assert os.path.exists(file_path)

            with open(file_path, "r") as f:
                content = f.read()
                assert content == "New content"

    def test_edit_file_no_changes(self):
        """Test editing a file with no changes."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            content = "unchanged content\n"
            temp_file.write(content)
            file_path = temp_file.name

        try:
            # Edit with the same content
            result = edit_file(file_path, content)

            assert "No changes made" in result
        finally:
            # Clean up
            os.unlink(file_path)

    @patch("builtins.open")
    def test_edit_file_error(self, mock_open):
        """Test error handling in edit_file."""
        mock_open.side_effect = PermissionError("Permission denied")

        result = edit_file("file.txt", "New content")

        assert "Error:" in result
        assert "Permission denied" in result


class TestFileSearch:
    """Tests for the file_search function."""

    @patch("code_agent.tools.file_tools.Path")
    def test_file_search_success(self, mock_path):
        """Test file search with results."""
        # Setup mock to return search results
        mock_return = MagicMock()
        mock_return.glob.return_value = [Path("file1.py"), Path("dir/file2.py"), Path("dir/subdir/file3.py")]
        mock_path.return_value = mock_return

        result = file_search("*.py")

        assert "file1.py" in result
        assert "dir/file2.py" in result
        assert "dir/subdir/file3.py" in result

    @patch("code_agent.tools.file_tools.Path")
    def test_file_search_no_results(self, mock_path):
        """Test file search with no results."""
        # Setup mock to return no results
        mock_return = MagicMock()
        mock_return.glob.return_value = []
        mock_path.return_value = mock_return

        result = file_search("nonexistent*.txt")

        assert "No files found" in result

    @patch("code_agent.tools.file_tools.Path")
    def test_file_search_error(self, mock_path):
        """Test error handling in file search."""
        # Setup mock to raise an exception
        mock_path.side_effect = Exception("Search error")

        result = file_search("*.py")

        assert "Error:" in result
        assert "Search error" in result


class TestCodebaseSearch:
    """Tests for the codebase_search function."""

    @patch("code_agent.tools.file_tools.subprocess.run")
    def test_codebase_search_success(self, mock_run):
        """Test codebase search with results."""
        # Setup mock to return search results
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "file1.py:10:def search_function():\n" "file2.py:20:    result = search_function()"
        mock_run.return_value = mock_process

        result = codebase_search("search_function")

        assert "file1.py:10:" in result
        assert "file2.py:20:" in result
        assert "def search_function()" in result
        assert "result = search_function()" in result

    @patch("code_agent.tools.file_tools.subprocess.run")
    def test_codebase_search_no_results(self, mock_run):
        """Test codebase search with no results."""
        # Setup mock to return no results
        mock_process = MagicMock()
        mock_process.returncode = 1  # Non-zero return code indicates no matches
        mock_process.stdout = ""
        mock_run.return_value = mock_process

        result = codebase_search("nonexistent_function")

        assert "No matches found" in result

    @patch("code_agent.tools.file_tools.subprocess.run")
    def test_codebase_search_error(self, mock_run):
        """Test error handling in codebase search."""
        # Setup mock to raise an exception
        mock_run.side_effect = Exception("Search error")

        result = codebase_search("function")

        assert "Error:" in result
        assert "Search error" in result

    @patch("code_agent.tools.file_tools.subprocess.run")
    def test_codebase_search_with_target_directories(self, mock_run):
        """Test codebase search with target directories."""
        # Setup mock to return search results
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "src/file.py:10:def function():"
        mock_run.return_value = mock_process

        result = codebase_search("function", target_directories=["src", "lib"])

        assert "src/file.py:10:" in result
        # Verify that the command includes the target directories
        call_args = mock_run.call_args[0][0]
        assert " src lib " in " ".join(call_args)


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
