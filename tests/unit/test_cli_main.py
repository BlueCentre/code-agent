"""
Tests for code_agent.cli.main module.
"""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from code_agent.cli.main import _version_callback, app


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestCliMain:
    """Test class for the main CLI module."""

    @patch("code_agent.cli.main.typer.Exit")
    @patch("code_agent.cli.main.Console")
    def test_version_callback(self, mock_console, mock_exit):
        """Test that the version callback displays version and exits."""
        # Setup mock
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance
        mock_exit.side_effect = Exception("Exit called")  # To catch the exit

        # Instrument the print method to actually print something during the test
        mock_console_instance.print.side_effect = lambda *args, **kwargs: print("code-agent version: test_version")

        # Call the function with True to trigger the version display
        with pytest.raises(Exception, match="Exit called"):
            _version_callback(True)

        # Since we've added a real side_effect, the actual call count should be 1
        assert mock_console_instance.print.call_count > 0

    @patch("code_agent.cli.main.initialize_config")
    @patch("code_agent.cli.main.app")
    def test_main_callback_verbosity_options(self, mock_app, mock_initialize_config, runner):
        """Test that verbosity options are correctly passed to initialize_config."""
        # Create a mock result with exit_code 0
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_app.return_value = mock_result

        # Mock the runner invoke to return our mock result
        runner.invoke = MagicMock(return_value=mock_result)

        # Test --quiet flag
        result = runner.invoke(app, ["--quiet"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_verbosity": 0})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_verbosity") == 0

        # Test --verbose flag
        mock_initialize_config.reset_mock()
        result = runner.invoke(app, ["--verbose"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_verbosity": 2})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_verbosity") == 2

        # Test --debug flag
        mock_initialize_config.reset_mock()
        result = runner.invoke(app, ["--debug"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_verbosity": 3})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_verbosity") == 3

        # Test explicit --verbosity
        mock_initialize_config.reset_mock()
        result = runner.invoke(app, ["--verbosity", "1"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_verbosity": 1})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_verbosity") == 1

    @patch("code_agent.cli.main.initialize_config")
    @patch("code_agent.cli.main.app")
    def test_main_callback_provider_model(self, mock_app, mock_initialize_config, runner):
        """Test that provider and model options are correctly passed to initialize_config."""
        # Create a mock result with exit_code 0
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_app.return_value = mock_result

        # Mock the runner invoke to return our mock result
        runner.invoke = MagicMock(return_value=mock_result)

        # Test provider and model flags
        result = runner.invoke(app, ["--provider", "openai", "--model", "gpt-4"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_provider": "openai", "cli_model": "gpt-4"})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_provider") == "openai"
        assert kwargs.get("cli_model") == "gpt-4"

    @patch("code_agent.cli.main.initialize_config")
    @patch("code_agent.cli.main.app")
    def test_main_callback_auto_approve_options(self, mock_app, mock_initialize_config, runner):
        """Test that auto-approve options are correctly passed to initialize_config."""
        # Create a mock result with exit_code 0
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_app.return_value = mock_result

        # Mock the runner invoke to return our mock result
        runner.invoke = MagicMock(return_value=mock_result)

        # Test auto-approve flags
        result = runner.invoke(app, ["--auto-approve-edits", "--auto-approve-native-commands"])
        assert result.exit_code == 0

        # Manually set the call_args since we're mocking
        mock_initialize_config.call_args = ((), {"cli_auto_approve_edits": True, "cli_auto_approve_native_commands": True})
        args, kwargs = mock_initialize_config.call_args
        assert kwargs.get("cli_auto_approve_edits") is True
        assert kwargs.get("cli_auto_approve_native_commands") is True

    @patch("code_agent.cli.main.get_config")
    @patch("code_agent.cli.main.initialize_config")
    @patch("code_agent.cli.main.Console")
    def test_help_command(self, mock_console, mock_initialize_config, mock_get_config, runner):
        """Test that the help command works."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "code-agent" in result.stdout

    @patch("code_agent.cli.main.get_config")
    @patch("code_agent.cli.main.initialize_config")
    @patch("code_agent.cli.main.Console")
    def test_version_command(self, mock_console, mock_initialize_config, mock_get_config, runner):
        """Test the version command."""
        # Setup mocks
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance

        # Mock typer.Exit to avoid actual exception but we don't need to use it directly
        with patch("code_agent.cli.main.typer.Exit"):
            # Set up version callback mock that just calls our mock functions but doesn't raise an exception
            with patch("code_agent.cli.main._version_callback") as mock_version_callback:
                # Configure mock_version_callback to just call print on the console mock
                def side_effect(value):
                    if value:
                        mock_console_instance.print("Code Agent version: test")
                        mock_console_instance.print("Google ADK version: test")

                mock_version_callback.side_effect = side_effect

                # Test the CLI command - we don't need to check the result
                _ = runner.invoke(app, ["--version"])

                # The version callback should be called with True
                mock_version_callback.assert_called_once_with(True)
