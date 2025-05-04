"""
Tests for the CLI main entry point.
"""

from unittest.mock import patch

from code_agent.cli import __main__


class TestCliMainEntry:
    """Test the CLI main entry point."""

    @patch("code_agent.cli.main.app")
    def test_main_module_execution(self, mock_app):
        """Test that the main module calls app() when executed as __main__."""
        # Set up module name to simulate being run directly
        original_name = __main__.__name__
        original_spec = getattr(__main__, "__spec__", None)

        try:
            # Set module name to __main__ to simulate being run as script
            __main__.__name__ = "__main__"
            if hasattr(__main__, "__spec__"):
                delattr(__main__, "__spec__")

            # This should trigger the if __name__ == "__main__" block
            # Re-import to trigger the __name__ == "__main__" check
            import importlib

            importlib.reload(__main__)

            # Verify app() was called
            mock_app.assert_called_once()

        finally:
            # Restore original module name and spec
            __main__.__name__ = original_name
            if original_spec is not None:
                __main__.__spec__ = original_spec

    @patch("code_agent.cli.main.app")
    def test_main_module_not_executed_when_imported(self, mock_app):
        """Test that app() is not called when the module is imported."""
        # Set up module name to simulate being imported
        original_name = __main__.__name__

        try:
            # Set module name to anything other than __main__
            __main__.__name__ = "some_other_module"

            # Re-import to trigger the __name__ == "__main__" check
            import importlib

            importlib.reload(__main__)

            # Verify app() was not called
            mock_app.assert_not_called()

        finally:
            # Restore original module name
            __main__.__name__ = original_name
