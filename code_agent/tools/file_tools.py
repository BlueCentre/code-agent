import difflib
from pathlib import Path
from typing import Dict, Optional, Union, Any

from google.adk.tools.function_tool import FunctionTool
from pydantic import BaseModel, Field
from rich import print
from rich.console import Console
from rich.prompt import Confirm  # For user confirmation
from rich.syntax import Syntax

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
def read_file(args: ReadFileArgs) -> str:
    """Reads the entire content of a file at the given path, restricted to CWD."""
    path = args.path
    if not is_path_within_cwd(path):
        # Break long f-string
        return (
            f"Error: Path access restricted. Can only read files within the "
            f"current working directory or its subdirectories: {path}"
        )
    try:
        # Path is already resolved in is_path_within_cwd, but resolve again for consistency
        file_path = Path(path).resolve()
        print(f"[yellow]Attempting to read file:[/yellow] {file_path}")

        if not file_path.is_file():
            return f"Error: File not found or is not a regular file: {path}"

        # Add file size check
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                mb_size = file_size / 1024 / 1024
                max_mb_size = MAX_FILE_SIZE_BYTES / 1024 / 1024
                # Break long f-string
                return (
                    f"Error: File is too large ({mb_size:.2f} MB). "
                    f"Maximum allowed size is {max_mb_size:.2f} MB."
                )
        except Exception as stat_e:
            return f"Error getting file size for {path}: {stat_e}"

        content = file_path.read_text()
        return content

    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied when trying to read file: {path}"
    except Exception as e:
        return f"Error reading file {path}: {e}"

# Create tool objects using the FunctionTool class
read_file_tool = FunctionTool.from_function(
    read_file,
    name="read_file",
    description="Reads the content of a specified file path."
)

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

# apply_edit signature should remain as modified previously
def apply_edit(args: ApplyEditArgs) -> str:
    """Applies proposed content changes to a file after showing a diff and requesting user confirmation. Restricted to CWD."""
    from code_agent.config.config import get_config
    config = get_config()
    file_path_str = args.target_file
    proposed_content = args.code_edit

    if not _is_path_safe(Path.cwd(), Path(file_path_str)):
        # Break long f-string
        return (
            f"Error: Path access restricted. Can only edit files within the "
            f"current working directory or its subdirectories: {file_path_str}"
        )

    try:
        file_path = Path(file_path_str).resolve()
        print(f"[yellow]Attempting to edit file:[/yellow] {file_path}")

        # Read current content (or empty if file doesn't exist)
        current_content = ""
        if file_path.is_file():
            current_content = file_path.read_text()
        elif file_path.exists():
            return f"Error: Path exists but is not a regular file: {args.target_file}"

        # --- Calculate and Display Diff ---
        diff = list(difflib.unified_diff(
            current_content.splitlines(keepends=True),
            proposed_content.splitlines(keepends=True),
            fromfile=f"a/{args.target_file}",
            tofile=f"b/{args.target_file}",
            lineterm='\n'
        ))

        if not diff:
            return "No changes detected. File content is the same."

        print("\n[bold]Proposed changes:[/bold]")
        # Use rich Syntax for diff highlighting
        diff_text = "".join(diff)
        syntax = Syntax(diff_text, "diff", theme="default", line_numbers=False)
        console.print(syntax)

        # --- Request Confirmation ---
        confirmed = False
        if config.auto_approve_edits:
            print("[yellow]Auto-approving edit based on configuration.[/yellow]")
            confirmed = True
        else:
            # Break long Confirm.ask call
            confirmed = Confirm.ask(
                f"Apply these changes to {args.target_file}?", default=False
            )

        # --- Apply Changes if Confirmed ---
        if confirmed:
            try:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(proposed_content)
                return f"Edit applied successfully to {args.target_file}."
            except Exception as write_e:
                return f"Error writing changes to file {args.target_file}: {write_e}"
        else:
            return "Edit cancelled by user."

    except FileNotFoundError:
        # This case might be handled by the initial check, but added for safety
        # If the intention is to create a new file, the logic handles it.
        pass # Let the diff/write logic handle file creation
    except PermissionError:
        return f"Error: Permission denied when accessing file: {args.target_file}"
    except Exception as e:
        return f"Error applying edit to {args.target_file}: {e}"

# Create the apply_edit tool
apply_edit_tool = FunctionTool.from_function(
    apply_edit,
    name="apply_edit",
    description="Proposes changes to a file by providing the new content."
)

# For compatibility with imports elsewhere, map the tool objects to their original names
read_file = read_file_tool
apply_edit = apply_edit_tool

# Example usage (can be removed later)
if __name__ == "__main__":
    # Create a dummy file to read
    dummy_path = Path("dummy_read_test.txt")
    dummy_path.write_text("This is a test file.\nIt has two lines.")

    print("Testing read_file tool:")
    # Use the updated tool with args object
    result_good = read_file(ReadFileArgs(path="dummy_read_test.txt"))
    print(f"Reading existing file:\n---\n{result_good}\n---")

    # Use the updated tool with args object
    result_bad = read_file(ReadFileArgs(path="non_existent_file.txt"))
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
    result_1 = apply_edit(ApplyEditArgs(
        target_file="dummy_edit_test.txt",
        code_edit="Line 1\nLine 2 - Modified\nLine 3\n"
    ))
    print(f"Result 1: {result_1}")
    print(f"Current content:\n{edit_path.read_text()}")

    # Test Case 2: Create a new file (requires user confirmation)
    print("\nTest 2: Create new file (confirm in prompt)")
    new_file_path = "dummy_new_file.txt"
    # Use the updated tool with args object
    result_2 = apply_edit(ApplyEditArgs(
        target_file=new_file_path,
        code_edit="This is a new file.\n"
    ))
    print(f"Result 2: {result_2}")
    new_file = Path(new_file_path)
    if new_file.exists():
        print(f"Current content:\n{new_file.read_text()}")
        new_file.unlink() # Clean up
    else:
        print(f"{new_file_path} was not created.")

    # Clean up initial dummy file
    if edit_path.exists(): # Check if it exists before unlinking
        edit_path.unlink()
