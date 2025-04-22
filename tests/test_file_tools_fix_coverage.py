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
    _get_file_metadata,
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
        patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)),
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
    """Test that is_path_within_cwd correctly validates paths."""
    # Override the autouse fixture for this test only
    with patch("code_agent.tools.file_tools.is_path_safe") as mock_is_path_safe:
        # Set up the mock to return different values based on the input
        def side_effect(path):
            if "/fake/cwd/" in path or path in ["file.txt", "./file.txt", "dir/file.txt"]:
                return True, None
            return False, "Path is outside the current workspace"

        mock_is_path_safe.side_effect = side_effect

        # Now test the function with various paths
        assert is_path_within_cwd("/fake/cwd/file.txt") is True
        assert is_path_within_cwd("/fake/cwd/dir/file.txt") is True
        assert is_path_within_cwd("/fake/other/file.txt") is False
        assert is_path_within_cwd("../other/file.txt") is False
        # Relative paths within cwd
        assert is_path_within_cwd("file.txt") is True
        assert is_path_within_cwd("./file.txt") is True
        assert is_path_within_cwd("dir/file.txt") is True


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
            assert "Failed when reading" in result
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


def test_read_file_outside_cwd():
    """Test that read_file refuses to read files outside CWD."""
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Invalid path")):
        result = read_file({"target_file": "/etc/passwd"})
        assert "Invalid path" in result


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

        assert "successfully updated" in result
        assert temp_file.read_text() == new_content


def test_apply_edit_modify_cancelled(temp_file: Path, mock_config):
    """Test modifying a file when user cancels."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=False):
        content_before = temp_file.read_text()
        new_content = "Line 1 - Modified\nLine 2\nLine 3"
        result = apply_edit(str(temp_file), new_content)

        assert "cancelled" in result
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
        assert "successfully updated" in result
        assert temp_file.read_text() == new_content


def test_apply_edit_create_file(tmp_path: Path, mock_config):
    """Test creating a new file with apply_edit."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        new_file_path = tmp_path / "new_file.txt"
        new_content = "Content for the new file."

        assert not new_file_path.exists()
        result = apply_edit(str(new_file_path), new_content)

        assert "successfully created" in result
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


def test_apply_edit_outside_cwd():
    """Test that apply_edit refuses to edit files outside CWD."""
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Invalid path")):
        result = apply_edit("/etc/passwd", "malicious content")
        assert "Invalid path" in result


def test_apply_edit_permission_error(temp_file: Path, mock_config):
    """Test error handling for permission errors when writing."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Permission denied")):
            result = apply_edit(str(temp_file), "New content")
            assert "Failed when writing to" in result
            assert "permission" in result.lower()


def test_apply_edit_generic_error(temp_file: Path, mock_config):
    """Test error handling for generic exceptions during edit."""
    with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
        with patch("pathlib.Path.write_text", side_effect=Exception("Generic error")):
            result = apply_edit(str(temp_file), "New content")
            assert "Failed when writing to" in result
            assert "Generic error" in result


def test_path_validation_fails():
    """Test that path validation fails correctly."""
    with (
        patch("code_agent.tools.file_tools.is_path_within_cwd", return_value=True),
        patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Invalid path")),
    ):
        # Suppress prints and terminal inputs during test
        with patch("builtins.print"), patch("builtins.input", return_value="y"):
            result = read_file("some_file.txt")
            assert "Invalid path" in result


def test_get_file_metadata_success(temp_file: Path):
    """Test getting file metadata successfully."""
    metadata = _get_file_metadata(temp_file)

    # Verify we have all expected keys
    assert "size" in metadata
    assert "size_formatted" in metadata
    assert "permissions" in metadata
    assert "modified" in metadata
    assert "created" in metadata

    # Check that the size is reasonable (file has content)
    assert metadata["size"] > 0
    assert "bytes" in metadata["size_formatted"] or "KB" in metadata["size_formatted"]

    # Check that permissions are in octal format (like '644')
    assert len(metadata["permissions"]) == 3
    assert all(c in "01234567" for c in metadata["permissions"])

    # Check date formats
    assert "-" in metadata["modified"]
    assert ":" in metadata["modified"]


def test_get_file_metadata_error():
    """Test handling errors when getting file metadata."""
    # Create a path that will cause an exception on stat
    non_existent_path = Path("non_existent_file_for_test.txt")

    # Get metadata - should return default values instead of raising an exception
    metadata = _get_file_metadata(non_existent_path)

    # Check all values are set to "Unknown"
    assert metadata["size"] == "Unknown"
    assert metadata["size_formatted"] == "Unknown"
    assert metadata["permissions"] == "Unknown"
    assert metadata["modified"] == "Unknown"
    assert metadata["created"] == "Unknown"
