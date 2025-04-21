import difflib
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator
from rich import print
from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from code_agent.config import get_config
from code_agent.tools.error_utils import (
    format_file_error,
    format_file_size_error,
    format_path_restricted_error,
)
from code_agent.tools.security import is_path_safe

console = Console()

# Default values (will be overridden by config)
DEFAULT_MAX_FILE_SIZE_KB = 1024  # 1MB
DEFAULT_MAX_LINES = 1000

# For backward compatibility with existing tests
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024


# --- Tool Input Schema ---
class ReadFileArgs(BaseModel):
    path: str = Field(..., description="The path to the file to read.")
    offset: Optional[int] = Field(None, description="Line number to start reading from (0-indexed).")
    limit: Optional[int] = Field(None, description="Maximum number of lines to read.")
    enable_pagination: bool = Field(False, description="Whether to enable pagination for large files.")

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v):
        if v is not None and v < 0:
            raise ValueError("offset must be a non-negative integer")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v is not None and v <= 0:
            raise ValueError("limit must be a positive integer")
        return v


# --- Helper for Path Validation ---
def is_path_within_cwd(path_str: str) -> bool:
    """Checks if the resolved path is within the current working directory."""
    is_safe, _ = is_path_safe(path_str)
    return is_safe


def _count_file_lines(file_path: Path) -> int:
    """
    Count the number of lines in a file efficiently.

    Args:
        file_path: Path to the file

    Returns:
        Number of lines in the file
    """
    count = 0
    with file_path.open("r") as f:
        for _ in f:
            count += 1
    return count


def _read_file_lines(file_path: Path, offset: int = 0, limit: Optional[int] = None) -> Tuple[List[str], int, int]:
    """
    Read lines from a file with pagination support.

    Args:
        file_path: Path to the file
        offset: Line number to start reading from (0-indexed)
        limit: Maximum number of lines to read

    Returns:
        Tuple of (lines read, total line count, next offset)
    """
    all_lines = file_path.read_text().splitlines(keepends=True)
    total_lines = len(all_lines)

    # Skip to the offset
    if offset >= total_lines:
        # Offset beyond file size, return empty list
        return [], total_lines, total_lines

    # Read up to the limit
    max_lines = limit if limit is not None else DEFAULT_MAX_LINES
    end_idx = min(offset + max_lines, total_lines)

    # Get the slice of lines for this range
    selected_lines = all_lines[offset:end_idx]
    next_offset = end_idx

    return selected_lines, total_lines, next_offset


# --- Tool Implementation ---
def read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None, enable_pagination: bool = False) -> str:
    """
    Reads the content of a file at the given path, with optional pagination support.

    Args:
        path: The path to the file to read
        offset: Line number to start reading from (0-indexed, optional)
        limit: Maximum number of lines to read (optional)
        enable_pagination: Whether to enable pagination for large files

    Returns:
        The file content or an error message
    """
    # Validate the offset and limit parameters
    if offset is not None and offset < 0:
        return f"Error: offset must be a non-negative integer, got {offset}"

    if limit is not None and limit <= 0:
        return f"Error: limit must be a positive integer, got {limit}"

    # Get configuration settings
    config = get_config()

    # Get file read settings from config or use defaults
    try:
        max_file_size_kb = config.file_operations.read_file.max_file_size_kb
        max_lines = config.file_operations.read_file.max_lines
        config_enable_pagination = config.file_operations.read_file.enable_pagination
    except AttributeError:
        # Fall back to defaults if configuration structure is not available
        max_file_size_kb = DEFAULT_MAX_FILE_SIZE_KB
        max_lines = DEFAULT_MAX_LINES
        config_enable_pagination = False

    # Convert KB to bytes
    max_file_size_bytes = max_file_size_kb * 1024

    # Use parameter value or config value for enable_pagination (parameter takes precedence)
    use_pagination = enable_pagination or config_enable_pagination

    # Set limit from parameter or config
    max_lines_to_read = limit if limit is not None else max_lines

    is_safe, reason = is_path_safe(path)
    if not is_safe:
        return format_path_restricted_error(path, reason)

    try:
        # Path is already validated in is_path_safe
        file_path = Path(path).resolve()
        print(f"[yellow]Attempting to read file:[/yellow] {file_path}")

        if not file_path.is_file():
            return (
                f"Error: File not found or is not a regular file: '{path}'.\n"
                f"Please check:\n"
                f"- If the path points to a regular file, not a directory\n"
                f"- If the file exists at the specified location"
            )

        # Add file size check
        try:
            file_size = file_path.stat().st_size
            if file_size > max_file_size_bytes and not use_pagination:
                return format_file_size_error(path, file_size, max_file_size_bytes, "To read large files, use pagination by setting enable_pagination=True")
        except Exception as stat_e:
            return format_file_error(stat_e, path, "checking size of")

        # If pagination is enabled, use the pagination logic
        if use_pagination:
            try:
                offset_value = offset if offset is not None else 0
                lines, total_lines, next_offset = _read_file_lines(file_path, offset_value, max_lines_to_read)

                # Build result with pagination info
                has_more = next_offset < total_lines
                content = "".join(lines)

                # Add pagination metadata
                pagination_info = (
                    f"\n\n--- Pagination Info ---\n"
                    f"File: {path}\n"
                    f"Total Lines: {total_lines}\n"
                    f"Current Range: Lines {offset_value+1}-{next_offset} (showing {len(lines)} lines)\n"
                )

                if has_more:
                    pagination_info += f"More content available: Yes (use offset={next_offset} to continue reading)\n"
                else:
                    pagination_info += "More content available: No (reached end of file)\n"

                return content + pagination_info
            except Exception as e:
                return format_file_error(e, path, "reading with pagination")
        else:
            # Read the whole file if pagination is disabled
            content = file_path.read_text()
            return content

    except FileNotFoundError as e:
        return format_file_error(e, path, "reading")
    except PermissionError as e:
        return format_file_error(e, path, "reading")
    except Exception as e:
        return format_file_error(e, path, "reading")


