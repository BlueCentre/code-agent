"""Additional unit tests for CLI run commands to improve coverage."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import typer

from code_agent.cli.commands.run import run_command


class TestRunCommandAdditional(unittest.TestCase):
    """Additional tests for run command to improve coverage."""

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

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run._resolve_agent_path_str")
    def test_run_command_with_nonexistent_path(self, mock_resolve_path_str, mock_console_class):
        """Test run_command with nonexistent path."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        
        # Make _resolve_agent_path_str return None to simulate nonexistent path
        mock_resolve_path_str.return_value = None

        # Call the run command with a path that will be resolved to None
        with self.assertRaises(typer.Exit):
            run_command(
                instruction="Test instruction",
                agent_path=Path("/nonexistent/agent.py"),
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

        # Verify _resolve_agent_path_str was called
        mock_resolve_path_str.assert_called_once()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.suffix", new_callable=PropertyMock)
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location")
    def test_run_command_with_invalid_module_spec(
        self, mock_spec_from_file_location, mock_exists, mock_suffix, 
        mock_is_file, mock_setup_logging, mock_get_config, 
        mock_init_config, mock_console_class
    ):
        """Test run_command with invalid module spec."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Mock path properties
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_suffix.return_value = ".py"
        
        # Make spec_from_file_location return None (invalid module spec)
        mock_spec_from_file_location.return_value = None

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

        # Verify error message was printed
        mock_console.print.assert_called()

    @patch("code_agent.cli.commands.run.Console")
    @patch("code_agent.cli.commands.run.ADK_INSTALLED", True)
    @patch("code_agent.cli.commands.run.InMemorySessionService", MagicMock())
    @patch("code_agent.cli.commands.run.initialize_config")
    @patch("code_agent.cli.commands.run.get_config")
    @patch("code_agent.cli.commands.run.setup_logging")
    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.suffix", new_callable=PropertyMock)
    @patch("pathlib.Path.exists")
    @patch("code_agent.cli.commands.run.importlib.util.spec_from_file_location")
    @patch("code_agent.cli.commands.run.importlib.util.module_from_spec")
    def test_run_command_with_exec_module_error(
        self, mock_module_from_spec, mock_spec_from_file_location, 
        mock_exists, mock_suffix, mock_is_file, 
        mock_setup_logging, mock_get_config, mock_init_config, 
        mock_console_class
    ):
        """Test run_command with exec_module error."""
        # Create a mock console
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Setup mock config
        mock_config = MagicMock()
        mock_config.verbosity = 1
        mock_get_config.return_value = mock_config

        # Mock path properties
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_suffix.return_value = ".py"
        
        # Create mock spec and loader
        mock_spec = MagicMock()
        mock_loader = MagicMock()
        mock_spec.loader = mock_loader
        mock_spec_from_file_location.return_value = mock_spec
        
        # Create mock module
        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module
        
        # Make exec_module raise an exception
        mock_loader.exec_module.side_effect = Exception("Module execution error")

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

        # Verify exec_module was called
        mock_loader.exec_module.assert_called_once()
        
        # Verify error message was printed
        mock_console.print.assert_called() 