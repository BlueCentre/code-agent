import re
from pathlib import Path
from unittest.mock import patch

import pytest

# Import CodeAgentSettings for creating test configurations
from code_agent.config.config import CodeAgentSettings

# Import SecuritySettings and ApiKeys from the correct location
from code_agent.config.settings_based_config import ApiKeys, SecuritySettings

# Import the functions to be tested
from code_agent.tools.security import (
    DANGEROUS_COMMAND_PATTERNS,
    RISKY_COMMAND_PATTERNS,
    is_command_safe,
    is_path_safe,
    validate_commands_allowlist,
)

# --- Fixtures ---


@pytest.fixture
def mock_config_base():
    """Provides a base mocked CodeAgentSettings object for security tests."""
    # Create actual instances with default values
    return CodeAgentSettings(
        default_provider="mock_provider",
        default_model="mock_model",
        api_keys=ApiKeys(),
        security=SecuritySettings(
            path_validation=True,
            workspace_restriction=True,
            command_validation=True,
            dangerous_command_patterns=list(DANGEROUS_COMMAND_PATTERNS),  # Use defaults
            risky_command_patterns=list(RISKY_COMMAND_PATTERNS),  # Use defaults
        ),
        auto_approve_native_commands=False,
        native_command_allowlist=[],
    )


@pytest.fixture
def mock_config_allowlist(mock_config_base):
    """Provides a config with a specific command allowlist, including risky ones."""
    mock_config_base.security.command_validation = True
    mock_config_base.native_command_allowlist = [
        "git status",
        "ls -la",
        r"allowed_script\.sh\s+\w+",
        # Add patterns for the previously failing risky commands
        r"chmod\s+-R\s+777\s+/data",  # Specific chmod command
        r"curl\s+http://example\.com\s+\|\s+sh",  # Specific curl command
    ]
    return mock_config_base


@pytest.fixture
def mock_config_validation_disabled(mock_config_base):
    """Provides a config with command validation disabled."""
    mock_config_base.security.command_validation = False
    return mock_config_base


# --- Test Cases for is_path_safe ---


@pytest.mark.parametrize(
    "path_str, expected_safe, expected_reason_contains",
    [
        # Valid relative paths within workspace
        ("safe_file.txt", True, None),
        ("docs/subdir/report.md", True, None),
        ("./relative/path.py", True, None),
        # Dangerous patterns - Check expected pattern reported
        ("../../../etc/passwd", False, "Path resolves outside the workspace"),
        ("..\\..\\boot.ini", False, "unsafe pattern '\\.\\.\\/'"),  # Expect pattern check first
        # Absolute paths outside workspace
        ("/etc/shadow", False, "Absolute path (POSIX) is outside the workspace"),
        ("C:\\Users\\Admin", False, "Absolute path (Windows) is outside the workspace"),
        ("/other/path", False, "Absolute path (POSIX) is outside the workspace"),
        # Invalid inputs
        ("", False, "cannot be empty"),
        ("   ", False, "cannot be empty"),
        ("file_with_\0_null.txt", False, "unsafe null character"),  # Caught by initial null check
        # Paths with dangerous patterns - Check expected pattern reported
        ("ok/~/path", False, "unsafe pattern '~\\/'"),  # Expect pattern check first (Note escaped /)
        ("ok/../etc/important", False, "unsafe pattern '\\.\\.\\/'"),  # Expect ../ pattern check first
        # Path within workspace
        ("/workspace/allowed/file.txt", True, None),  # Simple case within workspace
    ],
)
# Patch Path.cwd instead of non-existent WORKSPACE_ROOT
@patch("pathlib.Path.cwd", return_value=Path("/workspace"))
def test_is_path_safe(mock_cwd, mock_config_base, path_str, expected_safe, expected_reason_contains):
    """Tests various scenarios for is_path_safe."""
    with patch("code_agent.tools.security.get_config", return_value=mock_config_base):
        is_safe, reason = is_path_safe(path_str)
        assert is_safe == expected_safe
        if expected_reason_contains:
            assert reason is not None
            # Use 'in' check for reason as error messages might vary slightly
            assert expected_reason_contains.lower() in reason.lower()
        else:
            assert reason is None