# --- Delete File Tool Function ---
def delete_file(path: str) -> str:
    """Deletes a file at the given path, restricted to CWD."""
    is_safe, reason = is_path_safe(path)
    if not is_safe:
        return format_path_restricted_error(path, reason)

    try:
        file_path = Path(path).resolve()
        print(f"[yellow]Attempting to delete file:[/yellow] {file_path}")

        if not file_path.exists():
            return f"Error: File does not exist: '{path}'.\n" f"Please check if the file path is correct."

        if not file_path.is_file():
            return (
                f"Error: Path exists but is not a regular file: '{path}'.\n"
                f"Only regular files can be deleted with this tool.\n"
                f"If you're trying to delete a directory, this operation is not supported."
            )

        file_path.unlink()
        return f"File deleted successfully: {path}"

    except FileNotFoundError as e:
        return format_file_error(e, path, "deleting")
    except PermissionError as e:
        return format_file_error(e, path, "deleting")
    except Exception as e:
        return format_file_error(e, path, "deleting")


# --- Apply Edit Tool Input Schema ---
class ApplyEditArgs(BaseModel):
    target_file: str = Field(..., description="The path to the file to edit.")
    code_edit: str = Field(..., description="The proposed content to apply to the file.")


def apply_edit(target_file: str, code_edit: str) -> str:
    """Applies proposed content changes to a file after showing a diff and requesting user confirmation."""
    config = get_config()

    is_safe, reason = is_path_safe(target_file)
    if not is_safe:
        return format_path_restricted_error(target_file, reason)

    try:
        file_path = Path(target_file).resolve()

        # Check if path exists and is a directory
        if file_path.exists() and not file_path.is_file():
            return (
                f"Error: Path exists but is not a regular file: '{target_file}'.\n"
                f"Only regular files can be edited. If you're trying to edit a directory,\n"
                f"this operation is not supported."
            )

        # Get current content or empty string if file doesn't exist
        current_content = ""
        if file_path.exists() and file_path.is_file():
            try:
                current_content = file_path.read_text()
            except Exception as read_e:
                return format_file_error(read_e, target_file, "reading for edit")

        proposed_content = code_edit

        # Check if there's an actual change
        if current_content == proposed_content and file_path.exists():
            return f"No changes needed, file content already matches the proposed edit for {target_file}."

        # --- Prepare and Show Diff ---
        is_new_file = not file_path.exists()

        console = Console()
        print()
        if is_new_file:
            print(f"[bold green]Creating new file:[/bold green] {target_file}")

            # Just show the syntax-highlighted content for new files
            syntax = Syntax(
                proposed_content,
                lexer="python",  # This will be auto-detected in many cases
                line_numbers=True,
                theme="monokai",
            )
            console.print(syntax)
        else:
            print(f"[bold yellow]Editing existing file:[/bold yellow] {target_file}")

            # Generate diff between current and proposed
            diff = list(
                difflib.unified_diff(
                    current_content.splitlines(),
                    proposed_content.splitlines(),
                    fromfile=f"Current: {target_file}",
                    tofile=f"Proposed: {target_file}",
                    lineterm="",
                )
            )

            # Create a highlighted diff display
            table = Table(show_header=False, box=None)
            table.add_column("Change", style="bold")
            table.add_column("Line")

            for line in diff:
                if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                    table.add_row("", f"[dim]{line}[/dim]")
                elif line.startswith("+"):
                    table.add_row("+", f"[green]{line[1:]}[/green]")
                elif line.startswith("-"):
                    table.add_row("-", f"[red]{line[1:]}[/red]")
                else:
                    table.add_row("", line)

            console.print(table)

        # --- Request Confirmation ---
        if not config.auto_approve_edits:
            if is_new_file:
                if not Confirm.ask(f"Create new file {target_file} with the shown content?", default=False):
                    return "Edit cancelled. No file created."
            else:
                if not Confirm.ask(f"Apply these changes to {target_file}?", default=False):
                    return "Edit cancelled. File remains unchanged."
        else:
            print("[yellow]Auto-approving edit based on configuration.[/yellow]")

        # --- Apply the Changes ---
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the new content
            file_path.write_text(proposed_content)

            if is_new_file:
                return f"New file successfully created at {target_file}."
            else:
                return f"File {target_file} successfully updated."
        except PermissionError as e:
            return format_file_error(e, target_file, "writing to")
        except Exception as e:
            return format_file_error(e, target_file, "writing to")

    except Exception as e:
        return format_file_error(e, target_file, "processing edit for")


