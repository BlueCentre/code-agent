from unittest.mock import patch

import pytest

# Import necessary config classes
from code_agent.config.config import CodeAgentSettings
from code_agent.config.settings_based_config import ApiKeys, FileOperationsSettings, SecuritySettings  # Import FileOperationsSettings

# Assuming simple_tools still exists and contains these functions
# If not, these imports will need adjustment based on the actual location
from code_agent.tools.simple_tools import (
    apply_edit,
    read_file,
)

# Remove old FileSettings import if it exists
# from code_agent.schemas import FileSettings # Keep commented out or remove

# --- Fixtures ---


@pytest.fixture
def mock_config_base():
    """Provides a base mocked CodeAgentSettings object."""
    return CodeAgentSettings(
        default_provider="mock_provider",
        default_model="mock_model",
        api_keys=ApiKeys(),
        security=SecuritySettings(  # Add security settings used by functions
            path_validation=True,
            workspace_restriction=True,
            command_validation=True,  # Keep even if run_native_command isn't here
        ),
        # Use FileOperationsSettings
        file_operations=FileOperationsSettings(),
        auto_approve_native_commands=False,
        native_command_allowlist=[],
        auto_approve_edit=False,  # Corrected: Changed edits -> edit
    )


@pytest.fixture
def auto_approve_config(mock_config_base):
    """Mock config with auto-approve edits enabled."""
    mock_config_base.auto_approve_edits = True
    return mock_config_base


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("This is a test file\nwith multiple lines\nfor testing")
    return file_path


@pytest.fixture
def large_temp_file(tmp_path):
    """Create a temporary file larger than the configured max size."""
    file_path = tmp_path / "large_test_file.txt"

    # Hardcode the default max size to avoid linter confusion
    # Default in FileOperationsSettings.ReadFileSettings is 1024 KB
    max_kb = 1024
    max_bytes = max_kb * 1024

    # Generate content larger than the max file size
    content = "x" * (max_bytes + 1000)
    file_path.write_text(content)
    return file_path


# --- Tests for read_file ---


# Patch the internal security check used in simple_tools
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
# Patch get_config as it's likely used internally by read_file
@patch("code_agent.tools.simple_tools.get_config")
def test_read_file_path_restricted(mock_get_config, mock_is_path_within_cwd, mock_config_base):
    """Test read_file returns an error when path is restricted."""
    mock_is_path_within_cwd.return_value = False  # Path is not within CWD
    mock_get_config.return_value = mock_config_base

    result = read_file("/restricted/path.txt")

    assert "restricted for security reasons" in result
    mock_is_path_within_cwd.assert_called_once_with("/restricted/path.txt")


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
def test_read_file_success(mock_get_config, mock_is_path_within_cwd, mock_config_base, temp_file):
    """Test read_file successfully reads a file."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base

    result = read_file(str(temp_file))

    assert "This is a test file" in result
    assert "with multiple lines" in result
    assert "for testing" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
def test_read_file_not_found(mock_get_config, mock_is_path_within_cwd, mock_config_base):
    """Test read_file returns an error when file is not found."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base

    result = read_file("nonexistent_file.txt")

    assert "Error: File not found or is not a regular file" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
def test_read_file_not_a_file(mock_get_config, mock_is_path_within_cwd, mock_config_base, tmp_path):
    """Test read_file returns an error when path is a directory."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base

    result = read_file(str(tmp_path))

    assert "Error: File not found or is not a regular file" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
def test_read_file_too_large(mock_get_config, mock_is_path_within_cwd, mock_config_base, large_temp_file):
    """Test read_file returns an error when file is too large."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base

    result = read_file(str(large_temp_file))

    assert "Error: File" in result
    assert "too large" in result
    assert "Maximum allowed size" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
@patch("pathlib.Path.stat")
def test_read_file_stat_error(mock_stat, mock_get_config, mock_is_path_within_cwd, mock_config_base, temp_file):
    """Test read_file handles stat errors gracefully."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base
    mock_stat.side_effect = OSError("Stat error")

    result = read_file(str(temp_file))

    assert "Error: Failed when reading" in result
    assert "Stat error" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
@patch("pathlib.Path.read_text")
def test_read_file_permission_error(mock_read_text, mock_get_config, mock_is_path_within_cwd, mock_config_base, temp_file):
    """Test read_file handles permission errors gracefully."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base
    mock_read_text.side_effect = PermissionError("Permission denied")

    result = read_file(str(temp_file))

    assert "Error: Failed when reading" in result
    assert "You don't have permission to access" in result


@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("code_agent.tools.simple_tools.get_config")
@patch("pathlib.Path.read_text")
def test_read_file_generic_error(mock_read_text, mock_get_config, mock_is_path_within_cwd, mock_config_base, temp_file):
    """Test read_file handles generic errors gracefully."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base
    mock_read_text.side_effect = Exception("Generic error")

    result = read_file(str(temp_file))

    assert "Error: Failed when reading" in result
    assert "Generic error" in result


# --- Tests for apply_edit ---


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
def test_apply_edit_path_restricted(mock_is_path_within_cwd, mock_get_config, mock_config_base):
    """Test apply_edit returns an error when path is restricted."""
    mock_is_path_within_cwd.return_value = False  # Path is not within CWD
    mock_get_config.return_value = mock_config_base

    result = apply_edit("/restricted/path.txt", "New content")

    assert "outside the allowed workspace" in result
    mock_is_path_within_cwd.assert_called_once_with("/restricted/path.txt")


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
def test_apply_edit_path_exists_but_not_file(mock_is_path_within_cwd, mock_get_config, mock_config_base, tmp_path):
    """Test apply_edit returns an error when path exists but is not a file."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base

    result = apply_edit(str(tmp_path), "New content")

    assert "Error: Path exists but is not a regular file" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("rich.prompt.Confirm.ask")
