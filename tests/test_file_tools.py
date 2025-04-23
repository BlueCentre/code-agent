import sys  # For checking platform for permission tests
from pathlib import Path
from unittest.mock import patch

import pytest

from code_agent.config import (  # Changed Config -> SettingsConfig
    SettingsConfig,
)
from code_agent.tools.file_tools import (
    apply_edit,
    read_file,
)


# For test purposes, we'll mock is_path_safe to always return (True, None) during tests
# This will allow our tests to work with temp directories from pytest
@pytest.fixture(autouse=True)
def mock_path_validation():
    """Mock the is_path_safe function to always return True for tests."""
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        yield


# --- Fixtures ---


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary file with test content."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3")
    return file_path


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    return dir_path


# --- Tests for read_file ---


def test_read_file_success(temp_file: Path):
    """Test that a valid file can be read successfully."""
    result = read_file(str(temp_file))
    assert result == "Line 1\nLine 2\nLine 3"


def test_read_file_not_found():
    """Test reading a non-existent file."""
    result = read_file("non_existent_file.txt")
    assert "not found" in result.lower()


def test_read_file_is_directory(temp_dir: Path):
    """Test attempting to read a directory."""
    result = read_file(str(temp_dir))
    assert "not a regular file" in result.lower()


def test_read_file_too_large(tmp_path: Path):
    """Test attempting to read a file that exceeds the size limit."""
    large_file_path = tmp_path / "large_file.txt"
    # Create content slightly larger than the limit (assuming limit is 1MB)
    # Use a known size to avoid relying on the exact constant from the module
    limit = 1 * 1024 * 1024
    try:
        with open(large_file_path, "wb") as f:
            f.seek(limit)  # Seek to 1MB + 1 byte
            f.write(b"\0")  # Write a single byte
    except OSError as e:
        pytest.skip(f"Skipping large file test, failed to create file: {e}")

    result = read_file(str(large_file_path))

    assert "too large" in result.lower()
    assert "maximum allowed size" in result.lower()


def test_read_file_empty(tmp_path: Path):
    """Test reading an empty file."""
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    result = read_file(str(empty_file))
    assert result == ""


@pytest.mark.skipif(sys.platform == "win32", reason="Permission tests behave differently on Windows")
def test_read_file_permission_error(temp_file: Path, monkeypatch):
    """Test handling permission error during read."""
    # Mock Path.read_text to raise PermissionError
    with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
        result = read_file(str(temp_file))
        assert "permission" in result.lower()
        assert "access" in result.lower()


# Note: Testing actual non-UTF8 read depends heavily on locale/OS.
# Mocking read_text raising UnicodeDecodeError is an alternative.
# def test_read_file_decode_error(tmp_path: Path):
#     decode_error_file = tmp_path / "decode_error.bin"
#     # Invalid start byte for UTF-8
#     decode_error_file.write_bytes(b'\x80abc')
#     result = read_file(str(decode_error_file))
#     # Check for generic error or specific decode error
#     assert "Error reading file" in result


def test_read_file_outside_cwd(temp_file: Path, monkeypatch):
    """Test attempting to read a file outside the CWD."""
    # Since we're mocking is_path_safe to always return True,
    # We need to mock it specifically for this test to return False
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Path not within current directory")):
        # Mock CWD to be the parent of the temp file's directory
        original_cwd = Path.cwd()
        mock_cwd = temp_file.parent.parent
        monkeypatch.chdir(mock_cwd)

        # Construct a path that resolves outside the mocked CWD
        # (temp_file is in tmp_path/..., cwd is tmp_path)
        relative_path_to_file = temp_file.relative_to(mock_cwd)

        result = read_file(str(relative_path_to_file))
        assert "Error:" in result
        assert "restricted for security reasons" in result

        # Restore CWD
        monkeypatch.chdir(original_cwd)