# Legacy function that accepts ReadFileArgs for compatibility
def read_file_legacy(args: ReadFileArgs) -> str:
    return read_file(args.path)


# Legacy function that accepts ApplyEditArgs for compatibility
def apply_edit_legacy(args: ApplyEditArgs) -> str:
    return apply_edit(args.target_file, args.code_edit)


# Example usage (can be removed later)
if __name__ == "__main__":
    # Create a dummy file to read
    dummy_path = Path("dummy_read_test.txt")
    dummy_path.write_text("This is a test file.\nIt has two lines.")

    print("Testing read_file tool:")
    # Use the updated tool with args object
    result_good = read_file("dummy_read_test.txt")
    print(f"Reading existing file:\n---\n{result_good}\n---")

    # Use the updated tool with args object
    result_bad = read_file("non_existent_file.txt")
    print(f"Reading non-existent file:\n---\n{result_bad}\n---")

    # Clean up dummy file
    dummy_path.unlink()

    print("\nTesting apply_edit tool:")
    # Create a dummy file
    edit_path = Path("dummy_edit_test.txt")
    edit_path.write_text("Line 1\nLine 2\nLine 3\n")
    print(f"Created: {edit_path.name}")

    # Test Case 1: Apply a change (requires user confirmation in terminal)
    print("\nTest 1: Modify existing file (confirm in prompt)")
    # Use the updated tool with args object
    result_1 = apply_edit("dummy_edit_test.txt", "Line 1\nLine 2 - Modified\nLine 3\n")
    print(f"Result 1: {result_1}")
    print(f"Current content:\n{edit_path.read_text()}")

    # Test Case 2: Create a new file (requires user confirmation)
    print("\nTest 2: Create new file (confirm in prompt)")
    new_file_path = "dummy_new_file.txt"
    # Use the updated tool with args object
    result_2 = apply_edit(new_file_path, "This is a new file.\n")
    print(f"Result 2: {result_2}")
    new_file = Path(new_file_path)
    if new_file.exists():
        print(f"Current content:\n{new_file.read_text()}")
        new_file.unlink()  # Clean up
    else:
        print(f"{new_file_path} was not created.")

    # Clean up initial dummy file
    if edit_path.exists():  # Check if it exists before unlinking
        edit_path.unlink()
