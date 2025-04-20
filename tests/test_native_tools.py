from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from code_agent.config import SettingsConfig  # Changed Config -> SettingsConfig
from code_agent.tools.native_tools import RunNativeCommandArgs, run_native_command

# --- Mocks & Fixtures ---

@pytest.fixture
def mock_subprocess_run():
    """Mocks subprocess.run."""
    with patch("code_agent.tools.native_tools.subprocess.run") as mock_run:
        yield mock_run

@pytest.fixture
def mock_confirm():
    """Mocks rich.prompt.Confirm.ask."""
    with patch("code_agent.tools.native_tools.Confirm.ask") as mock_ask:
        yield mock_ask

@pytest.fixture
def mock_get_config():
    """Mocks config.get_config."""
    with patch("code_agent.tools.native_tools.get_config") as mock_get:
        # Default mock config unless overridden in test
        mock_config = SettingsConfig(
            auto_approve_native_commands=False,
            native_command_allowlist=[]
        )
        mock_get.return_value = mock_config
        yield mock_get

def configure_mock_config(
    mock_get_config_fixture: MagicMock, 
    auto_approve: bool = False, 
    allowlist: Optional[list] = None
):
    """Helper to configure the mocked config return value."""
    if allowlist is None:
        allowlist = []

    mock_config = SettingsConfig(
        auto_approve_native_commands=auto_approve,
        native_command_allowlist=allowlist
    )
    mock_get_config_fixture.return_value = mock_config
    return mock_config

def configure_mock_subprocess(
    mock_subprocess_fixture: MagicMock,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0
):
    """Helper to configure the mocked subprocess result."""
    mock_result = Mock()
    mock_result.stdout = stdout
    mock_result.stderr = stderr
    mock_result.returncode = returncode
    mock_subprocess_fixture.return_value = mock_result

# --- Test Cases ---

