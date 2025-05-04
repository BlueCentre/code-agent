"""
Tests for the CLI main entry point using direct mocking.
"""

from unittest.mock import patch

# Import the module to test
from code_agent.cli import __main__


class TestCliMainEntrySimple:
    """Simple test for the CLI main entry point."""

    @patch("code_agent.cli.main.app")
    def test_main_module_function_exists(self, mock_app):
        """Test that the main module has the expected main function."""
        # Verify the module has the expected structure
        assert hasattr(__main__, "__name__")

        # Verify it imports app from the right place
        from code_agent.cli import main

        assert hasattr(main, "app")

        # Test the module has the if __name__ == "__main__" block
        # by examining its source code
        with open(__main__.__file__, "r") as f:
            source = f.read()
            assert 'if __name__ == "__main__":' in source
            assert "app()" in source
