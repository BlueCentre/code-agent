"""Security utilities for validating paths and commands.

This module provides configurable security checks for file operations and command execution.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from code_agent.config.config import get_config

# List of patterns for potentially dangerous path traversal
DANGEROUS_PATH_PATTERNS = [
    r"\.\.\/",  # "../" - Directory traversal
    r"\.\.$",  # ".." at the end
    r"\/\.\.",  # "/.." in the middle
    r"~\/",  # "~/" - Home directory
    r"\/etc\/",  # "/etc/" - System config files
    r"\/var\/",  # "/var/" - System variables
    r"\/dev\/",  # "/dev/" - Device files
    r"\/root\/",  # "/root/" - Root user directory
    r"\/home\/(?!$)",  # "/home/" but not followed by the user running the process
    r"\/proc\/",  # "/proc/" - Process information
    r"\/sys\/",  # "/sys/" - System files
]

# Commands that should trigger warnings regardless of configuration
DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+-r[f]?\s+[\/]",  # rm -rf /
    r"rm\s+-[f]?r\s+[\/]",  # rm -fr /
    r"sudo\s+rm",  # sudo rm
    r"dd\s+.*if=.*of=.*",  # dd if= of=
    r"mkfs\.",  # formatting filesystems
    r":\(\)\s*\{\s*:\s*\|\s*:\s*\&\s*\}",  # Fork bomb
    r">+\s*/",  # Redirect to root directory
    r">\s+/(etc|boot)",  # Redirect to critical system directories
]

# Less dangerous but still risky commands
RISKY_COMMAND_PATTERNS = [
    r"chmod\s+-R",  # chmod -R
    r"chown\s+-R",  # chown -R
    r"mv\s+.*\s+/",  # Moving files to root
    r"cp\s+.*\s+/",  # Copying files to root
    r"wget\s+.*\s+\|\s+.*sh",  # piping wget to shell
    r"curl\s+.*\s+\|\s+.*sh",  # piping curl to shell
    r"npm\s+install\s+(-g|--global)",  # global npm install
    r"pip\s+install\s+(-g|--global)",  # global pip install
    r"apt(\-get)?\s+(remove|purge)",  # apt remove/purge
    r"yum\s+(remove|erase)",  # yum remove/erase
]

# Define standard library os path separator
SEP = os.path.sep


def is_path_safe(path_str: str, strict: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validates if a path is safe to access, considering OS differences.

    Args:
        path_str: The path string to validate.
        strict: If True, enforces workspace restriction even if config disables it.

    Returns:
        Tuple containing (is_safe, reason_if_unsafe)
    """
    # 0. Basic Input Validation
    if not path_str or path_str.isspace():
        return False, "Path cannot be empty or whitespace."
    # Null byte check MUST happen before creating Path object
    if "\0" in path_str:
        return False, "Path contains unsafe null character."

    config = get_config()
    security = getattr(config, "security", None)
    # Determine effective settings based on config and strict flag
    path_validation_enabled = strict or (security and getattr(security, "path_validation", True))
    workspace_restriction_enabled = strict or (security and getattr(security, "workspace_restriction", True))

    # 1. Early exit if validation is completely disabled
    if not path_validation_enabled and not workspace_restriction_enabled and not strict:
        return True, "Path validation and workspace restriction disabled in configuration."

    # 2. Perform Workspace Check (if enabled)
    if workspace_restriction_enabled:
        try:
            # Check for absolute paths FIRST, as these bypass relative checks
            # Simplify Windows check: Drive letter + colon is sufficient
            if re.match(r"^[a-zA-Z]:", path_str):
                return False, f"Absolute path (Windows) is outside the workspace: {path_str}"

            # If it's not a Windows absolute path, proceed with Path object handling
            cwd = Path.cwd()
            absolute_path_attempt = Path(cwd, path_str)
            resolved_path = absolute_path_attempt.resolve(strict=False)

            # Now check if it resolved outside the workspace
            if not resolved_path.is_relative_to(cwd):
                # If it resolved outside, *AND* it started with a POSIX separator, flag it as such
                if path_str.startswith(SEP):
                    return False, f"Absolute path (POSIX) is outside the workspace: {path_str}"
                else:
                    # Otherwise, it resolved outside due to traversals like ../
                    return False, f"Path resolves outside the workspace: {path_str} -> {resolved_path}"

            # If it *is* relative to cwd, it passed the workspace check. Proceed to pattern check...

        except OSError as e:
            # Errors during resolution (e.g., invalid chars on Windows not caught by null check)
            return False, f"Unable to resolve path due to OS error: {e}"
        except ValueError as e:
            # Catch potential errors like embedded null bytes if missed earlier
            return False, f"Path contains invalid characters or components: {e}"
        except Exception as e:
            # Catch-all for other unexpected pathlib errors
            return False, f"Unexpected error resolving path: {e}"

    # 3. Check for dangerous patterns (if path validation is enabled)
    if path_validation_enabled:
        try:
            # Normalize path separators for pattern matching consistency
            normalized_path_str = path_str.replace("\\", "/")
            for pattern in DANGEROUS_PATH_PATTERNS:
                # Use re.search to find pattern anywhere in the path
                if re.search(pattern, normalized_path_str):
                    # Use the specific pattern in the reason
                    return False, f"Path contains potentially unsafe pattern '{pattern}': {path_str}"
        except Exception as e:
            # Catch potential regex errors, though unlikely with predefined patterns
            return False, f"Error during pattern check: {e}"

    # 4. If all checks passed or were skipped appropriately
    return True, None


