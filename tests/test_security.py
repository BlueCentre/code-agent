import tempfile
from unittest import mock

import pytest

from code_agent.config import SecuritySettings, SettingsConfig
from code_agent.tools.security import (
    is_command_safe,
    is_path_safe,
    validate_commands_allowlist,
)


@pytest.fixture
def mock_config():
    """Mock the config for testing security settings."""
    security_settings = SecuritySettings(
        path_validation=True,
        workspace_restriction=True,
        command_validation=True,
    )
    mock_config = mock.MagicMock(spec=SettingsConfig)
    mock_config.security = security_settings
    mock_config.native_command_allowlist = ["ls", "cat", "echo"]
    return mock_config


class TestPathSecurity:
    """Tests for path security validation."""

    def test_safe_path(self, mock_config):
        """Test a safe path within CWD."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason = is_path_safe("test_file.txt")
            assert is_safe is True
            assert reason is None

    def test_path_traversal_attempt(self, mock_config):
        """Test path traversal attempts are detected."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason = is_path_safe("../../../etc/passwd")
            assert is_safe is False
            assert "unsafe pattern" in reason.lower()

    def test_absolute_path_outside_cwd(self, mock_config):
        """Test absolute paths outside CWD are rejected."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason = is_path_safe("/etc/passwd")
            assert is_safe is False
            assert "outside" in reason.lower()

    def test_path_security_disabled(self, mock_config):
        """Test paths are allowed when security is disabled."""
        mock_config.security.path_validation = False
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason = is_path_safe("../file.txt", strict=False)
            assert is_safe is True
            assert reason is None

    def test_workspace_restriction_disabled(self, mock_config):
        """Test paths outside CWD are allowed when workspace restriction is disabled."""
        mock_config.security.workspace_restriction = False
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            # Create a temp file outside CWD
            with tempfile.NamedTemporaryFile() as temp:
                is_safe, reason = is_path_safe(temp.name, strict=False)
                assert is_safe is True
                assert reason is None


class TestCommandSecurity:
    """Tests for command security validation."""

    def test_safe_command(self, mock_config):
        """Test a safe command."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason, is_warning = is_command_safe("echo hello")
            assert is_safe is True
            assert reason == ""
            assert is_warning is False

    def test_dangerous_command(self, mock_config):
        """Test dangerous commands are rejected."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason, is_warning = is_command_safe("rm -rf /")
            assert is_safe is False
            assert "dangerous pattern" in reason.lower()
            assert is_warning is False

    def test_risky_command(self, mock_config):
        """Test risky commands trigger warnings."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason, is_warning = is_command_safe("chmod -R 777 /tmp")
            assert is_safe is True  # Risky commands are allowed but warn
            assert "risky pattern" in reason.lower()
            assert is_warning is True

    def test_command_not_in_allowlist(self, mock_config):
        """Test commands not in allowlist are rejected."""
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason, is_warning = is_command_safe("curl example.com")
            assert is_safe is False
            assert "not found in the allowlist" in reason.lower()
            assert is_warning is False

    def test_command_validation_disabled(self, mock_config):
        """Test commands are allowed when security is disabled."""
        mock_config.security.command_validation = False
        with mock.patch("code_agent.tools.security.get_config", return_value=mock_config):
            is_safe, reason, is_warning = is_command_safe("rm -rf /")
            assert is_safe is True
            assert reason == ""
            assert is_warning is False


class TestAllowlistValidation:
    """Tests for command allowlist validation."""

    def test_validate_allowlist(self):
        """Test allowlist validation removes dangerous commands."""
        allowlist = ["ls", "echo", "rm -rf /", "cat", "chmod -R 777 ."]
        safe_allowlist = validate_commands_allowlist(allowlist)
        assert "ls" in safe_allowlist
        assert "echo" in safe_allowlist
        assert "cat" in safe_allowlist
        assert "rm -rf /" not in safe_allowlist
        assert "chmod -R 777 ." not in safe_allowlist

    def test_empty_allowlist(self):
        """Test empty allowlist validation."""
        assert validate_commands_allowlist([]) == []
        assert validate_commands_allowlist(None) == []
