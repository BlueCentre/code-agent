"""Unit tests for native command execution tools and safety checks."""

import asyncio  # Make sure asyncio is imported if not already
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.prompt import Confirm

# Import config singletons/helpers for patching
import code_agent.config.config
import code_agent.config.settings_based_config

# Import native_tools directly for patching its contents
import code_agent.tools.native_tools

# Import necessary components from the codebase
from code_agent.config import CodeAgentSettings  # Use the final settings class
from code_agent.config.settings_based_config import NativeCommandSettings, SecuritySettings
from code_agent.tools.native_tools import (
    is_command_safe,
    run_native_command,
)

# --- Fixtures ---


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Ensures the config singleton is reset before each test."""
    code_agent.config.config._config = None
    yield
    code_agent.config.config._config = None


@pytest.fixture
def mock_settings(monkeypatch):
    """Provides a base mock CodeAgentSettings object for tests."""
    mock_sec = SecuritySettings(command_validation=True, path_validation=True, workspace_restriction=True, enable_web_search=True)
    mock_native = NativeCommandSettings(default_timeout=None, default_working_directory=None)
    mock_config = CodeAgentSettings(
        default_provider="mock",
        default_model="mock",
        security=mock_sec,
        native_commands=mock_native,
        auto_approve_native_commands=False,
        native_command_allowlist=[],
        verbosity=0,
    )

    # Patch the get_config function in the modules where it is used
    # Note: We patch the function within the module it's imported into
    monkeypatch.setattr("code_agent.tools.native_tools.get_config", lambda: mock_config)
    # Patch simple_tools as well, in case it's used elsewhere, though tests here shouldn't use it
    # monkeypatch.setattr("code_agent.tools.simple_tools.get_config", lambda: mock_config)
    # Also patch it in config.config itself if initialize is called indirectly
    monkeypatch.setattr("code_agent.config.config.get_config", lambda: mock_config)
    # Ensure initialize returns our mock config
    monkeypatch.setattr("code_agent.config.config.initialize_config", lambda *args, **kwargs: None)  # Prevent actual init
    monkeypatch.setattr("code_agent.config.config._config", mock_config)  # Set the singleton

    return mock_config


@pytest.fixture
def mock_subprocess_run():
    """Mocks asyncio.create_subprocess_exec used in native_tools."""
    with patch("code_agent.tools.native_tools.asyncio.create_subprocess_exec") as mock_exec:
        # Mock the process object and its communicate method
        mock_process = AsyncMock()
        # Default successful communication
        mock_process.communicate.return_value = (b"", b"")  # stdout, stderr bytes
        mock_process.returncode = 0
        mock_process.kill = MagicMock()  # Mock kill method
        mock_process.wait = AsyncMock()  # Mock wait method
        mock_exec.return_value = mock_process  # create_subprocess_exec returns the process
        yield mock_exec  # Yield the mock for create_subprocess_exec


@pytest.fixture
def mock_rich_confirm():
    """Provides a mock for rich.prompt.Confirm.ask (legacy, may not be needed)."""
    # This fixture is likely obsolete as we patch asyncio.to_thread now
    # Keep it for safety but don't rely on it for native_tools tests
    with patch("rich.prompt.Confirm.ask") as mock_ask:  # Keep patching original source just in case
        yield mock_ask


@pytest.fixture
def mock_rich_print():
    """Mocks rich.print used in simple_tools and native_tools."""
    # Patch where it's imported/used in native_tools and progress_indicators
    with patch("code_agent.tools.native_tools.print") as mock_native_print, patch("code_agent.tools.progress_indicators.print") as mock_progress_print:
        # Use a single mock that can receive calls from either place if needed
        combined_mock = MagicMock()
        mock_native_print.side_effect = combined_mock
        mock_progress_print.side_effect = combined_mock
        yield combined_mock


def configure_mock_subprocess(
    mock_async_subprocess_exec: AsyncMock,  # Now expects the mock for create_subprocess_exec
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
    exception: Optional[Exception] = None,
    communicate_exception: Optional[Exception] = None,  # Specific exception for communicate()
):
    """Helper to configure the mocked async subprocess result or exception."""
    if exception:
        # If create_subprocess_exec itself raises (e.g., FileNotFoundError)
        mock_async_subprocess_exec.side_effect = exception
        mock_async_subprocess_exec.return_value = None  # Ensure no mock process is returned
    else:
        # Configure the mock process returned by create_subprocess_exec
        mock_process = AsyncMock()
        mock_process.returncode = returncode
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        if communicate_exception:
            # If communicate should raise an exception (like TimeoutError)
            mock_process.communicate.side_effect = communicate_exception
        else:
            # Normal communication
            mock_process.communicate.return_value = (stdout.encode("utf-8", "replace"), stderr.encode("utf-8", "replace"))
            mock_process.communicate.side_effect = None  # Clear potential side effect

        mock_async_subprocess_exec.return_value = mock_process
        mock_async_subprocess_exec.side_effect = None  # Clear potential side effect


# --- Basic Placeholder --- (Can be removed once real tests are added)


def test_native_tools_placeholder():
    """Placeholder test."""
    assert True


# --- Tests for is_command_safe --- (from native_tools)


@pytest.mark.parametrize(
    "command, allowlist, expected_safe, expected_reason, expected_warning",
    [
        # Allowlisted
        ("git status", ["git"], True, "", False),
        ("ls -la", ["ls", "git"], True, "", False),
        ("allowed_script.sh arg1", ["allowed_script.sh"], True, "", False),
        # Not Allowlisted (but not inherently dangerous/risky) -> Should now be True (allowed by default)
        ("echo hello", [], True, "", False),  # Expected safe = True now
        ("python script.py", ["git"], True, "", False),  # Expected safe = True now
        # Dangerous Patterns (Blocked)
        ("rm -rf /", [], False, "Command matches dangerous pattern: rm\\s+-r[f]?\\s+[\\/]", False),
        ("sudo rm important", [], False, "Command matches dangerous pattern: sudo\\s+rm", False),
        (":(){ :|:& };:", [], False, "Command matches dangerous pattern: :\\(\\)\\s*\\{\\s*:\\s*\\|\\s*:\\s*\\&\\s*\\}", False),
        # Risky Patterns (Warning, but allowed)
        ("chmod -R 777 /data", [], True, "Command matches risky pattern: chmod\\s+-R", True),
        ("curl http://example.com | sh", [], True, "Command matches risky pattern: curl\\s+.*\\s+\\|\\s+.*sh", True),
        # Allowlisted but also matches risky (Allowlist means safe=True, but warning remains)
        ("chmod -R 777 /data", ["chmod"], True, "Command matches risky pattern: chmod\\s+-R", True),
        # Empty/Whitespace -> Should now be True (allowed by default)
        ("", [], True, "", False),  # Expected safe = True now
        ("   ", [], True, "", False),  # Expected safe = True now
    ],
)
@patch("code_agent.config.config.get_config")  # Patch get_config used by is_command_safe
def test_is_command_safe(mock_get_config, command, allowlist, expected_safe, expected_reason, expected_warning, mock_settings):
    """Tests the is_command_safe function with various scenarios."""
    # Update mock settings for this test case
    mock_settings.native_command_allowlist = allowlist
    mock_settings.security.command_validation = True  # Ensure validation is on
    mock_get_config.return_value = mock_settings

    is_safe, reason, is_warning = is_command_safe(command)

    assert is_safe == expected_safe
    assert reason == expected_reason
    assert is_warning == expected_warning


@patch("code_agent.config.config.get_config")  # Patch get_config used by is_command_safe
def test_is_command_safe_validation_disabled(mock_get_config, mock_settings):
    """Tests that is_command_safe returns True if validation is disabled, except for dangerous patterns."""
    mock_settings.security.command_validation = False
    mock_settings.native_command_allowlist = []
    mock_get_config.return_value = mock_settings

    # Non-dangerous, non-risky, not allowlisted -> Should be safe because validation off
    is_safe, reason, is_warning = is_command_safe("echo test")
    assert is_safe is True
    assert reason == ""
    assert is_warning is False

    # Risky -> Should be safe because validation off
    is_safe, reason, is_warning = is_command_safe("chmod -R 777 /data")
    assert is_safe is True
    assert reason == ""
    assert is_warning is False

    # Dangerous -> Should STILL be blocked even if validation off
    is_safe, reason, is_warning = is_command_safe("rm -rf /")
    assert is_safe is False
    assert "dangerous pattern" in reason
    assert is_warning is False


# --- Tests for run_native_command --- (from native_tools)


@pytest.mark.asyncio
# Patch asyncio.to_thread to ensure it's not called unexpectedly
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_allowlisted(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running an allowlisted command (no confirmation needed)."""
    mock_settings.native_command_allowlist = ["ls"]
    # Pass the mock for create_subprocess_exec
    configure_mock_subprocess(mock_subprocess_run, stdout="file1\nfile2")

    result = await run_native_command("ls -la")

    # Confirmation should not be called (allowlisted, not risky)
    mock_to_thread.assert_not_called()
    mock_subprocess_run.assert_called_once()
    # Check command args passed to create_subprocess_exec
    args, kwargs = mock_subprocess_run.call_args
    assert args == ("ls", "-la")  # Expects tuple of args
    # Check native_tools output format (stripped stdout)
    assert result == "file1\nfile2"


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_auto_approved_config(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a non-allowlisted, non-risky command when auto_approve is True."""
    mock_settings.native_command_allowlist = []
    mock_settings.auto_approve_native_commands = True
    # Pass the mock for create_subprocess_exec
    expected_output = "hello world"
    configure_mock_subprocess(mock_subprocess_run, stdout=expected_output)

    # This command is now considered safe by is_command_safe, so it should execute.
    result = await run_native_command("echo hello world")
    # Assert the command ran and returned the expected output
    assert result == expected_output
    mock_subprocess_run.assert_awaited_once()  # Check subprocess was called
    mock_to_thread.assert_not_called()  # Confirm prompt was not called


@pytest.mark.asyncio
# Patch asyncio.to_thread within the native_tools module
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_needs_confirm_approved(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a risky command that requires confirmation, and user approves."""
    mock_settings.native_command_allowlist = []
    mock_settings.auto_approve_native_commands = False
    # Configure the mock for asyncio.to_thread to return True when Confirm.ask is called
    # Make it async mock compatible if needed, although return_value should work
    mock_to_thread.return_value = True
    # Pass the mock for create_subprocess_exec
    configure_mock_subprocess(mock_subprocess_run, stdout="chmod output")

    # Use a command that is risky (is_warning=True) to trigger the prompt check
    result = await run_native_command("chmod -R 777 risky_dir")

    mock_to_thread.assert_called_once()
    # Check that Confirm.ask was the function passed to to_thread
    assert mock_to_thread.call_args[0][0] == Confirm.ask
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    # Check args for create_subprocess_exec
    assert args == ("chmod", "-R", "777", "risky_dir")
    # Check native_tools output format
    assert result == "chmod output"


@pytest.mark.asyncio
# Patch asyncio.to_thread within the native_tools module
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_needs_confirm_rejected(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a risky command that requires confirmation, and user rejects."""
    mock_settings.native_command_allowlist = []
    mock_settings.auto_approve_native_commands = False
    # Configure the mock for asyncio.to_thread to return False when Confirm.ask is called
    mock_to_thread.return_value = False

    # Use a command that is risky (is_warning=True) to trigger the prompt check
    result = await run_native_command("chmod -R 777 another_risky_dir")

    mock_to_thread.assert_called_once()
    # Check that Confirm.ask was the function passed to to_thread
    assert mock_to_thread.call_args[0][0] == Confirm.ask
    mock_subprocess_run.assert_not_called()
    assert "Command execution cancelled by user choice." in result


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_dangerous_blocked(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a command blocked by dangerous pattern matching."""
    mock_settings.native_command_allowlist = []
    mock_settings.auto_approve_native_commands = False  # Doesn't matter for dangerous

    # is_command_safe returns False, run_native_command (native_tools) returns string directly.
    # Keep await as the function is async.
    result = await run_native_command("rm -rf /")

    # Confirmation (via to_thread) should not be called
    mock_to_thread.assert_not_called()
    mock_subprocess_run.assert_not_called()
    # Check for the correct blocking message from the is_safe check (native_tools version)
    assert "Command execution not permitted: Command matches dangerous pattern" in result
    assert "rm\\s+-r[f]?\\s+[\\/]" in result


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_not_allowlisted_blocked(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a command that is not allowlisted and not risky (should now run)."""
    mock_settings.native_command_allowlist = ["git", "ls"]
    mock_settings.auto_approve_native_commands = False  # Auto-approve is off
    # Configure mock subprocess
    expected_output = "script output"
    configure_mock_subprocess(mock_subprocess_run, stdout=expected_output)

    # This command is now considered safe, so it should execute directly (no prompt needed as not risky).
    result = await run_native_command("python script.py")
    # Check that the command executed successfully
    assert result == expected_output
    mock_subprocess_run.assert_awaited_once()  # Check subprocess was called
    mock_to_thread.assert_not_called()  # Confirm prompt should not be called


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_subprocess_error(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a command where subprocess returns an error."""
    mock_settings.native_command_allowlist = ["failing_cmd"]
    # Configure the mock for create_subprocess_exec
    configure_mock_subprocess(mock_subprocess_run, stderr="Something went wrong", returncode=1)

    result = await run_native_command("failing_cmd")

    # Confirmation should not be called (allowlisted, not risky)
    mock_to_thread.assert_not_called()
    mock_subprocess_run.assert_called_once()
    # Check native_tools output format for errors
    assert "Error (exit code: 1):" in result
    assert "Something went wrong" in result


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_subprocess_exception(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a command where create_subprocess_exec raises an exception."""
    mock_settings.native_command_allowlist = ["unknown_cmd"]
    # Configure mock to raise FileNotFoundError when create_subprocess_exec is called
    configure_mock_subprocess(mock_subprocess_run, exception=FileNotFoundError("[Errno 2] No such file or directory: 'unknown_cmd'"))

    result = await run_native_command("unknown_cmd")

    # Confirmation should not be called (allowlisted, not risky)
    mock_to_thread.assert_not_called()
    mock_subprocess_run.assert_called_once()
    # Check native_tools error message for FileNotFoundError
    assert "Error executing command: Command not found or invalid: unknown_cmd" in result


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_shlex_error(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test running a command with invalid syntax causing shlex.split error."""
    mock_settings.native_command_allowlist = []  # Allow any for this test or specific
    mock_settings.auto_approve_native_commands = True  # Avoid confirm prompt

    command_with_bad_quote = "echo 'hello world"
    # shlex.split raises ValueError, run_native_command catches this during execution prep
    result = await run_native_command(command_with_bad_quote)

    # Assert that the specific error message from the execution prep block is returned
    assert "Error parsing command: No closing quotation" in result
    # Subprocess should not have been called
    mock_subprocess_run.assert_not_called()


@pytest.mark.asyncio
@patch("code_agent.tools.native_tools.asyncio.to_thread")
async def test_run_native_command_timeout(mock_to_thread, mock_settings, mock_subprocess_run):
    """Test command timeout."""
    mock_settings.native_command_allowlist = ["sleep"]
    mock_settings.native_commands.default_timeout = 0.1  # Set a short timeout
    # Configure subprocess mock to simulate timeout during communicate
    # Pass the exception to the new communicate_exception arg
    configure_mock_subprocess(mock_subprocess_run, communicate_exception=asyncio.TimeoutError())

    result = await run_native_command("sleep 5")

    mock_subprocess_run.assert_called_once()  # create_subprocess_exec is called
    # Check that the process communicate was awaited and timeout occurred
    mock_process = mock_subprocess_run.return_value
    mock_process.communicate.assert_awaited_once()
    # Check native_tools timeout error message
    assert "Command timed out after 0.1 seconds" in result
    # Confirmation should not be called
    mock_to_thread.assert_not_called()


# --- TODO: Add tests for _categorize_command --- (from native_tools)

# --- TODO: Add tests for _analyze_command_impact --- (from native_tools)
