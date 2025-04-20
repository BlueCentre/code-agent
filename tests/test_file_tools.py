import sys  # For checking platform for permission tests
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_agent.config import (  # Changed Config -> SettingsConfig
    SettingsConfig,
)
from code_agent.tools.file_tools import (
    ApplyEditArgs,
    ReadFileArgs,
    apply_edit,
    read_file,
)

# --- Fixtures ---

@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Creates a temporary file with some content."""
    file_path = tmp_path / "test_file.txt"
    content = "Line 1\nLine 2\nLine 3"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    return dir_path

# --- Tests for read_file ---

def test_read_file_success(temp_file: Path):
    """Test reading an existing file successfully."""
    args = ReadFileArgs(path=str(temp_file))
    result = read_file(args)
    assert result == "Line 1\nLine 2\nLine 3"

def test_read_file_not_found(tmp_path: Path):
    """Test reading a non-existent file."""
    args = ReadFileArgs(path=str(tmp_path / "non_existent.txt"))
    result = read_file(args)
    assert "Error: File not found" in result

def test_read_file_is_directory(temp_dir: Path):
    """Test attempting to read a directory."""
    args = ReadFileArgs(path=str(temp_dir))
    result = read_file(args)
    assert "Error: File not found or is not a regular file" in result

def test_read_file_too_large(tmp_path: Path):
    """Test attempting to read a file that exceeds the size limit."""
    large_file_path = tmp_path / "large_file.txt"
    # Create content slightly larger than the limit (assuming limit is 1MB)
    # Use a known size to avoid relying on the exact constant from the module
    limit = 1 * 1024 * 1024
    try:
        with open(large_file_path, "wb") as f:
            f.seek(limit) # Seek to 1MB + 1 byte
            f.write(b"\0") # Write a single byte
    except OSError as e:
        pytest.skip(f"Skipping large file test, failed to create file: {e}")

    args = ReadFileArgs(path=str(large_file_path))
    result = read_file(args)

    assert "Error: File is too large" in result
    assert "Maximum allowed size" in result

def test_read_file_empty(tmp_path: Path):
    """Test reading an empty file."""
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    args = ReadFileArgs(path=str(empty_file))
    result = read_file(args)
    assert result == ""

@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Permission tests behave differently on Windows"
)
def test_read_file_permission_error(temp_file: Path, monkeypatch):
    """Test handling permission error during read."""
    # Mock Path.read_text to raise PermissionError
    with patch.object(
        Path, "read_text", side_effect=PermissionError("Permission denied")
    ):
        args = ReadFileArgs(path=str(temp_file))
        result = read_file(args)
        assert "Error: Permission denied" in result

# Note: Testing actual non-UTF8 read depends heavily on locale/OS.
# Mocking read_text raising UnicodeDecodeError is an alternative.
# def test_read_file_decode_error(tmp_path: Path):
#     decode_error_file = tmp_path / "decode_error.bin"
#     # Invalid start byte for UTF-8
#     decode_error_file.write_bytes(b'\x80abc')
#     args = ReadFileArgs(path=str(decode_error_file))
#     result = read_file(args)
#     # Check for generic error or specific decode error
#     assert "Error reading file" in result

def test_read_file_outside_cwd(temp_file: Path, monkeypatch):
    """Test attempting to read a file outside the CWD."""
    # Mock CWD to be the parent of the temp file's directory
    original_cwd = Path.cwd()
    mock_cwd = temp_file.parent.parent
    monkeypatch.chdir(mock_cwd)

    # Construct a path that resolves outside the mocked CWD
    # (temp_file is in tmp_path/..., cwd is tmp_path)
    relative_path_to_file = temp_file.relative_to(mock_cwd)

    args = ReadFileArgs(path=str(relative_path_to_file))
    result = read_file(args)
    assert "Error: Path access restricted" in result

    # Restore CWD
    monkeypatch.chdir(original_cwd)

# --- Tests for apply_edit ---

@patch("code_agent.tools.file_tools.Confirm.ask", return_value=True)
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_modify_confirmed(
    mock_get_config: MagicMock, mock_confirm: MagicMock, temp_file: Path
):
    """Test modifying a file when user confirms."""
    # Setup mock config (no auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    new_content = "Line 1 - Modified\nLine 2\nLine 3"
    args = ApplyEditArgs(
        path=str(temp_file),
        proposed_content=new_content
    )

    result = apply_edit(args)

    assert "Edit applied successfully" in result
    assert temp_file.read_text() == new_content
    mock_confirm.assert_called_once()

@patch("code_agent.tools.file_tools.Confirm.ask", return_value=False)
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_modify_cancelled(
    mock_get_config: MagicMock, mock_confirm: MagicMock, temp_file: Path
):
    """Test modifying a file when user cancels."""
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    # Store content *before* the action for the assertion
    content_before = temp_file.read_text()

    new_content = "Line 1 - Modified\nLine 2\nLine 3"
    args = ApplyEditArgs(
        path=str(temp_file),
        proposed_content=new_content
    )

    result = apply_edit(args)

    assert "Edit cancelled by user" in result
    # Content should not change from what it was before the call
    assert temp_file.read_text() == content_before
    mock_confirm.assert_called_once()

@patch("code_agent.tools.file_tools.Confirm.ask")
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_auto_approved(
    mock_get_config: MagicMock, mock_confirm: MagicMock, temp_file: Path
):
    """Test applying an edit with auto_approve_edits=True."""
    # Setup mock config (auto-approve)
    mock_config = SettingsConfig(auto_approve_edits=True)
    mock_get_config.return_value = mock_config

    new_content = "Auto-approved content"
    args = ApplyEditArgs(
        path=str(temp_file),
        proposed_content=new_content
    )

    result = apply_edit(args)

    assert "Edit applied successfully" in result
    assert temp_file.read_text() == new_content
    mock_confirm.assert_not_called() # Confirmation should be skipped

@patch("code_agent.tools.file_tools.Confirm.ask", return_value=True)
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_create_file(
    mock_get_config: MagicMock, mock_confirm: MagicMock, tmp_path: Path
):
    """Test creating a new file with apply_edit."""
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    new_file_path = tmp_path / "new_file.txt"
    new_content = "Content for the new file."
    args = ApplyEditArgs(
        path=str(new_file_path),
        proposed_content=new_content
    )

    assert not new_file_path.exists()
    result = apply_edit(args)

    assert "Edit applied successfully" in result
    assert new_file_path.exists()
    assert new_file_path.read_text() == new_content
    mock_confirm.assert_called_once()

@patch("code_agent.tools.file_tools.Confirm.ask")
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_no_changes(
    mock_get_config: MagicMock, mock_confirm: MagicMock, temp_file: Path
):
    """Test apply_edit when proposed content is the same as existing."""
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    # Read content once to use for args and assertion
    content_before = temp_file.read_text()
    args = ApplyEditArgs(
        path=str(temp_file),
        proposed_content=content_before
    )

    result = apply_edit(args)

    assert "No changes detected" in result
    assert temp_file.read_text() == content_before # Check content hasn't changed
    mock_confirm.assert_not_called() # No confirmation needed if no diff

@patch("code_agent.tools.file_tools.Confirm.ask")
@patch("code_agent.tools.file_tools.get_config")
def test_apply_edit_is_directory(
    mock_get_config: MagicMock, mock_confirm: MagicMock, temp_dir: Path
):
    """Test applying an edit to a path that is a directory."""
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    args = ApplyEditArgs(
        path=str(temp_dir),
        proposed_content="some content"
    )
    result = apply_edit(args)

    assert "Error: Path exists but is not a regular file" in result
    mock_confirm.assert_not_called()

def test_apply_edit_outside_cwd(temp_file: Path, monkeypatch):
    """Test attempting to edit a file outside the CWD."""
    original_cwd = Path.cwd()
    mock_cwd = temp_file.parent.parent
    monkeypatch.chdir(mock_cwd)

    relative_path_to_file = temp_file.relative_to(mock_cwd)
    args = ApplyEditArgs(
        path=str(relative_path_to_file),
        proposed_content="New Content"
    )

    result = apply_edit(args)
    assert "Error: Path access restricted" in result

    monkeypatch.chdir(original_cwd)

@patch("code_agent.tools.file_tools.Confirm.ask", return_value=True)
@patch("code_agent.tools.file_tools.get_config")
@patch.object(Path, "write_text", side_effect=PermissionError("Cannot write"))
def test_apply_edit_write_permission_error(
    mock_write_text: MagicMock,
    mock_get_config: MagicMock,
    mock_confirm: MagicMock,
    temp_file: Path
):
    """Test handling permission error during write in apply_edit."""
    mock_config = SettingsConfig(auto_approve_edits=False)
    mock_get_config.return_value = mock_config

    new_content = "Content that won\'t be written"
    args = ApplyEditArgs(
        path=str(temp_file),
        proposed_content=new_content
    )

    result = apply_edit(args)

    assert "Error writing changes to file" in result
    assert "Cannot write" in result
    mock_confirm.assert_called_once()
    mock_write_text.assert_called_once() # Ensure write was attempted
