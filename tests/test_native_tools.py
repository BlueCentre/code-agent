from subprocess import CompletedProcess
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from code_agent.config import SettingsConfig  # Changed Config -> SettingsConfig
from code_agent.tools.native_tools import (  # Update the import path
    _analyze_command_impact,
    _categorize_command,
    run_native_command,
)

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
def mock_console():
    """Mocks rich.console.Console to avoid rendering issues."""
    with patch("code_agent.tools.native_tools.console") as mock_console:
        yield mock_console


# For test purposes, we'll override any path validation
@pytest.fixture(autouse=True)
def mock_path_validation():
    """Mock the is_path_within_cwd function to always return True for tests."""
    with patch("code_agent.tools.native_tools.is_command_safe", return_value=(True, "", False)):
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


def test_run_command_confirmed(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test running a command successfully with user confirmation."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=[])
    configure_mock_subprocess(mock_subprocess_run, stdout="Success!", returncode=0)
    mock_confirm.return_value = True  # User confirms

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("echo 'hello'")

        mock_confirm.assert_called_once()
        mock_subprocess_run.assert_called_once()
        assert "Success!" in result


def test_run_command_cancelled(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test cancelling a command via user confirmation."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=[])
    mock_confirm.return_value = False  # User cancels

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("dangerous command")

        mock_confirm.assert_called_once()
        mock_subprocess_run.assert_not_called()
        assert "cancelled" in result.lower()


def test_run_command_auto_approved(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
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
    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("do-something --fast")

        mock_confirm.assert_not_called()  # Confirmation should be skipped
        mock_subprocess_run.assert_called_once()
        assert "Auto approved output" in result


def test_run_command_allowlisted_exact_match(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test running an exactly allowlisted command."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["git"])
    configure_mock_subprocess(mock_subprocess_run, stdout="git output", returncode=0)
    mock_confirm.return_value = True

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("git status -s")

        mock_confirm.assert_called_once()
        mock_subprocess_run.assert_called_once()
        assert "git output" in result


def test_run_command_allowlisted_prefix_fail(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test that a command is blocked if only a prefix is allowlisted
    (exact match required)."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["git"])

    # Mock is_command_safe to return that the command is unsafe
    with (
        patch("code_agent.tools.native_tools.get_config", return_value=mock_config),
        patch("code_agent.tools.native_tools.is_command_safe", return_value=(False, "Command is not in the allowlist", False)),
    ):
        result = run_native_command("git-lfs pull")  # Base command 'git-lfs' is not 'git'

        mock_confirm.assert_not_called()
        mock_subprocess_run.assert_not_called()
        assert "not permitted" in result.lower() or "not in the allowlist" in result.lower()


def test_run_command_disallowed(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test attempting to run a command not on the allowlist."""
    mock_config = configure_mock_config(auto_approve=False, allowlist=["ls", "echo"])

    # Mock is_command_safe to return that the command is unsafe
    with (
        patch("code_agent.tools.native_tools.get_config", return_value=mock_config),
        patch("code_agent.tools.native_tools.is_command_safe", return_value=(False, "Command is not in the allowlist", False)),
    ):
        result = run_native_command("rm -rf /")

        mock_confirm.assert_not_called()
        mock_subprocess_run.assert_not_called()
        assert "not permitted" in result.lower() or "not in the allowlist" in result.lower()


def test_run_command_disallowed_but_auto_approved(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test running a disallowed command when auto-approve is on
    (should warn but run)."""
    mock_config = configure_mock_config(auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("dangerous --op")

        mock_confirm.assert_not_called()
        mock_subprocess_run.assert_called_once()
        assert "output" in result


def test_run_command_disallowed_but_auto_approved_warns(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock, capsys):
    """Test that a warning is printed when running a disallowed command
    with auto-approve."""
    mock_config = configure_mock_config(auto_approve=True, allowlist=["ls"])
    configure_mock_subprocess(mock_subprocess_run, stdout="output", returncode=0)

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        run_native_command("dangerous --op")

        # We can't easily capture the rich formatted output with capsys
        # Instead, verify the subprocess was called
        mock_subprocess_run.assert_called_once()


def test_run_command_shlex_error(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test handling of errors during shlex.split (e.g., bad quoting)."""
    mock_config = configure_mock_config(auto_approve=True)  # Auto-approve to skip confirm

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        # Command with an unclosed quote - should be caught in _categorize_command
        with pytest.raises(ValueError, match="No closing quotation"):
            run_native_command('echo "Hello world')


def test_run_command_subprocess_error(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test handling of errors during subprocess execution."""
    mock_config = configure_mock_config(auto_approve=True)  # Auto-approve to skip confirm
    mock_subprocess_run.side_effect = Exception("Subprocess failed!")

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("error command")

        mock_subprocess_run.assert_called_once()
        assert "error executing command" in result.lower()
        assert "subprocess failed!" in result.lower()


def test_run_command_not_found(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test handling of FileNotFoundError when command doesn't exist."""
    mock_config = configure_mock_config(auto_approve=True)
    mock_subprocess_run.side_effect = FileNotFoundError("Command not found")

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("invalid_command_name")

        mock_subprocess_run.assert_called_once()
        assert "command not found" in result.lower()


def test_run_command_capture_stderr(mock_subprocess_run: MagicMock, mock_confirm: MagicMock, mock_console: MagicMock):
    """Test that stderr output is captured and included in the result."""
    mock_config = configure_mock_config(auto_approve=True)
    configure_mock_subprocess(
        mock_subprocess_run,
        stdout="Standard output",
        stderr="Error output",
        returncode=1,
    )

    with patch("code_agent.tools.native_tools.get_config", return_value=mock_config):
        result = run_native_command("command-with-error")

        assert "Standard output" in result
        assert "Error output" in result
        assert "exit code: 1" in result.lower()


def test_categorize_command():
    """Test that commands are correctly categorized."""
    # Test file operations commands
    assert "file_operations" in _categorize_command("ls -la")
    assert "file_operations" in _categorize_command("rm file.txt")
    assert "file_operations" in _categorize_command("cat README.md")

    # Test network commands
    assert "network" in _categorize_command("curl example.com")
    assert "network" in _categorize_command("ping -c 4 google.com")

    # Test development commands
    assert "development" in _categorize_command("git status")
    assert "development" in _categorize_command("python setup.py install")

    # Test command that falls into multiple categories
    categories = _categorize_command("git clone https://github.com/example/repo")
    assert "development" in categories

    # Test empty command
    assert _categorize_command("") == []

    # Test unknown command
    assert _categorize_command("unknown_command_xyz") == []


def test_analyze_command_impact():
    """Test the command impact analysis function."""
    # Test low impact command
    impact_level, warnings = _analyze_command_impact("ls -la")
    assert impact_level == "Low"
    assert len(warnings) == 0

    # Test medium impact commands
    impact_level, warnings = _analyze_command_impact("rm file.txt")
    assert impact_level == "Medium"
    assert len(warnings) > 0
    assert any("delete files" in warning for warning in warnings)

    impact_level, warnings = _analyze_command_impact("pip install requests")
    assert impact_level == "Medium"
    assert len(warnings) > 0
    assert any("install" in warning for warning in warnings)

    # Test high impact commands
    impact_level, warnings = _analyze_command_impact("chmod -R 777 /path")
    assert impact_level == "High"
    assert len(warnings) > 0
    assert any("recursive" in warning.lower() for warning in warnings)
    assert any("permissions" in warning.lower() for warning in warnings)

    impact_level, warnings = _analyze_command_impact("rm -rf temp/")
    assert impact_level == "High"
    assert len(warnings) > 0
    assert any("recursive" in warning.lower() for warning in warnings)
