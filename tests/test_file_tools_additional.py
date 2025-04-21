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
    delete_file,
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
    with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True):
        yield


class TestIsPathWithinCwd:
    def test_valid_path_within_cwd(self):
        """Test that a path within CWD is considered valid."""
        with (
            patch("pathlib.Path.cwd") as mock_cwd,
            patch("pathlib.Path.resolve") as mock_resolve,
            patch("pathlib.Path.is_relative_to") as mock_is_relative,
        ):
            mock_cwd.return_value = Path("/home/user")
            mock_resolve.return_value = Path("/home/user/test.txt")
            mock_is_relative.return_value = True

            result = is_path_within_cwd("test.txt")
            assert result is True

    def test_path_outside_cwd(self):
        """Test that a path outside CWD is considered invalid."""
        with (
            patch("pathlib.Path.cwd") as mock_cwd,
            patch("pathlib.Path.resolve") as mock_resolve,
            patch("pathlib.Path.is_relative_to") as mock_is_relative,
        ):
            mock_cwd.return_value = Path("/home/user")
            mock_resolve.return_value = Path("/etc/passwd")
            mock_is_relative.return_value = False

            result = is_path_within_cwd("/etc/passwd")
            assert result is False

    def test_path_resolution_error(self):
        """Test handling errors during path resolution."""
        with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
            result = is_path_within_cwd("invalid\\path")
            assert result is False


class TestReadFile:
    """Tests for the read_file function."""

    def test_read_file_outside_cwd(self):
        with patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within:
            mock_is_within.return_value = False

            result = read_file("/etc/passwd")
            assert "Error" in result
            assert "Path access restricted" in result

    def test_read_file_not_found(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = False

            result = read_file("nonexistent_file.txt")
            assert "Error" in result
            assert "not a regular file" in result

    def test_read_file_too_large(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = True

            # Mock stat result
            mock_stat_result = MagicMock()
            mock_stat_result.st_size = MAX_FILE_SIZE_BYTES + 1024  # Slightly over the limit
            mock_stat.return_value = mock_stat_result

            result = read_file("large_file.txt")
            assert "Error" in result
            assert "File is too large" in result

    def test_read_file_permission_error(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")),
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = True

            # Mock stat to return a reasonable file size so the size check passes
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat_result = MagicMock()
                mock_stat_result.st_size = 1024  # A small file
                mock_stat.return_value = mock_stat_result

                result = read_file("protected_file.txt")
                assert "Error" in result
                assert "Permission denied" in result


class TestDeleteFile:
    """Tests for the delete_file function."""

    def test_delete_file_success(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = True
            mock_is_file.return_value = True

            result = delete_file("file_to_delete.txt")
            assert "File deleted successfully" in result
            mock_unlink.assert_called_once()

    def test_delete_file_outside_cwd(self):
        with patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within:
            mock_is_within.return_value = False

            result = delete_file("/etc/passwd")
            assert "Error" in result
            assert "Path access restricted" in result

    def test_delete_file_nonexistent(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = False

            result = delete_file("nonexistent_file.txt")
            assert "Error" in result
            assert "does not exist" in result

    def test_delete_file_not_a_file(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.is_file") as mock_is_file,
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = True
            mock_is_file.return_value = False

            result = delete_file("directory/")
            assert "Error" in result
            assert "not a regular file" in result

    def test_delete_file_permission_error(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")),
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = True
            mock_is_file.return_value = True

            result = delete_file("protected_file.txt")
            assert "Error" in result
            assert "Permission denied" in result

    def test_delete_file_generic_error(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.unlink", side_effect=Exception("Unexpected error")),
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = True
            mock_is_file.return_value = True

            result = delete_file("problematic_file.txt")
            assert "Error" in result
            assert "Unexpected error" in result


class TestApplyEdit:
    """Tests for the apply_edit function."""

    def test_apply_edit_success(self):
        with (
            patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.read_text", return_value="Original content"),
            patch("pathlib.Path.write_text") as mock_write,
            patch("rich.prompt.Confirm.ask", return_value=True),
        ):
            mock_is_file.return_value = True

            # Mock config to not auto-approve
            with patch("code_agent.config.get_config") as mock_config:
                config = MagicMock()
                config.auto_approve_edits = False
                mock_config.return_value = config

                result = apply_edit("test.txt", "Updated content")
                assert "Edit applied successfully" in result
                mock_write.assert_called_once_with("Updated content")

    def test_apply_edit_create_new_file(self, tmp_path):
        """Test applying an edit to create a new file using a real temporary directory."""
        # Use a real temporary file to avoid mocking complexities
        new_file = tmp_path / "test_new_file.txt"

        with (
            patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
            patch("rich.prompt.Confirm.ask", return_value=True),
        ):
            # Mock config to not auto-approve
            with patch("code_agent.config.get_config") as mock_config:
                config = MagicMock()
                config.auto_approve_edits = False
                mock_config.return_value = config

                # Apply an edit to create the new file
                result = apply_edit(str(new_file), "New file content")

                # Verify the file was created with the right content
                assert new_file.exists()
                assert new_file.read_text() == "New file content"
                assert "Edit applied successfully" in result

    def test_apply_edit_no_changes(self):
        content = "Original content"
        with (
            patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.read_text", return_value=content),
            patch("pathlib.Path.write_text") as mock_write,
            patch("rich.prompt.Confirm.ask", return_value=True),
        ):
            mock_is_file.return_value = True

            # Mock config
            with patch("code_agent.config.get_config") as mock_config:
                config = MagicMock()
                config.auto_approve_edits = False
                mock_config.return_value = config

                result = apply_edit("test.txt", content)  # Same content
                assert "No changes detected" in result
                mock_write.assert_not_called()

    def test_apply_edit_permission_error(self):
        with (
            patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.read_text", return_value="Original content"),
            patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")),
            patch("rich.prompt.Confirm.ask", return_value=True),
        ):
            mock_is_file.return_value = True

            # Mock config
            with patch("code_agent.config.get_config") as mock_config:
                config = MagicMock()
                config.auto_approve_edits = False
                mock_config.return_value = config

                result = apply_edit("protected.txt", "New content")
                assert "Error writing changes to file" in result
                assert "Permission denied" in result

    def test_apply_edit_outside_cwd(self):
        with patch("code_agent.tools.file_tools._is_path_safe", return_value=False):
            result = apply_edit("/etc/passwd", "malicious content")
            assert "Error: Path access restricted" in result

    def test_apply_edit_generic_error(self):
        with (
            patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
            patch("pathlib.Path.resolve", side_effect=Exception("Unknown error")),
        ):
            result = apply_edit("test.txt", "content")
            assert "Error applying edit to" in result
            assert "Unknown error" in result