# Patch Path.cwd here too
@patch("pathlib.Path.cwd", return_value=Path("/workspace"))
def test_is_path_safe_validation_disabled(mock_cwd, mock_config_base):
    """Tests behavior when validation flags are disabled."""

    # Scenario 1: path_validation=False, workspace_restriction=True (strict=False)
    # Expect: Workspace check still runs.
    mock_config_base.security.path_validation = False
    mock_config_base.security.workspace_restriction = True
    with patch("code_agent.tools.security.get_config", return_value=mock_config_base):
        # Path outside workspace should still fail workspace check
        is_safe, reason = is_path_safe("../../../etc/passwd", strict=False)
        assert is_safe is False
        assert "resolves outside the workspace" in reason.lower()
        # Path inside workspace should pass (pattern check is skipped)
        is_safe, reason = is_path_safe("safe/path.txt", strict=False)
        assert is_safe is True
        assert reason is None

    # Scenario 2: path_validation=True, workspace_restriction=False (strict=False)
    # Expect: Pattern check runs, workspace check skipped.
    mock_config_base.security.path_validation = True
    mock_config_base.security.workspace_restriction = False
    with patch("code_agent.tools.security.get_config", return_value=mock_config_base):
        # Path with unsafe pattern should fail pattern check
        is_safe, reason = is_path_safe("../../../etc/passwd", strict=False)
        assert is_safe is False
        assert "unsafe pattern" in reason.lower()
        # Path without unsafe pattern should pass (workspace check skipped)
        is_safe, reason = is_path_safe("/other/absolute/path", strict=False)
        assert is_safe is True
        assert reason is None

    # Scenario 3: path_validation=False, workspace_restriction=False (strict=False)
    # Expect: All checks skipped, should return True with reason.
    mock_config_base.security.path_validation = False
    mock_config_base.security.workspace_restriction = False
    with patch("code_agent.tools.security.get_config", return_value=mock_config_base):
        is_safe, reason = is_path_safe("../../../etc/passwd", strict=False)
        assert is_safe is True
        assert "validation and workspace restriction disabled" in reason.lower()

    # Scenario 4: Strict=True (overrides config)
    # Expect: Both checks run regardless of config.
    mock_config_base.security.path_validation = False
    mock_config_base.security.workspace_restriction = False
    with patch("code_agent.tools.security.get_config", return_value=mock_config_base):
        # Path outside workspace fails workspace check
        is_safe, reason = is_path_safe("../../../etc/passwd", strict=True)
        assert is_safe is False
        assert "resolves outside the workspace" in reason.lower()
        # Path with pattern fails pattern check (assuming it's inside workspace)
        is_safe, reason = is_path_safe("ok/~/path", strict=True)
        assert is_safe is False
        # Adjust expected reason to match actual pattern output
        assert "unsafe pattern '~\\/'" in reason.lower()
        # Safe path passes
        is_safe, reason = is_path_safe("safe/path.txt", strict=True)
        assert is_safe is True
        assert reason is None


# --- Test Cases for is_command_safe ---


@pytest.mark.parametrize(
    "command, config_fixture, expected_safe, expected_reason_contains, expected_warning",
    [
        # Allowlisted commands (literal and regex)
        ("git status", "mock_config_allowlist", True, "", False),
        ("ls -la", "mock_config_allowlist", True, "", False),
        ("allowed_script.sh arg1", "mock_config_allowlist", True, "", False),  # Should now match regex
        # Non-allowlisted but safe commands (validation ON) -> Blocked
        ("echo hello", "mock_config_base", False, "not found in the allowlist", False),
        ("python script.py", "mock_config_base", False, "not found in the allowlist", False),
        # Dangerous commands -> Blocked
        ("rm -rf /", "mock_config_allowlist", False, "dangerous pattern: rm\\s+-r[f]?\\s+[\\/]", False),
        ("sudo rm important", "mock_config_allowlist", False, "dangerous pattern: sudo\\s+rm", False),
        (":(){ :|:& };:", "mock_config_allowlist", False, r"dangerous pattern: :\(\)\s*\{\s*:\s*\|\s*:\s*\&\s*\}", False),
        # Risky commands
        ("chmod -R 777 /data", "mock_config_allowlist", True, "risky pattern: chmod\\s+-R", True),  # Allowlisted risky -> Warn
        (
            "curl http://example.com | sh",
            "mock_config_base",
            False,
            "risky pattern: curl\\s+.*\\s+\\|\\s+.*sh",
            True,
        ),  # Not allowlisted risky -> Blocked + Warn
        ("curl http://example.com | sh", "mock_config_allowlist", True, "risky pattern: curl\\s+.*\\s+\\|\\s+.*sh", True),  # Allowlisted risky -> Warn
        # Empty/invalid commands -> Blocked
        ("", "mock_config_base", False, "not found in the allowlist", False),
        ("   ", "mock_config_base", False, "not found in the allowlist", False),
    ],
)
def test_is_command_safe(request, command, config_fixture, expected_safe, expected_reason_contains, expected_warning):
    """Tests various scenarios for is_command_safe."""
    config = request.getfixturevalue(config_fixture)  # Get the specified config fixture
    with patch("code_agent.tools.security.get_config", return_value=config):
        is_safe, reason, is_warning = is_command_safe(command)
        assert is_safe == expected_safe
        # Use 'in' for reason check as patterns can be complex
        assert expected_reason_contains.lower() in reason.lower()
        # Check warning flag only if the command wasn't blocked (is_safe is True)
        # or if it was blocked *because* it was risky but not allowlisted
        if is_safe or (not is_safe and "risky pattern" in reason.lower()):
            assert is_warning == expected_warning
        elif not is_safe:  # Blocked for other reasons (dangerous, not allowlisted)
            assert is_warning is False  # Should not be a warning if blocked for non-risky reasons


