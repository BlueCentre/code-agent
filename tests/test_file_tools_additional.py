"""
Tests for the file_tools module to improve coverage.

These tests focus on edge cases and error handling in the file_tools module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.file_tools import (
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
    with patch("code_agent.tools.file_tools.get_config") as mock_get_config:
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
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat_result = MagicMock()
                    mock_stat_result.st_size = MAX_FILE_SIZE_BYTES + 1
                    mock_stat.return_value = mock_stat_result

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
                with patch("pathlib.Path.stat"):
                    with patch("pathlib.Path.read_text", side_effect=FileNotFoundError("Not found")):
                        result = read_file("nonexistent.txt")
                        assert "Error: File not found" in result

    def test_read_file_permission_error(self):
        """Test read_file with a file that causes a permission error."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.stat"):
                    with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                        result = read_file("protected.txt")
                        assert "Error: Permission denied" in result

    def test_read_file_generic_error(self):
        """Test read_file with a file that causes a generic error."""
        with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.stat"):
                    with patch("pathlib.Path.read_text", side_effect=Exception("Generic error")):
                        result = read_file("error.txt")
                        assert "Error reading file" in result


class TestApplyEdit:
    """Tests for the apply_edit function."""

    def test_apply_edit_path_outside_cwd(self):
        """Test that apply_edit rejects paths outside current working directory."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=False):
            result = apply_edit("/some/absolute/path", "content")
            assert "Error: Path access restricted" in result

    def test_apply_edit_not_a_file(self, mock_config):
        """Test apply_edit with a path that exists but is not a file."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=False):
                    result = apply_edit("some_directory", "content")
                    assert "Error: Path exists but is not a regular file" in result

    def test_apply_edit_no_changes(self, mock_config):
        """Test apply_edit when the proposed content is the same as the current content."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="content"):
                    result = apply_edit("file.txt", "content")
                    assert "No changes detected" in result

    def test_apply_edit_user_confirms(self, mock_config):
        """Test apply_edit when the user confirms the changes."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="old content"):
                    with patch("rich.prompt.Confirm.ask", return_value=True):
                        with patch("pathlib.Path.write_text") as mock_write:
                            result = apply_edit("file.txt", "new content")
                            assert "Edit applied successfully" in result
                            mock_write.assert_called_once_with("new content")

    def test_apply_edit_user_declines(self, mock_config):
        """Test apply_edit when the user declines the changes."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="old content"):
                    with patch("rich.prompt.Confirm.ask", return_value=False):
                        result = apply_edit("file.txt", "new content")
                        assert "Edit cancelled by user" in result

    def test_apply_edit_auto_approve(self, mock_config):
        """Test apply_edit with auto-approve enabled."""
        mock_config.auto_approve_edits = True
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="old content"):
                    with patch("pathlib.Path.write_text"):
                        result = apply_edit("file.txt", "new content")
                        assert "Edit applied successfully" in result

    def test_apply_edit_new_file(self, mock_config):
        """Test apply_edit creating a new file."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=False):
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("rich.prompt.Confirm.ask", return_value=True):
                        with patch("pathlib.Path.write_text"):
                            with patch("pathlib.Path.parent.mkdir") as mock_mkdir:
                                result = apply_edit("new_file.txt", "content")
                                assert "Edit applied successfully" in result
                                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_apply_edit_write_error(self, mock_config):
        """Test apply_edit when writing the file fails."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("pathlib.Path.read_text", return_value="old content"):
                    with patch("rich.prompt.Confirm.ask", return_value=True):
                        with patch("pathlib.Path.write_text", side_effect=OSError("Write error")):
                            with patch("pathlib.Path.parent.mkdir"):
                                result = apply_edit("file.txt", "new content")
                                assert "Error writing changes to file" in result

    def test_apply_edit_permission_error(self, mock_config):
        """Test apply_edit when a permission error occurs."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.resolve", side_effect=PermissionError("Permission denied")):
                result = apply_edit("protected.txt", "content")
                assert "Error: Permission denied" in result

    def test_apply_edit_generic_error(self, mock_config):
        """Test apply_edit when a generic error occurs."""
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=True):
            with patch("pathlib.Path.resolve", side_effect=Exception("Generic error")):
                result = apply_edit("error.txt", "content")
                assert "Error applying edit to error.txt" in result


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
