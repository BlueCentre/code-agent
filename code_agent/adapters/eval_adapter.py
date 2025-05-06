"""
Evaluation Adapter - Provides compatibility with Google ADK CLI evaluation functionality.

This module adapts our Typer-based CLI to work with ADK CLI evaluation patterns.
It implements or adapts evaluation functions for agent performance assessment.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich.console import Console

from code_agent.adapters.adk_adapter import adk_adapter

logger = logging.getLogger(__name__)

# Check for numpy, pandas and other evaluation dependencies
try:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from sklearn import metrics
    from tabulate import tabulate

    EVAL_DEPENDENCIES_AVAILABLE = True
except ImportError:
    EVAL_DEPENDENCIES_AVAILABLE = False

MISSING_EVAL_DEPENDENCIES_MESSAGE = """
To use the eval command, you need to install the following additional dependencies:

```
pip install numpy pandas scikit-learn matplotlib seaborn tabulate
```

These packages are required for evaluation metrics calculation and visualization.
"""


def check_eval_dependencies() -> bool:
    """
    Check if evaluation dependencies are available.

    Returns:
        True if all required dependencies are available, False otherwise
    """
    return EVAL_DEPENDENCIES_AVAILABLE


def load_eval_set(file_path: str) -> List[Dict[str, Any]]:
    """
    Load evaluation set from a JSON file.

    Args:
        file_path: Path to the evaluation set JSON file

    Returns:
        List of evaluation examples
    """
    logger.info(f"Loading evaluation set from {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Evaluation set file not found: {file_path}")

    with open(file_path, "r") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in evaluation set file: {file_path}")


def run_eval(
    agent_module_file_path: str,
    eval_set_file_path: Tuple[str, ...],
    config_file_path: Optional[str] = None,
    print_detailed_results: bool = False,
    result_file_path: Optional[str] = None,
    metadata_file_path: Optional[str] = None,
) -> None:
    """
    Run evaluation on an agent using the specified evaluation sets.

    Args:
        agent_module_file_path: Path to the agent module file
        eval_set_file_path: Tuple of paths to evaluation set files
        config_file_path: Optional path to config file
        print_detailed_results: Whether to print detailed results
        result_file_path: Optional path to save results
        metadata_file_path: Optional path to metadata file
    """
    console = Console()

    if not check_eval_dependencies():
        console.print(MISSING_EVAL_DEPENDENCIES_MESSAGE, style="yellow")
        raise typer.Exit(code=1)

    # Load the agent
    agent_path = Path(agent_module_file_path)
    agent = adk_adapter.load_agent(agent_path)
    if not agent:
        raise ValueError(f"Failed to load agent from {agent_module_file_path}")

    # Load all evaluation sets
    all_examples = []
    for eval_file in eval_set_file_path:
        examples = load_eval_set(eval_file)
        all_examples.extend(examples)

    # Build metadata
    metadata = {}
    if metadata_file_path:
        try:
            with open(metadata_file_path, "r") as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Error loading metadata file: {e}")

    # Add some default metadata
    metadata["agent_path"] = str(agent_path)
    metadata["eval_set_files"] = list(eval_set_file_path)
    metadata["num_examples"] = len(all_examples)

    # Run evaluation on all examples
    results = []
    console.print(f"[bold]Running evaluation on {len(all_examples)} examples...[/bold]")

    for i, example in enumerate(all_examples):
        console.print(f"[dim]Processing example {i+1}/{len(all_examples)}...[/dim]", end="\r")

        # Get user input and expected output
        user_input = example.get("input", "")
        expected_output = example.get("expected_output", "")

        if not user_input:
            logger.warning(f"Example {i+1} has no input, skipping")
            continue

        # Call the agent
        try:
            # Use the appropriate method to call the agent
            if hasattr(agent, "generate_content"):
                response = agent.generate_content(user_input)
                actual_output = response.text
            else:
                # Try calling the agent directly
                actual_output = str(agent(user_input))

            # Compare with expected output
            # In a real implementation, this would use more sophisticated metrics
            # For now, we're just checking for exact match
            match = expected_output.strip() == actual_output.strip()

            results.append(
                {
                    "example_id": i,
                    "input": user_input,
                    "expected_output": expected_output,
                    "actual_output": actual_output,
                    "score": 1.0 if match else 0.0,
                }
            )

        except Exception as e:
            logger.error(f"Error evaluating example {i+1}: {e}")
            results.append(
                {
                    "example_id": i,
                    "input": user_input,
                    "expected_output": expected_output,
                    "actual_output": f"ERROR: {e!s}",
                    "score": 0.0,
                }
            )

    # Print summary
    console.print("\n[bold green]Evaluation complete![/bold green]")

    # Calculate overall score
    if results:
        overall_score = sum(r["score"] for r in results) / len(results)
        console.print(f"[bold]Overall score: {overall_score:.2f}[/bold]")
    else:
        console.print("[yellow]No results to evaluate[/yellow]")

    # Print detailed results if requested
    if print_detailed_results and results:
        console.print("\n[bold]Detailed Results:[/bold]")
        # Create a table with tabulate
        table_data = [
            [
                r["example_id"],
                r["input"][:50] + ("..." if len(r["input"]) > 50 else ""),
                r["actual_output"][:50] + ("..." if len(r["actual_output"]) > 50 else ""),
                r["score"],
            ]
            for r in results
        ]

        console.print(tabulate(table_data, headers=["ID", "Input", "Output", "Score"], tablefmt="grid"))

    # Save results if a file path is provided
    if result_file_path:
        result_data = {
            "metadata": metadata,
            "results": results,
            "overall_score": overall_score if results else 0.0,
        }

        with open(result_file_path, "w") as f:
            json.dump(result_data, f, indent=2)

        console.print(f"[bold]Results saved to {result_file_path}[/bold]")