def is_command_safe(command: str) -> Tuple[bool, str, bool]:
    """
    Validates if a command is safe to execute.

    Args:
        command: The command string to validate

    Returns:
        Tuple containing (is_safe, reason_if_unsafe, is_warning)
        - is_safe: False only if command should be blocked
        - reason_if_unsafe: Description of the issue
        - is_warning: True for warnings, False for errors
    """
    config = get_config()
    security = getattr(config, "security", None)

    # 1. Check if validation is disabled (but still block dangerous)
    if security and not getattr(security, "command_validation", True):
        # Still check dangerous patterns even if validation is off
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, command):
                # Block dangerous commands always
                return False, f"Command matches dangerous pattern: {pattern}", False
        # Otherwise, allow if validation is disabled
        return True, "", False

    # 2. Check for dangerous patterns (block)
    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, command):
            return False, f"Command matches dangerous pattern: {pattern}", False

    # 3. Check for risky patterns (potential warning)
    is_risky = False
    risky_reason = ""
    # Use configured patterns if available, otherwise defaults
    risky_patterns = getattr(security, "risky_command_patterns", RISKY_COMMAND_PATTERNS)
    for pattern in risky_patterns:
        if re.search(pattern, command):
            is_risky = True
            risky_reason = f"Command matches risky pattern: {pattern}"
            break  # A command can be risky for one reason

    # 4. Check allowlist (using regex match)
    allowlist = getattr(config, "native_command_allowlist", [])
    is_allowed = False
    # Check if the command string starts with any pattern in the allowlist
    for prefix_pattern in allowlist:
        if not prefix_pattern:
            continue  # Skip empty patterns
        try:
            # Use re.match to check if command STARTS with the pattern
            if re.match(prefix_pattern, command):
                is_allowed = True
                break  # Command is allowlisted, no need to check further patterns
        except re.error as e:
            # Handle invalid regex in allowlist (should ideally be caught earlier)
            print(f"[bold yellow]Warning:[/bold yellow] Invalid regex in command allowlist: '{prefix_pattern}' - {e}")
            # Treat command as not allowed if its pattern is broken
            continue

    # 5. Determine final outcome (Corrected Logic)
    if is_allowed:
        # Allowlisted: Safe, but keep warning if risky
        return True, risky_reason if is_risky else "", is_risky
    else:
        # Not allowlisted:
        if is_risky:
            # Block risky commands NOT on allowlist, but provide reason and warning flag
            return False, risky_reason, True
        else:
            # Block non-dangerous, non-risky, non-allowlisted commands
            return False, "Command not found in the allowlist", False


def validate_commands_allowlist(allowlist: List[str]) -> List[str]:
    """
    Validates the commands allowlist against DANGEROUS patterns ONLY
    and returns a sanitized list (removes dangerous and empty).

    Args:
        allowlist: List of command prefixes/patterns to validate

    Returns:
        Sanitized list of command prefixes/patterns
    """
    if not allowlist:
        return []

    # Remove any empty/None/whitespace entries first
    sanitized = [cmd for cmd in allowlist if cmd and not cmd.isspace()]

    # Validate each command prefix against DANGEROUS patterns
    safe_commands = []
    for cmd in sanitized:
        is_dangerous = False
        # Check against dangerous command patterns
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            try:
                # Use search as the pattern might be anywhere in the allowlist entry
                if re.search(pattern, cmd):
                    print(f"[bold yellow]Warning:[/bold yellow] Allowlist item '{cmd}' matches dangerous pattern '{pattern}'. Removing.")
                    is_dangerous = True
                    break
            except re.error as e:
                print(f"[bold red]Error:[/bold red] Invalid regex pattern '{pattern}' while checking allowlist item '{cmd}': {e}")
                # Treat error during check as potentially dangerous
                is_dangerous = True
                break

        # Removed the extra check for "chmod -R" / "chown -R"

        if not is_dangerous:
            safe_commands.append(cmd)

    return safe_commands
