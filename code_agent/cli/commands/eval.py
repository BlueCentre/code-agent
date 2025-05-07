"""
Command for evaluating agent performance.
Uses our eval_adapter to provide compatibility with ADK CLI evaluation functionality.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

# Import our evaluation adapter
from code_agent.adapters.eval_adapter import (
    MISSING_EVAL_DEPENDENCIES_MESSAGE,
    check_eval_dependencies,
    run_eval,
)

# Console for rich output
console = Console()


def eval_command(
    agent_module_file_path: Annotated[
        Path, typer.Argument(exists=True, dir_okay=True, file_okay=False, resolve_path=True, help="Path to the agent source code folder.")
    ],
    eval_set_file_path: Annotated[List[str], typer.Argument(help="Path(s) to evaluation set file(s).")],
    config_file_path: Annotated[Optional[str], typer.Option(help="Optional. The path to config file.")] = None,
    print_detailed_results: Annotated[bool, typer.Option(help="Optional. Whether to print detailed results on console or not.")] = False,
    result_file_path: Annotated[Optional[str], typer.Option(help="Optional. File path to save the evaluation results.")] = None,
    metadata_file_path: Annotated[
        Optional[str], typer.Option(help="Optional. The path to the metadata file to include extra info such as the model name.")
    ] = None,
    log_level: Annotated[str, typer.Option(help="Optional. Set the logging level.")] = "INFO",
    log_to_tmp: Annotated[bool, typer.Option(help="Optional. Whether to log to system temp folder instead of console.")] = False,
):
    """
    Evaluate agent's performance against evaluation sets.

    Example:
        code-agent eval path/to/my_agent path/to/eval_set.json
    """
    # Check for eval dependencies
    if not check_eval_dependencies():
        console.print(MISSING_EVAL_DEPENDENCIES_MESSAGE, style="yellow")
        raise typer.Exit(code=1)

    # Set up logging
    if log_to_tmp:
        log_file = tempfile.NamedTemporaryFile(prefix="code_agent_eval_", suffix=".log", delete=False, mode="w")
        logging.basicConfig(
            filename=log_file.name,
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        console.print(f"[bold blue]Logging to {log_file.name}[/bold blue]")
    else:
        logging.basicConfig(level=getattr(logging, log_level.upper()))

    # Convert Path to string for compatibility with the existing function
    agent_module_file_path_str = str(agent_module_file_path)

    # Convert eval_set_file_path from List to tuple
    eval_set_file_paths = tuple(eval_set_file_path)

    try:
        run_eval(
            agent_module_file_path=agent_module_file_path_str,
            eval_set_file_path=eval_set_file_paths,
            config_file_path=config_file_path,
            print_detailed_results=print_detailed_results,
            result_file_path=result_file_path,
            metadata_file_path=metadata_file_path,
        )
    except Exception as e:
        console.print(f"[bold red]Evaluation failed: {e!s}[/bold red]")
        raise typer.Exit(code=1) from e
