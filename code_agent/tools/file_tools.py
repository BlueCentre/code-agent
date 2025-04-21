import difflib
from pathlib import Path

from pydantic import BaseModel, Field
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

console = Console()

# Define a max file size limit (e.g., 1MB)
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024


# --- Tool Input Schema ---
class ReadFileArgs(BaseModel):
    path: str = Field(..., description="The path to the file to read.")


# --- Helper for Path Validation ---
def is_path_within_cwd(path_str: str) -> bool:
    """Checks if the resolved path is within the current working directory."""
    try:
        cwd = Path.cwd()
        resolved_path = Path(path_str).resolve()
        return resolved_path.is_relative_to(cwd)
    except (ValueError, OSError):
        return False


# --- Tool Implementation ---
def read_file(path: str) -> str:
    """Reads the entire content of a file at the given path, restricted to CWD."""
    if not is_path_within_cwd(path):
        return format_path_restricted_error(path)

    try:
        # Path is already resolved in is_path_within_cwd, but resolve again for consistency
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
            if file_size > MAX_FILE_SIZE_BYTES:
                return format_file_size_error(path, file_size, MAX_FILE_SIZE_BYTES)
        except Exception as stat_e:
            return format_file_error(stat_e, path, "checking size of")

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
    if not is_path_within_cwd(path):
        return format_path_restricted_error(path)

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


# _is_path_safe helper should remain as introduced by previous edits
def _is_path_safe(base_path: Path, target_path: Path) -> bool:
    """Check if the target path is within the base path directory."""
    try:
        resolved_base = base_path.resolve()
        resolved_target = target_path.resolve()
        return resolved_target.is_relative_to(resolved_base)
    except Exception:
        return False


# apply_edit function with updated signature
def apply_edit(target_file: str, code_edit: str) -> str:
    """Applies proposed content changes to a file after showing a diff and requesting user confirmation."""
    config = get_config()

    if not is_path_within_cwd(target_file):
        return format_path_restricted_error(target_file)

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

        # --- Ask for Confirmation ---
        if config.auto_approve_edits:
            print("[yellow]Auto-approving edit based on configuration.[/yellow]")
            confirmed = True
        else:
            # Ask for confirmation only if not auto-approved
            confirmed = Confirm.ask(f"Apply these changes to {target_file}?", default=False)

        # --- Apply Changes if Confirmed ---
        if confirmed:
            try:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(proposed_content)
                return f"Edit applied successfully to {target_file}."
            except Exception as write_e:
                return format_file_error(write_e, target_file, "writing changes to")
        else:
            return "Edit cancelled by user."

    except FileNotFoundError:
        # This case might be handled by the initial check, but added for safety
        # If the intention is to create a new file, the logic handles it.
        pass  # Let the diff/write logic handle file creation
    except PermissionError as e:
        return format_file_error(e, target_file, "accessing")
    except Exception as e:
        return format_file_error(e, target_file, "applying edit to")


# For compatibility with legacy code that might expect ReadFileArgs
def read_file_legacy(args: ReadFileArgs) -> str:
    return read_file(args.path)


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
