"""
Tests for code_agent.cli.utils module operations.
"""

from unittest.mock import MagicMock, patch

from rich.console import Console

from code_agent.cli.utils import (
    load_config_data,
    operation_complete,
    operation_error,
    operation_warning,
    save_config_data,
    step_progress,
    thinking_indicator,
)


class TestOperationMessages:
    """Tests for operation message display functions."""

    def test_operation_complete(self):
        """Test operation_complete function."""
        mock_console = MagicMock(spec=Console)
        operation_complete(mock_console, "Task completed successfully")
        mock_console.print.assert_called_once()
        assert "✓" in mock_console.print.call_args[0][0]
        assert "Task completed successfully" in mock_console.print.call_args[0][0]

    def test_operation_error(self):
        """Test operation_error function."""
        mock_console = MagicMock(spec=Console)
        operation_error(mock_console, "Error occurred during operation")
        mock_console.print.assert_called_once()
        assert "✗" in mock_console.print.call_args[0][0]
        assert "Error occurred during operation" in mock_console.print.call_args[0][0]

    def test_operation_warning(self):
        """Test operation_warning function."""
        mock_console = MagicMock(spec=Console)
        operation_warning(mock_console, "Warning: this might cause issues")
        mock_console.print.assert_called_once()
        assert "!" in mock_console.print.call_args[0][0]
        assert "Warning: this might cause issues" in mock_console.print.call_args[0][0]

    def test_step_progress(self):
        """Test step_progress function."""
        mock_console = MagicMock(spec=Console)
        step_progress(mock_console, "Processing data")
        mock_console.print.assert_called_once()
        assert "→" in mock_console.print.call_args[0][0]
        assert "Processing data" in mock_console.print.call_args[0][0]


class TestThinkingIndicator:
    """Tests for thinking_indicator context manager."""

    def test_thinking_indicator(self):
        """Test thinking_indicator context manager."""
        mock_console = MagicMock(spec=Console)
        message = "Thinking..."

        # Use the context manager
        with thinking_indicator(mock_console, message):
            # Should display the message
            mock_console.print.assert_called_once()
            assert message in mock_console.print.call_args[0][0]
            assert mock_console.print.call_args[1]["end"] == "\r"
            mock_console.print.reset_mock()

        # Should clear the message after the context
        mock_console.print.assert_called_once()
        assert mock_console.print.call_args[0][0].strip() == ""  # Just spaces
        assert mock_console.print.call_args[1]["end"] == "\r"


class TestConfigFileOperations:
    """Tests for config file loading and saving functions."""

    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_load_config_data_existing_file(self, mock_yaml_load, mock_open):
        """Test loading data from an existing config file."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        # Set up mock file and YAML data
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = "key: value"
        mock_yaml_load.return_value = {"key": "value"}

        # Call the function
        result = load_config_data(mock_path)

        # Verify the mocks were called correctly
        mock_path.exists.assert_called_once()
        mock_open.assert_called_once_with(mock_path, "r")
        mock_file.read.assert_called_once()
        mock_yaml_load.assert_called_once_with("key: value")

        # Verify the result
        assert result == {"key": "value"}

    @patch("builtins.open")
    @patch("yaml.safe_dump")
    def test_save_config_data(self, mock_yaml_dump, mock_open):
        """Test saving config data to a file."""
        mock_path = MagicMock()
        mock_path.parent = MagicMock()

        # Config data to save
        config_data = {"key": "value", "nested": {"subkey": "subvalue"}}

        # Call the function
        save_config_data(mock_path, config_data)

        # Verify the mocks were called correctly
        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_open.assert_called_once_with(mock_path, "w")
        mock_yaml_dump.assert_called_once()

        # Verify YAML dump args
        _, kwargs = mock_yaml_dump.call_args
        assert kwargs["default_flow_style"] is False
        assert kwargs["sort_keys"] is False
        assert mock_yaml_dump.call_args[0][0] == config_data
