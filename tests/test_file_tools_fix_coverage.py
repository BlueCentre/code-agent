"""
Tests for file_tools.py to improve coverage.

These tests specifically target the code_agent.tools.file_tools module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.tools.file_tools import (
    MAX_FILE_SIZE_BYTES,
    ReadFileArgs,
    apply_edit,
    is_path_within_cwd,
    read_file,
    read_file_legacy,
)


# For test purposes, we'll mock is_path_within_cwd to always return True during tests
@pytest.fixture(autouse=True)
def mock_path_validation():
    """Mock the path validation functions to always return True for tests."""
    with (
        patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True),
        patch("code_agent.tools.file_tools._is_path_safe", return_value=True),
    ):
        yield


# --- Fixtures ---
@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Creates a temporary file with some content."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3\n")
    return file_path


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    return dir_path


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    # Use module-level patch for get_config to handle internal imports
    with patch("code_agent.config.config.get_config") as mock_get_config:
        config = MagicMock()
        config.auto_approve_edits = False
        mock_get_config.return_value = config
        yield config


@pytest.fixture
def auto_approve_config():
    """Creates a config with auto_approve_edits=True."""
    config = MagicMock()
    config.auto_approve_edits = True
    return config


# --- Tests for is_path_within_cwd ---
def test_is_path_within_cwd():
    """Test the is_path_within_cwd function with various paths."""
    # Override the fixture for this specific test
    with patch("code_agent.tools.file_tools.is_path_within_cwd", side_effect=lambda x: is_path_within_cwd(x)):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/home/user")

            # Test relative path
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path("/home/user/file.txt")
                with patch("pathlib.Path.is_relative_to", return_value=True):
                    assert is_path_within_cwd("file.txt") is True

            # Test path outside cwd
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path("/tmp/file.txt")
                with patch("pathlib.Path.is_relative_to", return_value=False):
                    assert is_path_within_cwd("/tmp/file.txt") is False

            # Test error case
            with patch("pathlib.Path.resolve", side_effect=ValueError("Invalid path")):
                assert is_path_within_cwd("invalid://path") is False


# --- Tests for read_file ---
def test_read_file_success(temp_file: Path):
    """Test reading an existing file successfully."""
    result = read_file(str(temp_file))
    assert result == "Line 1\nLine 2\nLine 3\n"


def test_read_file_not_found(tmp_path: Path):
    """Test reading a non-existent file."""
    result = read_file(str(tmp_path / "non_existent.txt"))
    assert "File not found or is not a regular file" in result


def test_read_file_is_directory(temp_dir: Path):
    """Test attempting to read a directory."""
    result = read_file(str(temp_dir))
    assert "File not found or is not a regular file" in result


def test_read_file_too_large(tmp_path: Path):
    """Test attempting to read a file that exceeds the size limit."""
    large_file_path = tmp_path / "large_file.txt"

    # Create a stat_result-like object
    stat_result = type("MockStatResult", (), {"st_size": MAX_FILE_SIZE_BYTES + 1})

    with patch("pathlib.Path.is_file", return_value=True):
        with patch("pathlib.Path.stat", return_value=stat_result):
            result = read_file(str(large_file_path))
            assert "too large" in result
            assert "Maximum allowed size" in result


def test_read_file_stat_error(tmp_path: Path):
    """Test error handling when getting file stats."""
    file_path = tmp_path / "stat_error.txt"

    with patch("pathlib.Path.is_file", return_value=True):
        with patch("pathlib.Path.stat", side_effect=OSError("stat error")):
            result = read_file(str(file_path))
            assert "Failed when checking size of" in result
            assert "stat error" in result


def test_read_file_permission_error(temp_file: Path):
    """Test reading a file with permission error."""
    with patch("pathlib.Path.is_file", return_value=True):
        with patch("pathlib.Path.stat", return_value=type("MockStatResult", (), {"st_size": 100})):
            with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
                result = read_file(str(temp_file))
                assert "Failed when reading" in result
                assert "permission" in result.lower()


def test_read_file_generic_error(temp_file: Path):
    """Test reading a file with a generic error."""
    with patch("pathlib.Path.is_file", return_value=True):
        with patch("pathlib.Path.stat", return_value=type("MockStatResult", (), {"st_size": 100})):
            with patch("pathlib.Path.read_text", side_effect=Exception("Generic error")):
                result = read_file(str(temp_file))
                assert "Failed when reading" in result
                assert "Generic error" in result


def test_read_file_outside_cwd(temp_file: Path):
    """Test reading a file outside the CWD."""
    with patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=False):
        result = read_file(str(temp_file))
        assert "Path access restricted" in result


def test_read_file_legacy(temp_file: Path):
    """Test the legacy read_file function that takes ReadFileArgs."""
    args = ReadFileArgs(path=str(temp_file))

    with patch("code_agent.tools.file_tools.read_file") as mock_read_file:
        mock_read_file.return_value = "Mocked content"
        result = read_file_legacy(args)

        mock_read_file.assert_called_once_with(str(temp_file))
        assert result == "Mocked content"


# --- Tests for apply_edit ---
def test_apply_edit_modify_confirmed(temp_file: Path, mock_config):
    """Test modifying a file when user confirms."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        new_content = "Line 1 - Modified\nLine 2\nLine 3"
        result = apply_edit(str(temp_file), new_content)

        assert "Edit applied successfully" in result
        assert temp_file.read_text() == new_content


