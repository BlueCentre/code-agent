#!/usr/bin/env python
"""ADK Sandbox for experimentation.

This script provides a simple environment for experimenting with
Google ADK components before integrating them into the main codebase.
"""

import sys
from pathlib import Path

# First, modify path to include the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Then import the modules after path is set up
import google.adk as adk
from google.adk.models import Gemini


def main():
    """Run ADK sandbox experiments."""
    print(f"ADK Version: {adk.__version__}")
    print("ADK Sandbox Environment")
    print("=" * 80)

    # Simple environment check
    try:
        # Create a simple model instance
        model = Gemini(model_name="gemini-1.5-flash")
        print("✓ Successfully initialized Gemini model")
        # Access model configuration safely
        config = getattr(model, "config", {"model_name": "gemini-1.5-flash"})
        print(f"  Using model: {config.get('model_name', 'gemini-1.5-flash')}")
    except Exception as e:
        print(f"✗ Failed to initialize Gemini model: {e}")
        print("  Make sure you have set GOOGLE_API_KEY in your environment")

    print("\nBasic ADK Components Available:")
    print("- LlmAgent (google.adk.agents)")
    print("- Gemini model (google.adk.models)")
    print("- FunctionTool (google.adk.tools)")
    print("- InMemorySessionService (google.adk.sessions)")
    print("- InMemoryRunner (google.adk.runners)")

    print("\nReady for experimentation. Modify this script to test ADK components.")

    # TODO: Add more experiments here as needed


if __name__ == "__main__":
    main()
