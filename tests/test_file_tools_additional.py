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

    def test_read_file_cwd_validation(self, tmp_path: Path, capsys):
        """Test the read_file command refuses to read files outside CWD."""
        with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Invalid path")):
            parent_dir = tmp_path.parent
            result = read_file(str(parent_dir / "sensitive_file.txt"))

            # Check result contains error message
            assert "Invalid path" in result

    def test_read_file_not_a_file(self):
        """Test path exists but is not a regular file."""
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = False

            result = read_file("directory/")
            assert "not a regular file" in result.lower()

    def test_read_file_not_found(self):
        """Test path doesn't exist."""
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = False

            result = read_file("non_existent.txt")
            assert "not a regular file" in result.lower()

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
            assert "error" in result.lower()
            assert "too large" in result.lower()

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
                assert "error" in result.lower()
                assert "permission" in result.lower()

    def test_read_file_generic_error(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.is_file") as mock_is_file,
            patch("pathlib.Path.read_text", side_effect=Exception("Generic error")),
        ):
            mock_is_within.return_value = True
            mock_is_file.return_value = True

            # Mock stat to return a reasonable file size
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat_result = MagicMock()
                mock_stat_result.st_size = 1024  # A small file
                mock_stat.return_value = mock_stat_result

                result = read_file("problematic_file.txt")
                assert "error" in result.lower()
                assert "generic error" in result.lower()


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

            result = delete_file("test_file.txt")
            mock_unlink.assert_called_once()
            assert "successfully" in result.lower()

    def test_delete_file_not_found(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = False

            result = delete_file("non_existent.txt")
            assert "does not exist" in result.lower()

    def test_delete_file_is_directory(self):
        with (
            patch("code_agent.tools.file_tools.is_path_within_cwd") as mock_is_within,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.is_file") as mock_is_file,
        ):
            mock_is_within.return_value = True
            mock_exists.return_value = True
            mock_is_file.return_value = False

            result = delete_file("directory/")
            assert "neither a file nor directory" in result.lower()

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
            assert "error" in result.lower()
            assert "permission" in result.lower()

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
            assert "error" in result.lower()
            assert "unexpected error" in result.lower()


class TestApplyEdit:
    """Tests for the apply_edit function."""

    def test_apply_edit_checks_target_file(self):
        """Test that apply_edit checks if the target file is safe."""
        with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Invalid path")):
            result = apply_edit("/etc/passwd", "test content")
            assert "Invalid path" in result

    @pytest.fixture
    def temp_edit_file(self, tmp_path):
        """Create a temporary file for editing tests."""
        file_path = tmp_path / "test_edit_file.txt"
        file_path.write_text("Original content")
        return file_path

    @pytest.fixture
    def auto_approve_config(self):
        """Create a config with auto-approve enabled."""
        config = MagicMock()
        config.auto_approve_edits = True
        return config

    def test_apply_edit_replaces_content(self, temp_edit_file):
        """Test that apply_edit replaces content in the file."""
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True), patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
            # Execute the test
            result = apply_edit(str(temp_edit_file), "New content")

            # Verify the file was updated
            assert "successfully" in result.lower()
            assert temp_edit_file.read_text() == "New content"

    def test_apply_edit_creates_file(self, tmp_path):
        """Test that apply_edit creates a new file if it doesn't exist."""
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True), patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
            # Create a path for a file that doesn't exist yet
            new_file_path = tmp_path / "new_test_file.txt"
            assert not new_file_path.exists()

            # Execute the test
            result = apply_edit(str(new_file_path), "File content")

            # Verify the file was created
            assert "successfully" in result.lower()
            assert new_file_path.exists()
            assert new_file_path.read_text() == "File content"
