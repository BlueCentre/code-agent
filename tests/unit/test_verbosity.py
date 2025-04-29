#!/usr/bin/env python
"""Test script for the verbosity controller."""

import time

from code_agent.verbosity import VerbosityLevel, get_controller


def main():
    """Test the verbosity controller with different levels."""
    controller = get_controller()

    # Start with the default level
    print(f"Starting with verbosity level: {controller.level_name}")

    # Test messages at all levels
    for level in VerbosityLevel:
        print(f"\n--- Setting verbosity to {level.name} ---")
        controller.set_level(level)

        test_messages()
        time.sleep(0.5)  # Pause for readability

    print("\nVerbosity Controller Test Complete!")


def test_messages():
    """Display test messages at various verbosity levels."""
    controller = get_controller()

    controller.show_quiet("This message will always be shown (QUIET level)")
    controller.show_normal("This message shows at NORMAL level and above")
    controller.show_verbose("This message shows at VERBOSE level and above")
    controller.show_debug("This message shows only at DEBUG level")

    controller.show_error("This is an error message (always shown)")
    controller.show_warning("This is a warning message (VERBOSE and above)")
    controller.show_info("This is an info message (NORMAL and above)")
    controller.show_success("This is a success message (NORMAL and above)")

    # Test debug info (only shown at DEBUG level)
    controller.show_debug_info({"test": "data", "level": controller.level_name})


if __name__ == "__main__":
    main()
