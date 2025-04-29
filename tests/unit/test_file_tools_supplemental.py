"""
Supplemental unit tests for code_agent/tools/file_tools.py to improve coverage.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from code_agent.tools.file_tools import (
    ApplyEditArgs,
    ReadFileArgs,
    apply_edit,
    apply_edit_legacy,
    read_file_legacy,
)


@pytest.fixture
def temp_file():
    """Create a temporary test file with known content."""
    with tempfile.NamedTemporaryFile(mode="w+t", delete=False) as f:
        f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
        temp_file_path = f.name

    yield temp_file_path

    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def temp_directory():
    """Create a temporary directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    if os.path.exists(temp_dir):
        import shutil

        shutil.rmtree(temp_dir)


class TestReadFileArgs:
    """Tests for ReadFileArgs model validation."""

    def test_read_file_args_optional_fields(self):
        """Test that ReadFileArgs accepts None for optional fields."""
        args = ReadFileArgs(path="test.txt")
        assert args.path == "test.txt"
        assert args.offset is None
        assert args.limit is None
        assert args.enable_pagination is False


class TestReadFileLegacy:
    """Tests for the read_file_legacy function."""

    @patch("code_agent.tools.file_tools.read_file")
    def test_read_file_legacy_delegates_to_read_file(self, mock_read_file, temp_file):
        """Test that read_file_legacy delegates to read_file."""
        # Mock the internal read_file function
        mock_read_file.return_value = "Mocked content"

        # Create test arguments
        args = ReadFileArgs(path=temp_file)

        # Call the legacy function
        result = read_file_legacy(args)

        # Verify that read_file was called with the correct arguments
        mock_read_file.assert_called_once_with(args)

        # Verify the result
        assert result == "Mocked content"


class TestApplyEditArgs:
    """Tests for ApplyEditArgs model validation."""

    def test_apply_edit_args_required_fields(self):
        """Test that ApplyEditArgs requires all fields."""
        # Test missing target_file
        with pytest.raises(ValidationError):
            ApplyEditArgs(code_edit="test content")

        # Test missing code_edit
        with pytest.raises(ValidationError):
            ApplyEditArgs(target_file="test.txt")

        # Test valid args
        args = ApplyEditArgs(target_file="test.txt", code_edit="test content")
        assert args.target_file == "test.txt"
        assert args.code_edit == "test content"


class TestApplyEditLegacy:
    """Tests for the apply_edit_legacy function."""

    @patch("code_agent.tools.file_tools.apply_edit")
    def test_apply_edit_legacy_delegates_to_apply_edit(self, mock_apply_edit):
        """Test that apply_edit_legacy delegates to apply_edit."""
        # Set up the mock
        mock_apply_edit.return_value = "Edit applied successfully"

        # Create test arguments
        args = ApplyEditArgs(target_file="test.txt", code_edit="New content")

        # Call the legacy function
        result = apply_edit_legacy(args)

        # Verify that apply_edit was called with the correct arguments
        mock_apply_edit.assert_called_once_with(args.target_file, args.code_edit)

        # Verify the result
        assert result == "Edit applied successfully"


class TestApplyEditEdgeCases:
    """Additional edge case tests for apply_edit."""

    @patch("code_agent.tools.file_tools.is_path_safe")
    @patch("code_agent.tools.file_tools.Path.exists")
    @patch("code_agent.tools.file_tools.Path.is_file")
    @patch("code_agent.tools.file_tools.Path.read_text")
    @patch("code_agent.tools.file_tools.Path.write_text")
    @patch("pathlib.Path.parent")
    @patch("pathlib.Path.mkdir")
    @patch("code_agent.tools.file_tools.Confirm.ask")
    def test_apply_edit_with_different_line_endings(
        self, mock_confirm, mock_mkdir, mock_parent, mock_write_text, mock_read_text, mock_is_file, mock_exists, mock_is_path_safe, temp_file
    ):
        """Test apply_edit with different line endings."""
        # Set up mocks
        mock_is_path_safe.return_value = (True, None)
        mock_exists.return_value = True
        mock_is_file.return_value = True
        # File with Windows line endings
        mock_read_text.return_value = "Line 1\r\nLine 2\r\nLine 3\r\n"
        mock_confirm.return_value = True

        # Call with edit that preserves line endings
        result = apply_edit(temp_file, "New Line 1\r\nLine 2\r\nNew Line 3\r\n")

        # Should succeed
        assert "successfully" in result.lower()
        # Should preserve Windows line endings
        mock_write_text.assert_called_once()
        written_content = mock_write_text.call_args[0][0]
        assert "\r\n" in written_content

    @patch("code_agent.tools.file_tools.is_path_safe")
    @patch("code_agent.tools.file_tools.Path.exists")
    @patch("code_agent.tools.file_tools.Path.is_file")
    @patch("code_agent.tools.file_tools.Path.read_text")
    @patch("code_agent.tools.file_tools.Path.write_text")
    @patch("code_agent.tools.file_tools.Confirm.ask")
    @patch("code_agent.tools.file_tools.console.print")
    def test_apply_edit_with_empty_edit(
        self, mock_print, mock_confirm, mock_write_text, mock_read_text, mock_is_file, mock_exists, mock_is_path_safe, temp_file
    ):
        """Test apply_edit with an empty edit string."""
        # Set up mocks
        mock_is_path_safe.return_value = (True, None)
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_read_text.return_value = "Original content"
        mock_confirm.return_value = True

        # Call with empty edit
        result = apply_edit(temp_file, "")

        # Should not write anything
        mock_write_text.assert_not_called()

        # At least one warning message should be printed
        warning_called = False
        for call in mock_print.call_args_list:
            args = call[0][0]
            if isinstance(args, str) and ("warning" in args.lower() or "no changes" in args.lower()):
                warning_called = True
                break

        # Verify a warning was shown or handled appropriately
        assert warning_called or "No changes" in result
