"""
Tests for the file_tools module to improve coverage.

These tests focus on edge cases and error handling in the file_tools module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.file_tools import (
    read_file,
    apply_edit,
    is_path_within_cwd,
    MAX_FILE_SIZE_BYTES,
    delete_file,
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
    with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
        yield


class TestReadFile:
    """Tests for the read_file function."""

    def test_read_file_path_outside_cwd(self):
        """Test that read_file rejects paths outside current working directory."""
        # Override the fixture for this specific test
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=False):
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


class TestDeleteFile:
    """Tests for the delete_file function."""

    def test_delete_file_success(self):
        """Test deleting a file successfully."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.unlink") as mock_unlink:
                    result = delete_file("existing_file.txt")
                    assert "successfully" in result
                    mock_unlink.assert_called_once()

    def test_delete_file_nonexistent(self):
        """Test deleting a nonexistent file."""
        with patch("pathlib.Path.exists", return_value=False):
            result = delete_file("nonexistent_file.txt")
            assert "Error:" in result
            assert "does not exist" in result

    def test_delete_file_not_a_file(self):
        """Test deleting a path that is not a file."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=False):
                result = delete_file("directory/")
                assert "Error:" in result
                assert "not a regular file" in result

    def test_delete_file_permission_error(self):
        """Test deleting a file with permission error."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
                    result = delete_file("protected_file.txt")
                    assert "Error:" in result
                    assert "Permission denied" in result

    def test_delete_file_generic_error(self):
        """Test deleting a file with a generic error."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.unlink", side_effect=OSError("OS Error")):
                    result = delete_file("error_file.txt")
                    assert "Error:" in result
                    assert "OS Error" in result

    def test_delete_file_path_outside_cwd(self):
        """Test that delete_file rejects paths outside current working directory."""
        # Override the fixture for this specific test
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=False):
            result = delete_file("/some/absolute/path")
            assert "Error: Path access restricted" in result


class TestApplyEdit:
    """Tests for the apply_edit function."""

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
                    result = apply_edit("test_file.txt", "line 1\nline 2 modified\nline 3\n")
                    assert "successfully" in result
                    mock_write.assert_called_once()

    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_create_new(self, mock_confirm, mock_get_config):
        """Test creating a new file."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=False):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.write_text") as mock_write:
                    with patch("pathlib.Path.parent.mkdir") as mock_mkdir:
                        result = apply_edit("new_file.txt", "new content")
                        assert "successfully" in result
                        mock_write.assert_called_once()
                        mock_mkdir.assert_called_once()

    @patch("code_agent.config.config.get_config")
    def test_edit_file_no_changes(self, mock_get_config):
        """Test with no changes to the file."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value="line 1\nline 2\nline 3\n"):
                result = apply_edit("test_file.txt", "line 1\nline 2\nline 3\n")
                assert "No changes detected" in result

    @patch("code_agent.config.config.get_config")
    @patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied"))
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_permission_error(self, mock_confirm, mock_write, mock_get_config):
        """Test editing a file with permission error."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value="line 1\nline 2\nline 3\n"):
                result = apply_edit("protected_file.txt", "line 1\nline 2 modified\nline 3\n")
                assert "Error:" in result
                assert "Permission denied" in result

    @patch("code_agent.config.config.get_config")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_parent_dir_creation_error(self, mock_confirm, mock_get_config):
        """Test creating a new file with parent directory creation error."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=False):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.parent.mkdir", side_effect=PermissionError("Permission denied")):
                    result = apply_edit("new/subfolder/file.txt", "new content")
                    assert "Error:" in result
                    assert "Permission denied" in result

    @patch("code_agent.config.config.get_config")
    @patch("pathlib.Path.write_text", side_effect=Exception("Generic error"))
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_edit_file_generic_error(self, mock_confirm, mock_write, mock_get_config):
        """Test editing a file with a generic error."""
        # Setup the mock config
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config

        # Mock file operations
        with patch("pathlib.Path.is_file", return_value=True):
            with patch("pathlib.Path.read_text", return_value="line 1\nline 2\nline 3\n"):
                result = apply_edit("error_file.txt", "line 1\nline 2 modified\nline 3\n")
                assert "Error:" in result
                assert "Generic error" in result

    def test_edit_file_path_outside_cwd(self):
        """Test that edit_file rejects paths outside current working directory."""
        # Override the fixture for this specific test
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=False):
            result = apply_edit("/some/absolute/path", "new content")
            assert "Error: Path access restricted" in result


class TestIsPathWithinCwd:
    """Tests for the is_path_within_cwd function."""

    def test_path_within_cwd(self):
        """Test path within current working directory."""
        with patch("pathlib.Path.cwd", return_value=Path("/current/working/dir")):
            with patch("pathlib.Path.resolve", return_value=Path("/current/working/dir/subdir/file.txt")):
                result = is_path_within_cwd("subdir/file.txt")
                assert result is True

    def test_path_outside_cwd(self):
        """Test path outside current working directory."""
        with patch("pathlib.Path.cwd", return_value=Path("/current/working/dir")):
            with patch("pathlib.Path.resolve", return_value=Path("/different/dir/file.txt")):
                result = is_path_within_cwd("/different/dir/file.txt")
                assert result is False

    def test_path_error(self):
        """Test path resolution error."""
        with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
            result = is_path_within_cwd("invalid/path")
            assert result is False