def test_apply_edit_success_new_file(mock_confirm_ask, mock_is_path_within_cwd, mock_get_config, mock_config_base, tmp_path, mocker):
    """Test apply_edit successfully creates a new file."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    # Ensure auto-approve is OFF for this test
    mock_config_base.auto_approve_edits = False
    mock_get_config.return_value = mock_config_base
    mock_confirm_ask.return_value = True  # Simulate user confirmation

    new_file_path = tmp_path / "new_file.txt"
    content = "This is a new file"

    # Mock Path methods for the new file scenario
    mock_is_file = mocker.patch("pathlib.Path.is_file", return_value=False)
    mock_exists = mocker.patch("pathlib.Path.exists", return_value=False)
    mock_write_text = mocker.patch("pathlib.Path.write_text")
    # Mock mkdir on the parent directory
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")

    result = apply_edit(str(new_file_path), content)

    # Assertions
    mock_is_path_within_cwd.assert_called_once_with(str(new_file_path))
    # is_file and exists should be called on the target path
    # Check call args if specific path instance is needed, but call_count might suffice
    assert mock_is_file.call_count >= 1
    assert mock_exists.call_count >= 1  # Should be called after is_file is false
    mock_confirm_ask.assert_called_once()
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    # Check write_text was called once with the correct content argument
    # The mock captures (self, content) args, assert_called_once_with checks non-self args
    mock_write_text.assert_called_once_with(content)

    assert "successfully" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("rich.prompt.Confirm.ask")
def test_apply_edit_success_existing_file(mock_confirm_ask, mock_is_path_within_cwd, mock_get_config, mock_config_base, temp_file):
    """Test apply_edit successfully edits an existing file."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base
    mock_confirm_ask.return_value = True

    original_content = temp_file.read_text()
    new_content = "This is the edited content."

    result = apply_edit(str(temp_file), new_content)

    assert "successfully" in result
    assert temp_file.read_text() == new_content
    assert temp_file.read_text() != original_content  # Ensure content changed
    mock_confirm_ask.assert_called_once()


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("rich.prompt.Confirm.ask")
def test_apply_edit_cancelled(mock_confirm_ask, mock_is_path_within_cwd, mock_get_config, mock_config_base, temp_file):
    """Test apply_edit handles user cancellation."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    # Ensure auto-approve is OFF for this test
    mock_config_base.auto_approve_edits = False
    mock_get_config.return_value = mock_config_base
    mock_confirm_ask.return_value = False  # Simulate user cancelling

    original_content = temp_file.read_text()
    new_content = "This content should not be written."

    result = apply_edit(str(temp_file), new_content)

    assert "cancelled" in result
    assert temp_file.read_text() == original_content  # Ensure file unchanged
    mock_confirm_ask.assert_called_once()


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
def test_apply_edit_auto_approve(mock_is_path_within_cwd, mock_get_config, temp_file, auto_approve_config):
    """Test apply_edit auto-approves when configured."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = auto_approve_config

    new_content = "This is auto-approved content."

    result = apply_edit(str(temp_file), new_content)

    assert "successfully" in result
    assert temp_file.read_text() == new_content


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("rich.prompt.Confirm.ask")
@patch("pathlib.Path.write_text")
def test_apply_edit_write_error(mock_write_text, mock_confirm_ask, mock_is_path_within_cwd, mock_get_config, mock_config_base, temp_file):
    """Test apply_edit handles write errors."""
    mock_is_path_within_cwd.return_value = True  # Path is within CWD
    mock_get_config.return_value = mock_config_base
    mock_confirm_ask.return_value = True  # Simulate user confirmation
    mock_write_text.side_effect = PermissionError("Write permission denied")

    result = apply_edit(str(temp_file), "New content")

    assert "Error" in result
    assert "Failed when writing changes to" in result
    assert "Write permission denied" in result
    mock_confirm_ask.assert_called_once()


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.is_path_within_cwd")
@patch("rich.prompt.Confirm.ask")
@patch("pathlib.Path.read_text")
def test_apply_edit_read_error(mock_read_text, mock_confirm_ask, mock_is_path_within_cwd, mock_get_config, mock_config_base, temp_file):
    """Test apply_edit handles read errors during initial read."""
    mock_is_path_within_cwd.return_value = True
    mock_get_config.return_value = mock_config_base
    # Mock read_text to fail on the FIRST call within apply_edit
    # mock_read_text.side_effect = [temp_file.read_text(), PermissionError("Read permission denied")] # REMOVE side_effect list
    mock_read_text.side_effect = PermissionError("Read permission denied")  # Raise error directly

    result = apply_edit(str(temp_file), "New content")

    assert "Error" in result
    assert "Failed reading original content from" in result
    assert "Read permission denied" in result
    mock_confirm_ask.assert_not_called()  # Confirmation should not be asked
    mock_read_text.assert_called_once()  # Ensure read_text was attempted


# Note: PermissionError/GenericError during write are covered by test_apply_edit_write_error
# Specific tests for those during write might be redundant if write_text is mocked.

# Remove tests for is_path_within_cwd and run_native_command as they are tested elsewhere
