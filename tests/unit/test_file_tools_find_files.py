"""
Unit tests for find_files function in code_agent/tools/file_tools.py.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from code_agent.tools.file_tools import find_files


class TestFindFilesAdvanced:
    """Advanced tests for the find_files function."""

    @pytest.fixture
    def complex_directory_structure(self):
        """Create a complex temporary directory structure with different file types."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # Create subdirectories with different depths
        sub_dirs = [
            "subdir1",
            "subdir1/nested1",
            "subdir1/nested1/deep1",
            "subdir2",
            "subdir2/nested2",
            "empty_dir",
        ]

        for sub_dir in sub_dirs:
            os.makedirs(os.path.join(temp_dir, sub_dir), exist_ok=True)

        # Create files with different extensions
        files = [
            "file1.txt",
            "file2.py",
            "subdir1/sub_file1.txt",
            "subdir1/sub_file2.py",
            "subdir1/nested1/nested_file1.txt",
            "subdir1/nested1/nested_file2.json",
            "subdir1/nested1/deep1/deep_file1.py",
            "subdir2/sub2_file1.txt",
            "subdir2/sub2_file2.md",
            "subdir2/nested2/nested2_file1.py",
            ".hidden_file.txt",  # Hidden file
        ]

        for file_path in files:
            with open(os.path.join(temp_dir, file_path), "w") as f:
                f.write(f"Content of {file_path}")

        yield temp_dir

        # Clean up
        import shutil

        shutil.rmtree(temp_dir)

    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_with_pattern(self, mock_is_path_safe, complex_directory_structure):
        """Test find_files with different file patterns."""
        # Mock is_path_safe to return True
        mock_is_path_safe.return_value = (True, None)

        # Find all text files
        result = find_files(complex_directory_structure, "*.txt")
        # Should find 5 text files (including the hidden one)
        txt_files = [f for f in result if f.endswith(".txt")]
        assert len(txt_files) == 5

        # Find all Python files
        result = find_files(complex_directory_structure, "*.py")
        # Should find 4 Python files
        py_files = [f for f in result if f.endswith(".py")]
        assert len(py_files) == 4

        # Find files with specific name pattern
        result = find_files(complex_directory_structure, "*file1*")
        # Should find files with "file1" in their name
        assert len(result) >= 5

    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_with_max_depth(self, mock_is_path_safe, complex_directory_structure):
        """Test find_files with different max_depth values."""
        # Mock is_path_safe to return True
        mock_is_path_safe.return_value = (True, None)

        # Test with max_depth=0 (only files in the root directory)
        result = find_files(complex_directory_structure, "*", max_depth=0)
        # Should only find files in the root directory (file1.txt, file2.py, .hidden_file.txt)
        assert len(result) == 3
        for file_path in result:
            # Check that files are directly in the root directory, accounting for macOS /private resolution
            file_dir = os.path.dirname(file_path)
            normalized_file_dir = file_dir.replace("/private", "", 1) if file_dir.startswith("/private") else file_dir
            normalized_test_dir = (
                complex_directory_structure.replace("/private", "", 1) if complex_directory_structure.startswith("/private") else complex_directory_structure
            )
            assert normalized_file_dir == normalized_test_dir

        # Test with max_depth=1 (files in root and immediate subdirectories)
        result = find_files(complex_directory_structure, "*", max_depth=1)
        # Should find files in root and immediate subdirectories but not deeper
        deep_files = [f for f in result if "deep1" in f or "nested1" in f or "nested2" in f]
        # No files from deeper directories
        assert len(deep_files) == 0

        # Test with max_depth=2 (files up to nested1 and nested2 level)
        result = find_files(complex_directory_structure, "*", max_depth=2)
        # Should find files in root, subdir1, subdir2, nested1, and nested2, but not in deep1
        deep_files = [f for f in result if "deep1" in f]
        # No files from deepest directory
        assert len(deep_files) == 0
        nested_files = [f for f in result if "nested1" in f or "nested2" in f]
        # Should find files in nested directories
        assert len(nested_files) > 0

    def test_find_files_nonexistent_directory(self):
        """Test find_files with a nonexistent directory."""
        result = find_files("/nonexistent/directory", "*")
        assert result == []

    @patch("code_agent.tools.file_tools.console.print")
    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_unsafe_path(self, mock_is_path_safe, mock_console_print):
        """Test find_files with an unsafe path."""
        # Mock the is_path_safe function to return False
        mock_is_path_safe.return_value = (False, "Path is restricted")

        # Call find_files with any path
        result = find_files("/some/path", "*")

        # Check that the result is empty
        assert result == []

        # Check that the console.print was called with an error message
        error_called = False
        for call in mock_console_print.call_args_list:
            args = call[0][0]
            if isinstance(args, str) and "Error" in args and "Path is restricted" in args:
                error_called = True
                break
        assert error_called, "Error message was not printed"

    @patch("pathlib.Path.iterdir")
    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_permission_error(self, mock_is_path_safe, mock_iterdir, complex_directory_structure):
        """Test find_files handles permission errors correctly."""
        # Mock is_path_safe to return True
        mock_is_path_safe.return_value = (True, None)

        # Mock iterdir to raise PermissionError
        mock_iterdir.side_effect = PermissionError("Permission denied")

        # Call find_files
        result = find_files(complex_directory_structure, "*")

        # Result should be empty or contain only files that could be accessed
        assert len(result) == 0

    @patch("pathlib.Path.is_file")
    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_other_error(self, mock_is_path_safe, mock_is_file, complex_directory_structure):
        """Test find_files handles other errors correctly."""
        # Mock is_path_safe to return True
        mock_is_path_safe.return_value = (True, None)

        # Mock is_file to raise an unexpected error
        mock_is_file.side_effect = RuntimeError("Unexpected error")

        # Call find_files and check if it handles the error gracefully
        try:
            result = find_files(complex_directory_structure, "*")
            # If it reaches here, it handled the error
            assert len(result) == 0
        except RuntimeError:
            pytest.fail("find_files did not handle the unexpected error gracefully")

    @patch("code_agent.tools.file_tools.console.print")
    @patch("code_agent.tools.file_tools.is_path_safe")
    def test_find_files_empty_directory(self, mock_is_path_safe, mock_console_print, tmp_path):
        """Test find_files with an empty directory."""
        # Mock is_path_safe to return True
        mock_is_path_safe.return_value = (True, None)

        # Create an empty directory
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        # Call find_files on the empty directory
        result = find_files(str(empty_dir), "*")

        # Result should be empty
        assert result == []

        # Verify warning message was printed
        warning_called = False
        for call in mock_console_print.call_args_list:
            args = call[0][0]
            if isinstance(args, str) and "Found 0 file(s)" in args:
                warning_called = True
                break
        assert warning_called, "Warning message was not printed"


if __name__ == "__main__":
    pytest.main()
