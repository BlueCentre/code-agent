from pathlib import Path
from unittest.mock import MagicMock, patch

from code_agent.tools.file_tools import DEFAULT_MAX_LINES, _read_file_lines, read_file


# Test for the internal _read_file_lines function
def test_read_file_lines_basic(tmp_path: Path):
    """Test the basic functionality of _read_file_lines."""
    # Create a test file with multiple lines
    test_file_path = tmp_path / "test_file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Test reading the entire file
    lines, total, next_offset = _read_file_lines(test_file_path)
    assert len(lines) == min(100, DEFAULT_MAX_LINES)
    assert total == 100
    assert next_offset == min(100, DEFAULT_MAX_LINES)
    assert lines[0] == "Line 1\n"


def test_read_file_lines_with_offset(tmp_path: Path):
    """Test _read_file_lines with an offset."""
    test_file_path = tmp_path / "test_file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Test reading with an offset
    offset = 50
    lines, total, next_offset = _read_file_lines(test_file_path, offset=offset)
    assert len(lines) == min(50, DEFAULT_MAX_LINES)  # Should read from 50 to end
    assert total == 100
    assert next_offset == 100
    assert lines[0] == "Line 51\n"


def test_read_file_lines_with_limit(tmp_path: Path):
    """Test _read_file_lines with a limit."""
    test_file_path = tmp_path / "test_file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Test reading with a limit
    limit = 20
    lines, total, next_offset = _read_file_lines(test_file_path, limit=limit)
    assert len(lines) == limit
    assert total == 100
    assert next_offset == limit
    assert lines[0] == "Line 1\n"
    assert lines[-1] == f"Line {limit}\n"


def test_read_file_lines_with_offset_and_limit(tmp_path: Path):
    """Test _read_file_lines with both offset and limit."""
    test_file_path = tmp_path / "test_file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Test reading with both offset and limit
    offset = 30
    limit = 15
    lines, total, next_offset = _read_file_lines(test_file_path, offset=offset, limit=limit)
    assert len(lines) == limit
    assert total == 100
    assert next_offset == offset + limit
    assert lines[0] == "Line 31\n"
    assert lines[-1] == f"Line {offset + limit}\n"


def test_read_file_lines_offset_beyond_file(tmp_path: Path):
    """Test _read_file_lines with an offset beyond the file size."""
    test_file_path = tmp_path / "test_file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(10)])
    test_file_path.write_text(test_content)

    # Test reading with an offset beyond the file size
    offset = 100
    lines, total, next_offset = _read_file_lines(test_file_path, offset=offset)
    assert len(lines) == 0
    assert total == 10
    assert next_offset == 10


def test_read_file_lines_empty_file(tmp_path: Path):
    """Test _read_file_lines with an empty file."""
    test_file_path = tmp_path / "empty_file.txt"
    test_file_path.write_text("")

    # Test reading an empty file
    lines, total, next_offset = _read_file_lines(test_file_path)
    assert len(lines) == 0
    assert total == 0
    assert next_offset == 0


def test_read_file_pagination_error(tmp_path: Path):
    """Test read_file when pagination encounters an error."""
    test_file_path = tmp_path / "file.txt"
    test_file_path.write_text("Test content")

    # Mock the security check to allow the test path and mock _read_file_lines to raise an exception
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        with patch("code_agent.tools.file_tools._read_file_lines", side_effect=Exception("Pagination error")):
            result = read_file(str(test_file_path), enable_pagination=True)
            assert "Error: Failed when reading with pagination" in result
            assert "Pagination error" in result


def test_read_file_with_config_pagination_enabled(tmp_path: Path):
    """Test read_file with pagination enabled in config but not in parameters."""
    test_file_path = tmp_path / "file.txt"
    test_content = "\n".join([f"Line {i+1}" for i in range(100)])
    test_file_path.write_text(test_content)

    # Create a mock config with pagination enabled
    mock_config = MagicMock()
    mock_config.file_operations.read_file.enable_pagination = True
    mock_config.file_operations.read_file.max_file_size_kb = 1024
    mock_config.file_operations.read_file.max_lines = 50

    # Mock the security check to allow the test path
    with patch("code_agent.tools.file_tools.is_path_safe", return_value=(True, None)):
        with patch("code_agent.tools.file_tools.get_config", return_value=mock_config):
            # Also need to mock file_path.is_file() to return True
            with patch("pathlib.Path.is_file", return_value=True):
                # Mock stat to return a small file size to avoid size check issues
                with patch("pathlib.Path.stat", return_value=type("obj", (object,), {"st_size": 100})):
                    # Mock read_text to return our test content
                    with patch("pathlib.Path.read_text", return_value=test_content):
                        result = read_file(str(test_file_path))
                        # Should use pagination from config even though not specified in params
                        assert "Pagination Info" in result
                        assert "Total Lines: 100" in result
