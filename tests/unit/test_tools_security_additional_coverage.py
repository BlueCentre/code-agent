"""
Tests to increase coverage for code_agent.tools.security module,
focusing on sanitization methods and error handling.
"""

import pathlib
from unittest.mock import patch

from code_agent.tools.security import (
    convert_to_path_safely,
    sanitize_directory_name,
    sanitize_file_name,
    validate_path,
)


class TestToolsSecurity:
    """Tests for the security module with focus on edge cases."""

    def test_sanitize_file_name_edge_cases(self):
        """Test sanitize_file_name with various edge cases."""
        # Test with None
        assert sanitize_file_name(None) == "untitled"
        # Test with empty string
        assert sanitize_file_name("") == "untitled"
        # Test with whitespace
        assert sanitize_file_name("   ") == "untitled"
        # Test with special characters
        assert sanitize_file_name("!@#$%^&*().txt") == "file_________.txt"
        # Test with null bytes
        assert sanitize_file_name("\0\1\2file.txt") == "file___.txt"

    def test_sanitize_directory_name_edge_cases(self):
        """Test sanitize_directory_name with various edge cases."""
        # Test with None
        assert sanitize_directory_name(None) == "directory"
        # Test with empty string
        assert sanitize_directory_name("") == "directory"
        # Test with whitespace
        assert sanitize_directory_name("   ") == "directory"
        # Test with special characters
        assert sanitize_directory_name("!@#$%^&*()") == "dir_________"
        # Test with null bytes
        assert sanitize_directory_name("\0\1\2dir") == "dir___"

    def test_convert_to_path_safely_edge_cases(self):
        """Test convert_to_path_safely with various edge cases."""
        # Test with None
        assert convert_to_path_safely(None) is None

        # Test with empty string
        assert convert_to_path_safely("") == pathlib.Path(".")

        # Test with absolute path
        abs_path = "/absolute/path"
        assert convert_to_path_safely(abs_path) == pathlib.Path(abs_path)

        # Test with relative path
        rel_path = "relative/path"
        assert convert_to_path_safely(rel_path) == pathlib.Path(rel_path)

        # Test with path containing special characters
        special_path = "path!@#$%^&*()/file.txt"
        assert convert_to_path_safely(special_path) == pathlib.Path(special_path)

        # Test with Windows path
        windows_path = "C:\\Windows\\path"
        # Note: On non-Windows systems, this will be treated as a relative path
        expected_path = pathlib.Path(windows_path)
        assert convert_to_path_safely(windows_path) == expected_path

        # Test with Unicode path
        unicode_path = "path/to/filé.txt"
        assert convert_to_path_safely(unicode_path) == pathlib.Path(unicode_path)

        # Test with Path object
        path_obj = pathlib.Path("path/to/file.txt")
        assert convert_to_path_safely(path_obj) == path_obj

    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.exists")
    def test_validate_path_with_nonexistent_path(self, mock_exists, mock_is_dir):
        """Test validate_path with nonexistent path."""
        # Mock exists to return False
        mock_exists.return_value = False

        # Test with nonexistent path
        test_path = pathlib.Path("/nonexistent/path")
        result = validate_path(test_path)

        # Should return False
        assert not result

        # Verify is_dir was not called
        mock_is_dir.assert_not_called()

    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.exists")
    def test_validate_path_with_file(self, mock_exists, mock_is_dir):
        """Test validate_path with a file path."""
        # Mock exists to return True
        mock_exists.return_value = True

        # Mock is_dir to return False (indicating a file)
        mock_is_dir.return_value = False

        # Test with file path
        test_path = pathlib.Path("/path/to/file.txt")
        result = validate_path(test_path)

        # Should return False
        assert not result

    @patch("os.access")
    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.exists")
    def test_validate_path_with_directory_no_access(self, mock_exists, mock_is_dir, mock_access):
        """Test validate_path with directory but no access."""
        # Mock exists to return True
        mock_exists.return_value = True

        # Mock is_dir to return True
        mock_is_dir.return_value = True

        # Mock access to return False
        mock_access.return_value = False

        # Test with directory path
        test_path = pathlib.Path("/path/to/directory")
        result = validate_path(test_path)

        # Should return False due to no access
        assert not result

    @patch("code_agent.tools.security.is_path_safe")
    @patch("os.access")
    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.exists")
    def test_validate_path_with_valid_directory(self, mock_exists, mock_is_dir, mock_access, mock_is_path_safe):
        """Test validate_path with valid directory."""
        # Mock exists to return True
        mock_exists.return_value = True

        # Mock is_dir to return True
        mock_is_dir.return_value = True

        # Mock access to return True
        mock_access.return_value = True

        # Mock is_path_safe to return (True, None)
        mock_is_path_safe.return_value = (True, None)

        # Test with directory path
        test_path = pathlib.Path("/path/to/directory")
        result = validate_path(test_path)

        # Should return True when everything is valid
        assert result is True

    @patch("os.access")
    @patch("pathlib.Path.is_dir")
    @patch("pathlib.Path.exists")
    def test_validate_path_with_exception(self, mock_exists, mock_is_dir, mock_access):
        """Test validate_path when an exception occurs."""
        # Mock exists to raise an exception
        mock_exists.side_effect = Exception("Test exception")

        # Test with path
        test_path = pathlib.Path("/path/to/something")
        result = validate_path(test_path)

        # Should return False due to exception
        assert not result

        # Verify is_dir and access were not called
        mock_is_dir.assert_not_called()
        mock_access.assert_not_called()
