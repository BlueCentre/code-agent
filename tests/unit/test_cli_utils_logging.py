"""
Tests for logging configuration functions in code_agent.cli.utils module.
"""

import logging

from code_agent.cli.utils import setup_logging


class TestLoggingConfiguration:
    """Tests for the logging setup function."""

    def teardown_method(self):
        """Reset logging configuration after each test."""
        # Get the root logger and remove all handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        # Reset the level to WARNING (default)
        logger.setLevel(logging.WARNING)

    def test_setup_logging_debug_level(self):
        """Test setting up logging at DEBUG level."""
        # Call the function with verbosity level 3 (DEBUG)
        setup_logging(3)

        # Get the root logger and check its level
        logger = logging.getLogger()
        assert logger.level == logging.DEBUG

        # Check that a handler was added
        assert len(logger.handlers) > 0
        # Check that the handler has the correct level
        assert logger.handlers[0].level == logging.DEBUG

    def test_setup_logging_info_level(self):
        """Test setting up logging at INFO level."""
        # Call the function with verbosity level 2 (INFO)
        setup_logging(2)

        # Get the root logger and check its level
        logger = logging.getLogger()
        assert logger.level == logging.INFO

        # Check that a handler was added
        assert len(logger.handlers) > 0
        # Check that the handler has the correct level
        assert logger.handlers[0].level == logging.INFO

    def test_setup_logging_warning_level(self):
        """Test setting up logging at WARNING level."""
        # Call the function with verbosity level 1 (WARNING)
        setup_logging(1)

        # Get the root logger and check its level
        logger = logging.getLogger()
        assert logger.level == logging.WARNING

        # Check that a handler was added
        assert len(logger.handlers) > 0
        # Check that the handler has the correct level
        assert logger.handlers[0].level == logging.WARNING

    def test_setup_logging_error_level(self):
        """Test setting up logging at ERROR level."""
        # Call the function with verbosity level 0 (ERROR)
        setup_logging(0)

        # Get the root logger and check its level
        logger = logging.getLogger()
        assert logger.level == logging.ERROR

        # Check that a handler was added
        assert len(logger.handlers) > 0
        # Check that the handler has the correct level
        assert logger.handlers[0].level == logging.ERROR

    def test_setup_logging_with_existing_handler(self):
        """Test setting up logging when handlers already exist."""
        # Add a handler first
        logger = logging.getLogger()
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)  # Set an initial level
        logger.addHandler(handler)

        # Call the function with verbosity level 0 (ERROR)
        setup_logging(0)

        # The handler should now have the ERROR level
        assert handler.level == logging.ERROR

    def test_setup_logging_invalid_level(self):
        """Test setting up logging with an invalid verbosity level."""
        # Call the function with an invalid verbosity level
        setup_logging(999)  # Invalid level

        # Default to WARNING
        logger = logging.getLogger()
        assert logger.level == logging.WARNING