def test_read_file_pagination(tmp_path: Path):
    """Test the read_file pagination functionality."""
    # Create a test file with multiple lines
    test_file_path = tmp_path / "paginated_file.txt"
    test_content = "\n".join([f"This is line {i + 1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Test reading with pagination enabled, but no offset or limit
    result_no_params = read_file(path=str(test_file_path), enable_pagination=True)

    # Check that the full content is returned with pagination info
    assert "This is line 1" in result_no_params
    assert "This is line 100" in result_no_params
    assert "Pagination Info" in result_no_params
    assert "Total Lines: 100" in result_no_params

    # Test reading with offset
    result_with_offset = read_file(path=str(test_file_path), offset=50, enable_pagination=True)

    # Check that only content from line 51 onwards is returned
    assert "This is line 50" not in result_with_offset  # The line before offset should not be present
    assert "This is line 51" in result_with_offset  # The first line at offset should be present
    assert "Current Range: Lines 51-" in result_with_offset

    # Test reading with limit
    result_with_limit = read_file(path=str(test_file_path), limit=10, enable_pagination=True)

    # Check that only 10 lines are returned
    assert "This is line 1" in result_with_limit
    assert "This is line 10" in result_with_limit
    assert "This is line 11" not in result_with_limit
    assert "Current Range: Lines 1-10" in result_with_limit
    assert "More content available: Yes" in result_with_limit

    # Test reading with both offset and limit
    result_with_both = read_file(path=str(test_file_path), offset=20, limit=5, enable_pagination=True)

    # Check that the specified range is returned
    assert "This is line 20" not in result_with_both
    assert "This is line 21" in result_with_both
    assert "This is line 25" in result_with_both
    assert "This is line 26" not in result_with_both
    assert "Current Range: Lines 21-25" in result_with_both


def test_read_file_pagination_disabled(tmp_path: Path):
    """Test that pagination is disabled by default."""
    # Create a test file with multiple lines
    test_file_path = tmp_path / "normal_file.txt"
    test_content = "\n".join([f"This is line {i + 1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Read file without enabling pagination
    result = read_file(path=str(test_file_path))

    # The file should be read normally without pagination info
    assert "This is line 1" in result
    assert "This is line 100" in result
    assert "Pagination Info" not in result


def test_read_file_invalid_pagination_params(tmp_path: Path):
    """Test validation of pagination parameters."""
    test_file_path = tmp_path / "test_file.txt"
    test_file_path.write_text("Test content")

    # Test with negative offset
    result_negative_offset = read_file(path=str(test_file_path), offset=-1, enable_pagination=True)
    assert "Error: Failed when validating parameters" in result_negative_offset
    assert "Offset must be a non-negative integer" in result_negative_offset

    # Test with zero limit
    result_zero_limit = read_file(path=str(test_file_path), limit=0, enable_pagination=True)
    assert "Error: Failed when validating parameters" in result_zero_limit
    assert "Limit must be a positive integer" in result_zero_limit


# --- Tests for apply_edit ---


def test_apply_edit_modify_confirmed(temp_file: Path):
    """Test applying an edit with user confirmation."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock confirmation to return True (user confirms)
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
            new_content = "Line 1\nLine 2 Modified\nLine 3"
            result = apply_edit(str(temp_file), new_content)

            assert "successfully updated" in result


def test_apply_edit_modify_cancelled(temp_file: Path):
    """Test cancelling an edit."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock confirmation to return False (user cancels)
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=False):
            new_content = "Line 1\nLine 2 Modified\nLine 3"
            result = apply_edit(str(temp_file), new_content)

            assert "cancelled" in result


def test_apply_edit_auto_approved(temp_file: Path):
    """Test applying an edit with auto_approve_edits=True."""
    # Setup mock config (auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=True)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Confirmation should NOT be called with auto-approve=True
        with patch("code_agent.tools.file_tools.Confirm.ask"):
            with patch("code_agent.tools.file_tools.print"):  # Suppress output prints
                new_content = "Auto-approved content"
                result = apply_edit(str(temp_file), new_content)

                assert "successfully updated" in result


def test_apply_edit_create_file(tmp_path: Path):
    """Test creating a new file."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock confirmation to return True (user confirms)
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
            new_file_path = tmp_path / "new_file.txt"
            new_content = "New file content"
            result = apply_edit(str(new_file_path), new_content)

            assert "successfully created" in result


def test_apply_edit_no_changes(temp_file: Path):
    """Test apply_edit when proposed content is the same as existing."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Confirmation should NOT be called if no changes detected
        with patch("code_agent.tools.file_tools.Confirm.ask") as mock_ask:
            # Read content once to use for args and assertion
            content_before = temp_file.read_text()
            result = apply_edit(str(temp_file), content_before)

            assert "No changes needed" in result
            assert "already matches" in result
            assert temp_file.read_text() == content_before
            mock_ask.assert_not_called()


def test_apply_edit_is_directory(temp_dir: Path):
    """Test applying an edit to a path that is a directory."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        result = apply_edit(str(temp_dir), "Content for a directory")
        assert "not a regular file" in result.lower()


def test_apply_edit_outside_cwd(temp_file: Path):
    """Test editing a file outside of the current working directory."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock the path validation to return False
        with patch("code_agent.tools.file_tools.is_path_safe", return_value=(False, "Path not within current directory")):
            result = apply_edit("/etc/passwd", "Dangerous content")
            assert "restricted for security reasons" in result.lower()


def test_apply_edit_write_permission_error(temp_file: Path):
    """Test handling permission error during write."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock confirmation to return True (user confirms)
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
            # Mock write_text to raise PermissionError
            with patch.object(Path, "write_text", side_effect=PermissionError("Cannot write")):
                result = apply_edit(str(temp_file), "New content")

                assert "Failed when writing to" in result


def test_apply_edit_generic_error(temp_file: Path):
    """Test handling unknown errors during apply_edit."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)

    # Use the correct import path for get_config and patch it
    with patch("code_agent.config.config.get_config", return_value=mock_config):
        # Mock confirmation to return True (user confirms)
        with patch("code_agent.tools.file_tools.Confirm.ask", return_value=True):
            # Mock write_text to raise an unexpected exception
            with patch.object(Path, "write_text", side_effect=Exception("Unexpected error")):
                result = apply_edit(str(temp_file), "New content")

                assert "Failed when writing to" in result