def test_run_command_confirmed(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test running a command successfully with user confirmation."""
    configure_mock_config(mock_get_config, auto_approve=False, allowlist=[])
    configure_mock_subprocess(mock_subprocess_run, stdout="Success!", returncode=0)
    mock_confirm.return_value = True # User confirms

    args = RunNativeCommandArgs(command="echo 'hello'")
    result = run_native_command(args)

    mock_confirm.assert_called_once()
    mock_subprocess_run.assert_called_once_with(
        ["echo", "hello"], capture_output=True, text=True, check=False
    )
    assert "Exit Code: 0" in result
    assert "--- stdout ---" in result
    assert "Success!" in result
    assert "--- stderr ---" not in result

def test_run_command_cancelled(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test cancelling a command via user confirmation."""
    configure_mock_config(mock_get_config, auto_approve=False, allowlist=[])
    mock_confirm.return_value = False # User cancels

    args = RunNativeCommandArgs(command="dangerous command")
    result = run_native_command(args)

    mock_confirm.assert_called_once()
    mock_subprocess_run.assert_not_called()
    assert "Command execution cancelled by user" in result

def test_run_command_auto_approved(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test running a command with auto-approval enabled."""
    configure_mock_config(mock_get_config, auto_approve=True, allowlist=[])
    configure_mock_subprocess(mock_subprocess_run, stdout="Auto approved output", returncode=0)

    args = RunNativeCommandArgs(command="do-something --fast")
    result = run_native_command(args)

    mock_confirm.assert_not_called() # Confirmation should be skipped
    mock_subprocess_run.assert_called_once_with(
        ["do-something", "--fast"], capture_output=True, text=True, check=False
    )
    assert "Auto approved output" in result

def test_run_command_allowlisted_exact_match(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test running an exactly allowlisted command."""
    configure_mock_config(mock_get_config, auto_approve=False, allowlist=["git"])
    configure_mock_subprocess(mock_subprocess_run, stdout="git output", returncode=0)
    mock_confirm.return_value = True

    args = RunNativeCommandArgs(command="git status -s")
    result = run_native_command(args)

    mock_confirm.assert_called_once()
    mock_subprocess_run.assert_called_once_with(
        ["git", "status", "-s"], capture_output=True, text=True, check=False
    )
    assert "git output" in result

def test_run_command_allowlisted_prefix_fail(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test that a command is blocked if only a prefix is allowlisted 
    (exact match required)."""
    configure_mock_config(mock_get_config, auto_approve=False, allowlist=["git"])

    args = RunNativeCommandArgs(command="git-lfs pull") # Base command 'git-lfs' is not 'git'
    result = run_native_command(args)

    mock_confirm.assert_not_called()
    mock_subprocess_run.assert_not_called()
    assert (
        "Error: Command 'git-lfs' is not in the configured allowlist" 
        in result
    )

def test_run_command_disallowed(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test attempting to run a command not on the allowlist."""
    configure_mock_config(mock_get_config, auto_approve=False, allowlist=["ls", "echo"])

    args = RunNativeCommandArgs(command="rm -rf /")
    result = run_native_command(args)

    mock_confirm.assert_not_called()
    mock_subprocess_run.assert_not_called()
    assert (
        "Error: Command 'rm' is not in the configured allowlist" 
        in result
    ) # Check base command

def test_run_command_disallowed_but_auto_approved(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test running a disallowed command when auto-approve is on 
    (should warn but run)."""
    configure_mock_config(mock_get_config, auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    args = RunNativeCommandArgs(command="dangerous --op")
    result = run_native_command(args)

    mock_confirm.assert_not_called()
    mock_subprocess_run.assert_called_once_with(
        ["dangerous", "--op"], capture_output=True, text=True, check=False
    )
    assert "output" in result
    # TODO: Check for the warning print message? Requires capsys.

def test_run_command_disallowed_but_auto_approved_warns(
    mock_subprocess_run: MagicMock,
    mock_confirm: MagicMock,
    mock_get_config: MagicMock,
    capsys
):
    """Test that a warning is printed when running a disallowed command 
    with auto-approve."""
    configure_mock_config(mock_get_config, auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    args = RunNativeCommandArgs(command="dangerous --op")
    result = run_native_command(args)

    mock_confirm.assert_not_called()
    mock_subprocess_run.assert_called_once()
    assert "output" in result

    captured = capsys.readouterr()
    assert "Warning:" in captured.out or "Warning:" in captured.err
    assert ("not in the allowlist" in captured.out or
            "not in the allowlist" in captured.err)
    assert ("dangerous" in captured.out or
            "dangerous" in captured.err) # Check command name

def test_run_command_shlex_error(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test handling of errors during shlex.split (e.g., bad quoting)."""
    configure_mock_config(mock_get_config, auto_approve=True) # Auto-approve to skip confirm

    # Command with an unclosed quote
    args = RunNativeCommandArgs(command="echo \"Hello world")
    result = run_native_command(args)

    mock_confirm.assert_not_called()
    mock_subprocess_run.assert_not_called()
    assert "Error parsing command string:" in result

def test_run_command_subprocess_error(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test handling of errors during subprocess execution."""
    configure_mock_config(mock_get_config, auto_approve=True) # Auto-approve to skip confirm
    mock_subprocess_run.side_effect = Exception("Subprocess failed!")

    args = RunNativeCommandArgs(command="error command")
    result = run_native_command(args)

    mock_subprocess_run.assert_called_once()
    assert (
        "Error executing command 'error command': Subprocess failed!" 
        in result
    )

def test_run_command_not_found(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test handling of FileNotFoundError when command doesn't exist."""
    configure_mock_config(mock_get_config, auto_approve=True)
    mock_subprocess_run.side_effect = FileNotFoundError("Command not found")

    args = RunNativeCommandArgs(command="invalid_command_name")
    result = run_native_command(args)

    mock_subprocess_run.assert_called_once()
    assert "Error: Command not found: invalid_command_name" in result

def test_run_command_capture_stderr(
    mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_get_config: MagicMock
):
    """Test that stderr is captured and returned."""
    configure_mock_config(mock_get_config, auto_approve=True)
    configure_mock_subprocess(
        mock_subprocess_run, stderr="Something went wrong", returncode=1
    )

    args = RunNativeCommandArgs(command="command_that_fails")
    result = run_native_command(args)

    mock_subprocess_run.assert_called_once()
    assert "Exit Code: 1" in result
    assert "--- stderr ---" in result
    assert "Something went wrong" in result
    assert "--- stdout ---" not in result
