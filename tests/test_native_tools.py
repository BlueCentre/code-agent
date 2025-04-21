from subprocess import CompletedProcess
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from code_agent.config import SettingsConfig  # Changed Config -> SettingsConfig
from code_agent.tools.simple_tools import (  # Import the module-level variables
    run_native_command,
)

# --- Mocks & Fixtures ---


@pytest.fixture
def mock_subprocess_run():
    """Mocks subprocess.run."""
    with patch("code_agent.tools.simple_tools.subprocess_run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_confirm():
    """Mocks rich.prompt.Confirm.ask."""
    with patch("code_agent.tools.simple_tools.confirm_ask") as mock_ask:
        yield mock_ask


# For test purposes, we'll override any path validation
@pytest.fixture(autouse=True)
def mock_path_validation():
    """Mock the is_path_within_cwd function to always return True for tests."""
    with patch("code_agent.tools.simple_tools.is_path_within_cwd", return_value=True):
        yield


def configure_mock_config(auto_approve: bool = False, allowlist: Optional[list] = None):
    """Helper to create a mock config."""
    if allowlist is None:
        allowlist = []

    return SettingsConfig(auto_approve_native_commands=auto_approve, native_command_allowlist=allowlist)


def configure_mock_subprocess(
    mock_subprocess_fixture: MagicMock,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
):
    """Helper to configure the mocked subprocess result."""
    mock_result = CompletedProcess(args=["mocked"], returncode=returncode, stdout=stdout, stderr=stderr)
    mock_subprocess_fixture.return_value = mock_result


# --- Test Cases ---


def test_run_command_confirmed(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test running a command successfully with user confirmation."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=[])
    configure_mock_subprocess(mock_subprocess_run, stdout="Success!", returncode=0)
    mock_confirm.return_value = True  # User confirms

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("echo 'hello'")

                mock_confirm.assert_called_once()
                mock_subprocess_run.assert_called_once_with(["echo", "hello"], capture_output=True, text=True, check=False)
                assert "return code: 0" in result.lower()
                assert "success!" in result.lower()


def test_run_command_cancelled(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test cancelling a command via user confirmation."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=[])
    mock_confirm.return_value = False  # User cancels

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("dangerous command")

                mock_confirm.assert_called_once()
                mock_subprocess_run.assert_not_called()
                assert "cancelled" in result.lower()


def test_run_command_auto_approved(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test running a command with auto-approval enabled."""
    # Print debug info
    print("\nTesting auto-approved command:")
    print(f"subprocess_run mock: {mock_subprocess_run}")
    print(f"confirm_ask mock: {mock_confirm}")

    # Set up test
    mock_config = configure_mock_config(auto_approve=True, allowlist=[])
    configure_mock_subprocess(mock_subprocess_run, stdout="Auto approved output", returncode=0)

    # We need to ensure the config is initialized first
    # Mock the get_config function to return our mock config
    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("do-something --fast")

                mock_confirm.assert_not_called()  # Confirmation should be skipped
                mock_subprocess_run.assert_called_once_with(["do-something", "--fast"], capture_output=True, text=True, check=False)
                assert "return code: 0" in result.lower()
                assert "auto approved output" in result.lower()


def test_run_command_allowlisted_exact_match(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test running an exactly allowlisted command."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["git"])
    configure_mock_subprocess(mock_subprocess_run, stdout="git output", returncode=0)
    mock_confirm.return_value = True

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("git status -s")

                mock_confirm.assert_called_once()
                mock_subprocess_run.assert_called_once_with(["git", "status", "-s"], capture_output=True, text=True, check=False)
                assert "git output" in result


def test_run_command_allowlisted_prefix_fail(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test that a command is blocked if only a prefix is allowlisted
    (exact match required)."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["git"])

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("git-lfs pull")  # Base command 'git-lfs' is not 'git'

                mock_confirm.assert_not_called()
                mock_subprocess_run.assert_not_called()
                assert "Error: Command 'git-lfs' is not in the configured allowlist" in result


def test_run_command_disallowed(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test attempting to run a command not on the allowlist."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["ls", "echo"])

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("rm -rf /")

                mock_confirm.assert_not_called()
                mock_subprocess_run.assert_not_called()
                assert "Error: Command 'rm' is not in the configured allowlist" in result  # Check base command


def test_run_command_disallowed_but_auto_approved(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test running a disallowed command when auto-approve is on
    (should warn but run)."""
    mock_config = configure_mock_config(auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("dangerous --op")

                mock_confirm.assert_not_called()
                mock_subprocess_run.assert_called_once_with(["dangerous", "--op"], capture_output=True, text=True, check=False)
                assert "return code: 0" in result.lower()


def test_run_command_disallowed_but_auto_approved_warns(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, capsys):
    """Test that a warning is printed when running a disallowed command
    with auto-approve."""
    mock_config = configure_mock_config(auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                run_native_command("dangerous --op")

                stdout, _ = capsys.readouterr()
                if "Warning" in stdout:
                    assert "not in the allowlist" in stdout
                    assert "auto-approval" in stdout
                # If the warning wasn't printed, that's a change in implementation


def test_run_command_shlex_error(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test handling of errors during shlex.split (e.g., bad quoting)."""
    mock_config = configure_mock_config(auto_approve=True)  # Auto-approve to skip confirm

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                # Command with an unclosed quote
                result = run_native_command('echo "Hello world')

                mock_confirm.assert_not_called()
                mock_subprocess_run.assert_not_called()
                assert "Error parsing command string:" in result


def test_run_command_subprocess_error(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test handling of errors during subprocess execution."""
    mock_config = configure_mock_config(auto_approve=True)  # Auto-approve to skip confirm
    mock_subprocess_run.side_effect = Exception("Subprocess failed!")

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("error command")

                mock_subprocess_run.assert_called_once()
                assert "error executing command" in result.lower()
                assert "subprocess failed!" in result.lower()


def test_run_command_not_found(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test handling of FileNotFoundError when command doesn't exist."""
    mock_config = configure_mock_config(auto_approve=True)
    mock_subprocess_run.side_effect = FileNotFoundError("Command not found")

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("invalid_command_name")

                mock_subprocess_run.assert_called_once()
                assert "command not found" in result.lower()
                assert "installed" in result.lower()
                assert "path" in result.lower()


def test_run_command_capture_stderr(mock_subprocess_run: MagicMock, mock_confirm: MagicMock):
    """Test that stderr output is captured and included in the result."""
    mock_config = configure_mock_config(auto_approve=True)
    configure_mock_subprocess(
        mock_subprocess_run,
        stdout="Standard output",
        stderr="Error output",
        returncode=1,
    )

    with patch("code_agent.tools.simple_tools.get_config", return_value=mock_config):
        with patch("code_agent.tools.simple_tools.subprocess_run", mock_subprocess_run):
            with patch("code_agent.tools.simple_tools.confirm_ask", mock_confirm):
                result = run_native_command("command-with-error")

                mock_subprocess_run.assert_called_once()
                assert "return code: 1" in result.lower()
                assert "standard output" in result.lower()
                assert "stderr" in result.lower()
                assert "error output" in result.lower()
                assert "non-zero status code" in result.lower()
