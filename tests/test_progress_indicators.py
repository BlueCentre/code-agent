from unittest.mock import MagicMock, patch

from rich.status import Status

from code_agent.tools.progress_indicators import (
    command_execution_indicator,
    file_operation_indicator,
    operation_complete,
    operation_error,
    operation_warning,
    step_progress,
    thinking_indicator,
)


def test_thinking_indicator():
    """Test that thinking_indicator creates a Status with correct parameters."""
    with patch("code_agent.tools.progress_indicators.Status", autospec=True) as mock_status:
        mock_status_instance = MagicMock(spec=Status)
        mock_status.return_value.__enter__.return_value = mock_status_instance

        with thinking_indicator("Test thinking") as status:
            assert status is mock_status_instance

        # Verify Status was created with correct parameters
        mock_status.assert_called_once()
        args, kwargs = mock_status.call_args
        assert "[bold green]Test thinking[/bold green]" in args[0]
        assert kwargs.get("spinner") == "dots"


def test_file_operation_indicator():
    """Test that file_operation_indicator creates a Status with correct parameters."""
    with patch("code_agent.tools.progress_indicators.Status", autospec=True) as mock_status:
        mock_status_instance = MagicMock(spec=Status)
        mock_status.return_value.__enter__.return_value = mock_status_instance

        with file_operation_indicator("Reading", "test.py") as status:
            assert status is mock_status_instance

        # Verify Status was created with correct parameters
        mock_status.assert_called_once()
        args, kwargs = mock_status.call_args
        assert "[bold blue]Reading test.py...[/bold blue]" in args[0]
        assert kwargs.get("spinner") == "dots"


def test_command_execution_indicator():
    """Test that command_execution_indicator creates a Status with correct parameters."""
    with patch("code_agent.tools.progress_indicators.Status", autospec=True) as mock_status:
        mock_status_instance = MagicMock(spec=Status)
        mock_status.return_value.__enter__.return_value = mock_status_instance

        with command_execution_indicator("ls -la") as status:
            assert status is mock_status_instance

        # Verify Status was created with correct parameters
        mock_status.assert_called_once()
        args, kwargs = mock_status.call_args
        assert "[bold yellow]Executing: ls -la[/bold yellow]" in args[0]
        assert kwargs.get("spinner") == "dots"


def test_command_execution_indicator_long_command():
    """Test that command_execution_indicator truncates long commands."""
    with patch("code_agent.tools.progress_indicators.Status", autospec=True) as mock_status:
        mock_status_instance = MagicMock(spec=Status)
        mock_status.return_value.__enter__.return_value = mock_status_instance

        very_long_command = "find / -type f -name '*.py' -exec grep -l 'import os' {} \\; | xargs wc -l | sort -nr"
        with command_execution_indicator(very_long_command):
            pass

        # Verify command was truncated
        args, kwargs = mock_status.call_args
        assert "..." in args[0]
        assert len(very_long_command) > 50  # Original command is longer than 50 chars
        assert very_long_command[:47] in args[0]  # First 47 chars are included


def test_step_progress():
    """Test that step_progress prints formatted step information."""
    with patch("code_agent.tools.progress_indicators.console.print") as mock_print:
        step_progress("Testing step", "blue")
        mock_print.assert_called_once_with("[bold blue]◆ Testing step[/bold blue]")


def test_step_progress_completed():
    """Test that step_progress with completed=True uses checkmark."""
    with patch("code_agent.tools.progress_indicators.console.print") as mock_print:
        step_progress("Completed step", "green", completed=True)
        mock_print.assert_called_once_with("[bold green]✓ Completed step[/bold green]")


def test_operation_complete():
    """Test that operation_complete prints checkmark message."""
    with patch("code_agent.tools.progress_indicators.console.print") as mock_print:
        operation_complete("Operation done")
        mock_print.assert_called_once_with("[bold green]✓ Operation done[/bold green]")


def test_operation_warning():
    """Test that operation_warning prints warning message."""
    with patch("code_agent.tools.progress_indicators.console.print") as mock_print:
        operation_warning("Warning message")
        mock_print.assert_called_once_with("[bold yellow]⚠ Warning message[/bold yellow]")


def test_operation_error():
    """Test that operation_error prints error message."""
    with patch("code_agent.tools.progress_indicators.console.print") as mock_print:
        operation_error("Error message")
        mock_print.assert_called_once_with("[bold red]✗ Error message[/bold red]")