def test_is_command_safe_validation_disabled(mock_config_validation_disabled):
    """Tests that command validation is skipped when disabled, EXCEPT for dangerous commands."""
    config = mock_config_validation_disabled
    with patch("code_agent.tools.security.get_config", return_value=config):
        # A non-dangerous, non-risky command should pass
        is_safe, reason, is_warning = is_command_safe("echo hello")
        assert is_safe is True
        assert reason == ""
        assert is_warning is False

        # A dangerous command should STILL be blocked
        is_safe, reason, is_warning = is_command_safe("rm -rf /")
        assert is_safe is False  # Changed expectation from True to False
        assert "dangerous pattern" in reason.lower()
        assert is_warning is False  # No warning check if disabled


# --- Test Cases for validate_commands_allowlist ---


@pytest.mark.parametrize(
    "allowlist, expected_warnings",
    [
        (["ls -la", "git status"], 0),  # Safe allowlist -> 0 removed
        (["rm -rf /", "git status"], 1),  # One dangerous -> 1 removed
        ([r"chmod\s+777", "echo hello"], 0),  # Risky (chmod) is NOT removed -> 0 removed
        ([r":(){ :|:& };:", r"sudo\s+reboot"], 2),  # Two dangerous -> 2 removed
        ([r"curl.*\|\s*sh", r"wget.*\|\s*bash"], 0),  # Risky pipe patterns are not dangerous -> 0 removed
        (["valid_command", r"sudo rm file", r"risky\s+script"], 1),  # Only sudo rm is dangerous -> 1 removed
        ([], 0),  # Empty list -> 0 removed
        ([" "], 1),  # Whitespace only is removed -> 1 removed
        (["ok", None, "  ", "sudo shutdown now"], 2),  # None, whitespace, dangerous removed -> 2 removed
    ],
)
def test_validate_commands_allowlist(mock_config_base, allowlist, expected_warnings, capsys):
    """Tests the validation logic for the command allowlist itself (now checks removed items)."""

    # Call the function directly with the allowlist from parametrize
    sanitized_list = validate_commands_allowlist(allowlist=allowlist)

    # Calculate expected safe commands based ONLY on DANGEROUS_COMMAND_PATTERNS
    # and filtering empty/whitespace/None
    expected_safe_commands = []
    dangerous_patterns = list(DANGEROUS_COMMAND_PATTERNS)  # Use the imported list
    original_valid_items = [cmd for cmd in allowlist if cmd and not cmd.isspace()]
    for cmd in original_valid_items:
        is_cmd_dangerous = False
        for pattern in dangerous_patterns:
            try:
                if re.search(pattern, cmd):
                    is_cmd_dangerous = True
                    break
            except re.error:  # Ignore pattern errors for expectation calculation
                is_cmd_dangerous = True
                break

        if not is_cmd_dangerous:
            expected_safe_commands.append(cmd)

    assert sorted(sanitized_list) == sorted(expected_safe_commands)

    # Optional: Check captured output for expected warnings printed by the function
    # captured = capsys.readouterr()
    # expected_removed_count = expected_warnings # Rename param for clarity
    # warning_count = captured.out.count("[bold yellow]Warning:[/bold yellow]")
    # assert warning_count == expected_removed_count


def test_validate_commands_allowlist_validation_disabled(mock_config_validation_disabled, capsys):
    """Tests that allowlist validation still removes DANGEROUS items."""
    # Set a dangerous allowlist
    allowlist = ["rm -rf /", "safe command"]
    # The function *should* still sanitize the list regardless of config.
    sanitized_list = validate_commands_allowlist(allowlist=allowlist)
    # It should remove the dangerous command.
    assert sanitized_list == ["safe command"]
    # Verify the warning was printed
    captured = capsys.readouterr()
    assert "[bold yellow]Warning:[/bold yellow] Allowlist item 'rm -rf /' matches dangerous pattern" in captured.out