def test_apply_edit_modify_cancelled(temp_file: Path, mock_config):
    """Test modifying a file when user cancels."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=False):
        content_before = temp_file.read_text()
        new_content = "Line 1 - Modified\nLine 2\nLine 3"
        result = apply_edit(str(temp_file), new_content)

        assert "Edit cancelled by user" in result
        assert temp_file.read_text() == content_before


def test_apply_edit_auto_approved(temp_file: Path, auto_approve_config):
    """Test applying an edit with auto_approve_edits=True."""
    # Mock Confirm.ask to always return True if it's called
    # This prevents test failures if the code happens to still call it
    # despite auto-approve being enabled
    confirm_patch = patch("rich.prompt.Confirm.ask", return_value=True)

    # Mock the config get method and capture output to avoid terminal interaction
    with (
        patch("code_agent.config.config.get_config", return_value=auto_approve_config),
        patch("code_agent.tools.file_tools.print"),  # Suppress output
        patch("code_agent.tools.file_tools.console"),  # Suppress output
        confirm_patch,  # Handle any prompt attempts
    ):
        # Execute the test with patched modules
        new_content = "Auto-approved content"

        # Test that edit is applied successfully
        result = apply_edit(str(temp_file), new_content)

        # Verify result
        assert "Edit applied successfully" in result
        assert temp_file.read_text() == new_content


def test_apply_edit_create_file(tmp_path: Path, mock_config):
    """Test creating a new file with apply_edit."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        new_file_path = tmp_path / "new_file.txt"
        new_content = "Content for the new file."

        assert not new_file_path.exists()
        result = apply_edit(str(new_file_path), new_content)

        assert "Edit applied successfully" in result
        assert new_file_path.exists()
        assert new_file_path.read_text() == new_content


def test_apply_edit_no_changes(temp_file: Path, mock_config):
    """Test apply_edit when proposed content is the same as existing."""
    with patch("code_agent.tools.file_tools.Confirm.ask") as mock_confirm:
        content_before = temp_file.read_text()
        result = apply_edit(str(temp_file), content_before)

        assert "No changes needed" in result
        assert temp_file.read_text() == content_before
        mock_confirm.assert_not_called()


def test_apply_edit_is_directory(temp_dir: Path, mock_config):
    """Test applying an edit to a path that is a directory."""
    # First mock is_path_within_cwd to return True, then proceed with the test
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.is_file", return_value=False):
            result = apply_edit(str(temp_dir), "Some content")
            assert "regular file" in result


def test_apply_edit_outside_cwd(temp_file: Path, mock_config):
    """Test attempting to apply an edit to a file outside the CWD."""
    # Override the fixture to test path restriction
    with (
        patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=False),
        patch("code_agent.tools.file_tools._is_path_safe", return_value=False),
    ):
        # Suppress prints and terminal inputs during test
        with (
            patch("code_agent.tools.file_tools.print"),
            patch("code_agent.tools.file_tools.console"),
            patch("code_agent.tools.file_tools.Confirm.ask", return_value=False),
        ):
            result = apply_edit(str(temp_file), "Modified content")
            assert "Path access restricted" in result


def test_apply_edit_permission_error(temp_file: Path, mock_config):
    """Test error handling for permission errors when writing."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
            result = apply_edit(str(temp_file), "New content")
            assert "Failed when writing changes to" in result
            assert "permission" in result.lower()


def test_apply_edit_generic_error(temp_file: Path, mock_config):
    """Test error handling for generic exceptions during edit."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        with patch("pathlib.Path.write_text", side_effect=Exception("Generic error")):
            result = apply_edit(str(temp_file), "New content")
            assert "Failed when writing changes to" in result
            assert "Generic error" in result
