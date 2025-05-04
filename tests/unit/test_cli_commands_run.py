"""Unit tests for CLI run commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import typer

from code_agent.cli.commands.run import run_command


class TestRunCommand(unittest.TestCase):
    """Tests for CLI run command."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.agent_dir = Path(self.temp_dir.name) / "test_agent"
        self.agent_dir.mkdir(exist_ok=True)

        # Create a simple agent file for testing
        self.agent_file = self.agent_dir / "agent.py"
        with open(self.agent_file, "w") as f:
            f.write("""
from google.adk import Agent

# Define a simple agent
agent = Agent("Test Agent")

@agent.register_chat
def chat():
    return "This is a test agent"
""")

        # Create an __init__.py file to make it a package
        with open(self.agent_dir / "__init__.py", "w") as f:
            f.write("")

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.run_cli")
    @patch("importlib.util.spec_from_file_location")
    def test_run_command_with_valid_agent_file(
        self, mock_spec_from_file_location, mock_run_cli, mock_resolve_path, mock_setup_logging,
        mock_get_config, mock_init_config, mock_console_class
    ):
        """Test run_command with a valid agent file."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_config.provider = "openai"
        mock_config.model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock path resolution to return our test agent file path
        mock_resolve_path.return_value = str(self.agent_file)

        # Mock importlib functionality
        mock_spec = MagicMock()
        mock_loader = MagicMock()
        mock_spec.loader = mock_loader
        mock_spec_from_file_location.return_value = mock_spec

        # Create a mock module with root_agent
        mock_module = MagicMock()
        mock_module.root_agent = MagicMock()
        mock_module.root_agent.name = "Test Agent"

        # Set up the mock to return our module
        with patch("importlib.util.module_from_spec", return_value=mock_module):
            # Call the run command
            run_command(
                instruction="Test instruction",
                agent_path=self.agent_file,
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify run_cli was called
        mock_run_cli.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.run_cli")
    @patch("code_agent.cli.commands.run.importlib")
    def test_run_command_with_valid_agent_package(
        self, mock_importlib, mock_run_cli, mock_resolve_path, mock_setup_logging,
        mock_get_config, mock_init_config, mock_console_class
    ):
        """Test run_command with a valid agent package."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_config.provider = "openai"
        mock_config.model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock path resolution to return our test agent directory path
        mock_resolve_path.return_value = str(self.agent_dir)

        # Mock importlib to return a module with a root_agent
        mock_module = MagicMock()
        mock_module.root_agent = MagicMock()
        mock_importlib.import_module.return_value = mock_module

        # Call the run command with a directory path
        run_command(
            instruction="Test instruction",
            agent_path=self.agent_dir,
            session_id=None,
            interactive=False,
            show_timestamps=False,
            log_level=None,
            provider=None,
            model=None,
            temperature=None,
            max_tokens=None,
            save_session_cli=False,
            verbose=False
        )

        # Verify run_cli was called
        mock_run_cli.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", False)
    def test_run_command_without_adk_installed(self, mock_console_class):
        """Test run_command when ADK is not installed."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the run command
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=self.agent_file,
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify error message was printed
        mock_console.print.assert_called()
        error_message_calls = [call for call in mock_console.print.call_args_list if "Error" in str(call)]
        self.assertGreater(len(error_message_calls), 0)

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", None)
    def test_run_command_with_missing_session_service(self, mock_console_class):
        """Test run_command when InMemorySessionService is missing."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Call the run command
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=self.agent_file,
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify error message was printed
        mock_console.print.assert_called()
        self.assertTrue(any("Failed to import" in str(call) for call in mock_console.print.call_args_list))

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str", return_value=None)
    def test_run_command_with_invalid_agent_path(
        self, mock_resolve_path, mock_setup_logging,
        mock_get_config, mock_init_config, mock_console_class
    ):
        """Test run_command with an invalid agent path."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Call the run command with an invalid path
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("/invalid/path"),
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify _resolve_agent_path_str was called
        mock_resolve_path.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location", return_value=None)
    def test_run_command_with_module_loading_error(
        self, mock_spec_from_file, mock_resolve_path, mock_setup_logging,
        mock_get_config, mock_init_config, mock_console_class
    ):
        """Test run_command with a module loading error."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Mock path resolution to return our test agent file path
        mock_resolve_path.return_value = str(self.agent_file)

        # Call the run command with a file that can't be loaded
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=self.agent_file,
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify _resolve_agent_path_str was called
        mock_resolve_path.assert_called_once()

        # Verify spec_from_file_location was called
        mock_spec_from_file.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("code_agent.cli.commands.run.run_cli")
    @patch("code_agent.cli.commands.run.importlib")
    def test_run_command_with_package_import_error(
        self, mock_importlib, mock_run_cli, mock_resolve_path, mock_setup_logging,
        mock_get_config, mock_init_config, mock_console_class
    ):
        """Test run_command with a package import error."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Mock path resolution to return our test agent directory path
        mock_resolve_path.return_value = str(self.agent_dir)

        # Mock Path.is_file and Path.is_dir to control flow
        with patch("pathlib.Path.is_file", return_value=False), \
             patch("pathlib.Path.is_dir", return_value=True):

            # Make importlib.import_module raise ImportError
            mock_importlib.import_module.side_effect = ImportError("Module not found")

            # Call the run command with a package that can't be imported
            with self.assertRaises(typer.Exit):
                run_command(
                    instruction="Test instruction",
                    agent_path=self.agent_dir,
                    session_id=None,
                    interactive=False,
                    show_timestamps=False,
                    log_level=None,
                    provider=None,
                    model=None,
                    temperature=None,
                    max_tokens=None,
                    save_session_cli=False,
                    verbose=False
                )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify _resolve_agent_path_str was called
        mock_resolve_path.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    @patch("pathlib.Path.is_file", return_value=False)
    @patch("pathlib.Path.is_dir", return_value=False)
    def test_run_command_with_invalid_path_type(
        self, mock_is_dir, mock_is_file, mock_resolve_path,
        mock_setup_logging, mock_get_config, mock_init_config,
        mock_console_class
    ):
        """Test run_command with a path that is neither a file nor a directory."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Mock path resolution to return a path string
        mock_resolve_path.return_value = "/neither/file/nor/directory"

        # Call the run command with an invalid path type
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("/neither/file/nor/directory"),
                session_id=None,
                interactive=False,
                show_timestamps=False,
                log_level=None,
                provider=None,
                model=None,
                temperature=None,
                max_tokens=None,
                save_session_cli=False,
                verbose=False
            )

        # Verify initialize_config was called
        mock_init_config.assert_called_once()

        # Verify _resolve_agent_path_str was called
        mock_resolve_path.assert_called_once()
