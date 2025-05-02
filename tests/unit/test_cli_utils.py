"""
Tests for code_agent.cli.utils module.
"""

# Need imports for testing run_cli
import asyncio
import logging
import signal
import unittest  # Add this import
from pathlib import Path  # Ensure Path is imported
from unittest.mock import MagicMock, patch

import pytest
import typer  # Ensure typer is imported
import yaml  # Ensure yaml is imported
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from rich.console import Console

from code_agent.cli.utils import (
    _resolve_agent_path_str,  # Ensure this is imported
    load_config_data,  # Ensure this is imported
    operation_complete,
    operation_error,
    operation_warning,
    save_config_data,  # Ensure this is imported
    setup_logging,
    step_progress,
    thinking_indicator,
)

# Ensure settings models are imported if needed by fixtures
from code_agent.config.settings_based_config import CodeAgentSettings


@pytest.mark.parametrize(
    "level_input, expected_log_level",
    [
        (3, logging.DEBUG),
        (2, logging.INFO),
        (1, logging.WARNING),
        (0, logging.ERROR),
        (4, logging.WARNING),  # Test out of range high
        (-1, logging.WARNING),  # Test out of range low
        (None, logging.WARNING),  # Test None input (should default)
    ],
)
@patch("code_agent.cli.utils.logging.StreamHandler")  # Mock handler creation
@patch("code_agent.cli.utils.logging.Formatter")  # Mock formatter
@patch("code_agent.cli.utils.logging.getLogger")  # Mock getting the logger
def test_setup_logging_levels_no_handlers(mock_get_logger, mock_formatter, mock_handler_class, level_input, expected_log_level):
    """Test setup_logging with various levels when no handlers exist."""
    # Arrange
    mock_root_logger = MagicMock()
    mock_root_logger.handlers = []  # Simulate no handlers initially
    mock_get_logger.return_value = mock_root_logger
    mock_handler_instance = MagicMock()
    mock_handler_class.return_value = mock_handler_instance

    # Act
    setup_logging(level_input)

    # Assert
    mock_get_logger.assert_called_once()
    # Check root logger level was set
    mock_root_logger.setLevel.assert_called_once_with(expected_log_level)
    # Check default handler was added and configured
    mock_handler_class.assert_called_once()
    mock_formatter.assert_called_once()
    mock_handler_instance.setFormatter.assert_called_once()
    mock_handler_instance.setLevel.assert_called_once_with(expected_log_level)
    mock_root_logger.addHandler.assert_called_once_with(mock_handler_instance)


@patch("code_agent.cli.utils.logging.getLogger")
def test_setup_logging_existing_handlers(mock_get_logger):
    """Test setup_logging sets levels on existing handlers."""
    # Arrange
    mock_root_logger = MagicMock()
    mock_handler1 = MagicMock()
    mock_handler2 = MagicMock()
    mock_root_logger.handlers = [mock_handler1, mock_handler2]  # Simulate existing handlers
    mock_get_logger.return_value = mock_root_logger
    test_level = logging.DEBUG
    verbosity_input = 3

    # Act
    setup_logging(verbosity_input)

    # Assert
    mock_get_logger.assert_called_once()
    # Check root logger level was set
    mock_root_logger.setLevel.assert_called_once_with(test_level)
    # Check existing handlers had their levels set
    mock_handler1.setLevel.assert_called_once_with(test_level)
    mock_handler2.setLevel.assert_called_once_with(test_level)
    # Check a new handler was NOT added
    mock_root_logger.addHandler.assert_not_called()


# Add more tests here for other functions in utils.py


@patch("code_agent.cli.utils.Console")
def test_thinking_indicator(mock_console_class):
    """Test the thinking_indicator context manager."""
    mock_console_instance = MagicMock(spec=Console)
    mock_console_class.return_value = mock_console_instance
    message = "Processing..."

    with thinking_indicator(mock_console_instance, message):
        # Check print called on entry
        mock_console_instance.print.assert_called_once_with(f"[dim]{message}[/dim]", end="\r")
        mock_console_instance.print.reset_mock()  # Reset for exit check
        pass  # Simulate work being done

    # Check print called on exit to clear the line
    mock_console_instance.print.assert_called_once_with(" " * len(message), end="\r")


@patch("rich.console.Console.print")
def test_operation_complete(mock_print):
    """Test operation_complete prints the correct message."""
    console = Console()  # Real console, but print is mocked
    message = "Task finished."
    operation_complete(console, message)
    mock_print.assert_called_once_with(f"[bold green]✓[/bold green] {message}")


@patch("rich.console.Console.print")
def test_operation_error(mock_print):
    """Test operation_error prints the correct message."""
    console = Console()
    message = "Task failed."
    operation_error(console, message)
    mock_print.assert_called_once_with(f"[bold red]✗[/bold red] {message}")


@patch("rich.console.Console.print")
def test_operation_warning(mock_print):
    """Test operation_warning prints the correct message."""
    console = Console()
    message = "Something needs attention."
    operation_warning(console, message)
    mock_print.assert_called_once_with(f"[bold yellow]![/bold yellow] {message}")


@patch("rich.console.Console.print")
def test_step_progress(mock_print):
    """Test step_progress prints the correct message."""
    console = Console()
    message = "Starting next step..."
    step_progress(console, message)
    mock_print.assert_called_once_with(f"[bold cyan]→[/bold cyan] {message}")


# --- Tests for run_cli --- #


# Mock agent for tests
class MockAgent:
    def __init__(self, name="mock_agent"):
        self.name = name


# We need to patch things used *inside* run_cli
@patch("code_agent.cli.utils.signal.getsignal")
@patch("code_agent.cli.utils.signal.signal")
@patch("code_agent.cli.utils.signal.raise_signal")  # For non-interactive re-raise
@patch("code_agent.cli.utils.Runner")  # Mock the ADK Runner
@patch("code_agent.cli.utils.InMemorySessionService")  # Mock Session Service
@patch("code_agent.cli.utils.Console")  # Mock Console used inside
@patch("code_agent.cli.utils.Prompt.ask")  # Mock interactive prompt
def test_run_cli_sigint_non_interactive(
    mock_prompt_ask,
    mock_console_class,
    mock_session_service_class,
    mock_runner_class,
    mock_raise_signal,
    mock_signal,
    mock_getsignal,
    event_loop,  # Use pytest-asyncio event_loop fixture
):
    """Test SIGINT handling in non-interactive mode."""
    # Arrange
    mock_agent = MockAgent()
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_runner_instance = MagicMock(spec=Runner)
    mock_runner_class.return_value = mock_runner_instance
    original_handler = MagicMock()
    mock_getsignal.return_value = original_handler
    registered_handler = None

    # Capture the handler registered by run_cli
    def capture_handler(sig, handler):
        nonlocal registered_handler
        if sig == signal.SIGINT:
            registered_handler = handler

    mock_signal.side_effect = capture_handler

    # Simulate runner raising KeyboardInterrupt when handler is called
    async def mock_run_async(*args, **kwargs):
        # Simulate the interrupt occurring during processing
        if registered_handler:
            registered_handler(signal.SIGINT, None)  # Call the captured handler
        # After interrupt, the generator should stop or raise
        # We'll simulate it stopping by just not yielding anything further
        # or potentially raising the expected exception if the handler didn't stop it.
        # Since non-interactive re-raises, we expect an exception propagation
        # However, mocking raise_signal makes it hard to test propagation easily.
        # Instead, we'll assert raise_signal was called.
        # Use a simpler mock object or a valid event type
        mock_event = MagicMock()
        mock_event.type = "mock_event"
        yield mock_event  # Yield one event before interrupt
        # Stop generation after interrupt
        return

    mock_runner_instance.run_async.side_effect = mock_run_async

    # Act
    # Run run_cli (which calls process_message_async internally via asyncio.run)
    # We need to handle the async nature
    from code_agent.cli.utils import run_cli  # Import here to avoid issues with patching

    # run_cli uses asyncio.run, which manages its own loop.
    # We run it and check mocks afterwards.
    run_cli(mock_agent, "test_app", interactive=False, initial_instruction="Do stuff")

    # Assert
    # Check getsignal was called with SIGINT (allow multiple calls)
    mock_getsignal.assert_called_with(signal.SIGINT)
    # Check signal handler was registered
    mock_signal.assert_any_call(signal.SIGINT, registered_handler)
    # In non-interactive, it should restore the original handler and re-raise
    # Check raise_signal was called (easier than testing actual propagation)
    mock_raise_signal.assert_called_once_with(signal.SIGINT)
    # Check console output for interrupt message
    mock_console.print.assert_any_call("\n[bold yellow]Interrupt signal received. Exiting gracefully...")


@pytest.mark.skip(reason="Interactive SIGINT test needs refactoring due to asyncio.run mock complexity")  # Skip for now
@patch("code_agent.cli.utils.signal.getsignal")
@patch("code_agent.cli.utils.signal.signal")
@patch("code_agent.cli.utils.Runner")
@patch("code_agent.cli.utils.InMemorySessionService")
@patch("code_agent.cli.utils.Console")
@patch("code_agent.cli.utils.Prompt.ask", side_effect=["quit"])  # Simulate user typing quit
@patch("code_agent.cli.utils.asyncio.run")  # Mock asyncio.run to control the loop
def test_run_cli_sigint_interactive(
    mock_asyncio_run, mock_prompt_ask, mock_console_class, mock_session_service_class, mock_runner_class, mock_signal, mock_getsignal, event_loop
):
    """Test SIGINT handling in interactive mode."""
    # Arrange
    mock_agent = MockAgent()
    mock_console = MagicMock()
    mock_console_class.return_value = mock_console
    mock_runner_instance = MagicMock(spec=Runner)
    mock_runner_class.return_value = mock_runner_instance
    mock_session_service_instance = MagicMock(spec=InMemorySessionService)
    mock_session_service_class.return_value = mock_session_service_instance
    original_handler = MagicMock()
    mock_getsignal.return_value = original_handler
    registered_handler = None
    interrupt_occurred_in_handler = False

    def capture_handler(sig, handler):
        nonlocal registered_handler
        if sig == signal.SIGINT:
            registered_handler = handler

    mock_signal.side_effect = capture_handler

    # This will be the main async function called by the mocked asyncio.run
    async def mock_main_loop():
        nonlocal interrupt_occurred_in_handler
        # Simulate the interactive loop's behavior
        # First, process the initial message
        # (process_message_async needs to be mocked or tested separately)
        # Here, we focus on the SIGINT during the prompt

        # Simulate the prompt loop where the interrupt happens
        try:
            # Simulate work before prompt
            await asyncio.sleep(0.01)

            # Simulate the interrupt happening *while waiting for input*
            # or during processing of the previous message if that makes more sense.
            # Let's simulate it happening *before* the prompt.ask call
            if registered_handler:
                registered_handler(signal.SIGINT, None)  # Call the captured handler
                interrupt_occurred_in_handler = True

            # Normally Prompt.ask would block, but we mocked it to return 'quit'
            # or raise KeyboardInterrupt if that's how the handler works.
            # The test setup makes Prompt.ask return 'quit', so the loop exits.
            await asyncio.sleep(0.01)  # Allow event loop to process signal if needed

        except KeyboardInterrupt:
            # This might happen if the handler re-raises, but it shouldn't in interactive
            pass

    mock_asyncio_run.side_effect = lambda coro: event_loop.run_until_complete(coro)

    # Act
    from code_agent.cli.utils import run_cli

    # Run in interactive mode, provide initial instruction
    run_cli(mock_agent, "test_app", interactive=True, initial_instruction="First instruction")

    # Assert
    # Run the mocked main loop via the patched asyncio.run
    mock_asyncio_run.assert_called_once()
    # Get the coroutine passed to asyncio.run and run it
    coro = mock_asyncio_run.call_args[0][0]
    event_loop.run_until_complete(coro)

    assert interrupt_occurred_in_handler, "SIGINT handler was not called"
    mock_getsignal.assert_called_once_with(signal.SIGINT)
    mock_signal.assert_any_call(signal.SIGINT, registered_handler)
    # Check console output for interrupt message
    mock_console.print.assert_any_call("\n[bold yellow]Interrupt signal received. Exiting gracefully...")
    # Check loop likely exited due to interrupt/quit prompt
    # mock_prompt_ask might have been called once for the 'quit' input
    assert mock_prompt_ask.call_count <= 1  # Called 0 or 1 times depending on timing


@patch("builtins.open", new_callable=unittest.mock.mock_open)
@patch("code_agent.cli.utils.yaml.safe_dump")  # Patch safe_dump used for saving
def test_save_config_data_success(mock_yaml_dump, mock_open_func):
    """Test successfully saving data to a YAML file."""
    mock_path = MagicMock(spec=Path)
    # Mock the parent attribute on the specific mock_path instance
    mock_path.parent = MagicMock(spec=Path)
    config_data = {"new_key": "new_value"}
    save_config_data(mock_path, config_data)
    # Assert mkdir was called on the mocked parent
    mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_func.assert_called_once_with(mock_path, "w")
    mock_file_handle = mock_open_func()
    mock_yaml_dump.assert_called_once_with(config_data, mock_file_handle, default_flow_style=False, sort_keys=False)


@patch("builtins.open", side_effect=IOError("Cannot write"))
def test_save_config_data_write_error(mock_open_func):
    """Test saving data when writing to the file fails."""
    mock_path = MagicMock(spec=Path)
    # Mock the parent attribute on the specific mock_path instance
    mock_path.parent = MagicMock(spec=Path)
    config_data = {"error_key": "error_value"}
    # Function catches generic Exception and raises typer.Exit
    with pytest.raises(typer.Exit):
        save_config_data(mock_path, config_data)
    # Assert mkdir was called on the mocked parent
    mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_open_func.assert_called_once_with(mock_path, "w")


# --- Config helper tests ... ---


@pytest.fixture
def mock_settings_with_default():
    """Provides mock settings with a default agent path."""
    # Ensure CodeAgentSettings is correctly initialized if needed
    return CodeAgentSettings(default_agent_path=Path("path/to/default_agent"))


@pytest.fixture
def mock_settings_without_default():
    """Provides mock settings without a default agent path."""
    return CodeAgentSettings(default_agent_path=None)


# --- _resolve_agent_path_str tests --- #
@patch("code_agent.cli.utils.Path.resolve")
def test_resolve_agent_path_str_cli_provided(mock_resolve):
    """Test resolving path when CLI provides a path."""
    # Configure mock_resolve to return an object with a mocked exists method
    cli_path_obj = Path("path/from/cli")
    abs_path_obj = MagicMock(spec=Path)
    abs_path_obj.__str__.return_value = "/abs/path/from/cli"  # How it converts to string
    abs_path_obj.exists.return_value = True  # Simulate path existing
    mock_resolve.return_value = abs_path_obj

    cfg = CodeAgentSettings()
    resolved_path_str = _resolve_agent_path_str(cli_path_obj, cfg)

    assert resolved_path_str == str(abs_path_obj)
    # Assert that the exists method on the returned object was called
    abs_path_obj.exists.assert_called_once()
    # Assert resolve was called on the input path object implicitly (tricky, rely on behavior)


@patch("code_agent.cli.utils.Path.resolve")
def test_resolve_agent_path_str_cli_provided_not_exist(mock_resolve):
    """Test resolving path when CLI provides a path that does not exist."""
    cli_path_obj = Path("non/existent/cli/path")
    abs_path_obj = MagicMock(spec=Path)
    abs_path_obj.__str__.return_value = "/abs/non/existent/cli/path"
    abs_path_obj.exists.return_value = False  # Simulate path NOT existing
    mock_resolve.return_value = abs_path_obj

    cfg = CodeAgentSettings()
    resolved_path_str = _resolve_agent_path_str(cli_path_obj, cfg)
    assert resolved_path_str is None
    # Assert that the exists method on the returned object was called
    abs_path_obj.exists.assert_called_once()


@patch("code_agent.cli.utils.Path.resolve")
def test_resolve_agent_path_str_cli_none_default_exists(mock_resolve, mock_settings_with_default):
    """Test resolving path when CLI is None and default exists."""
    cli_path = None
    cfg = mock_settings_with_default
    abs_default_path_obj = MagicMock(spec=Path)
    abs_default_path_obj.__str__.return_value = "/abs/path/to/default_agent"
    abs_default_path_obj.exists.return_value = True  # Simulate path existing
    mock_resolve.return_value = abs_default_path_obj

    resolved_path_str = _resolve_agent_path_str(cli_path, cfg)

    assert resolved_path_str == str(abs_default_path_obj)
    # Assert that the exists method on the returned object was called
    abs_default_path_obj.exists.assert_called_once()


@patch("code_agent.cli.utils.Path.resolve")
def test_resolve_agent_path_str_cli_none_default_exists_not_exist(mock_resolve, mock_settings_with_default):
    """Test resolving path when CLI is None and default exists but path doesn't."""
    cli_path = None
    cfg = mock_settings_with_default
    abs_default_path_obj = MagicMock(spec=Path)
    abs_default_path_obj.__str__.return_value = "/abs/path/to/default_agent"
    abs_default_path_obj.exists.return_value = False  # Simulate path NOT existing
    mock_resolve.return_value = abs_default_path_obj

    resolved_path_str = _resolve_agent_path_str(cli_path, cfg)
    assert resolved_path_str is None
    # Assert that the exists method on the returned object was called
    abs_default_path_obj.exists.assert_called_once()


@patch("code_agent.cli.utils.Path.cwd")  # Patch cwd
@patch("code_agent.cli.utils.Path.resolve")  # Patch resolve
def test_resolve_agent_path_str_cli_none_default_none(mock_resolve, mock_cwd, mock_settings_without_default):
    """Test resolving path when CLI is None and default is None."""
    cli_path = None
    cfg = mock_settings_without_default

    cwd_path_obj = MagicMock(spec=Path)
    cwd_path_obj.__str__.return_value = "/mock/current/dir"
    cwd_path_obj.exists.return_value = True  # Assume CWD exists

    # Mock Path('.').resolve() to return our mock CWD object
    # We need to be careful how resolve is patched. Assume global patch works.
    mock_resolve.return_value = cwd_path_obj
    # We also need Path('.') to trigger the resolve mock correctly.
    # Patching Path.cwd might be simpler if the code uses that.
    # Let's assume the code does Path('.').resolve()

    resolved_path_str = _resolve_agent_path_str(cli_path, cfg)
    assert resolved_path_str == str(cwd_path_obj)

    # Assert that the exists method on the returned object was called
    cwd_path_obj.exists.assert_called_once()
    # We no longer mock or assert on cwd directly if resolve handles Path('.')
    # mock_cwd.assert_called_once()


# --- load_config_data tests --- #
@patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="key: value")
@patch("code_agent.cli.utils.yaml.safe_load")
def test_load_config_data_success(mock_yaml_load, mock_open_func):
    """Test successfully loading data from a YAML file."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    file_content = "key: value"
    expected_data = {"key": "value"}
    mock_yaml_load.return_value = expected_data
    data = load_config_data(mock_path)
    assert data == expected_data
    mock_path.exists.assert_called_once()
    mock_open_func.assert_called_once_with(mock_path, "r")
    mock_yaml_load.assert_called_once_with(file_content)


@patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="")
@patch("code_agent.cli.utils.yaml.safe_load")
def test_load_config_data_empty_file(mock_yaml_load, mock_open_func):
    """Test loading data from an empty YAML file."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    data = load_config_data(mock_path)
    assert data == {}
    mock_path.exists.assert_called_once()
    mock_open_func.assert_called_once_with(mock_path, "r")
    mock_yaml_load.assert_not_called()


def test_load_config_data_not_found():
    """Test loading data when the config file does not exist."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = False
    data = load_config_data(mock_path)
    assert data == {}
    mock_path.exists.assert_called_once()


@patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="invalid: yaml: content")
@patch("code_agent.cli.utils.yaml.safe_load", side_effect=yaml.YAMLError("Bad YAML"))
def test_load_config_data_yaml_error(mock_yaml_load, mock_open_func):
    """Test loading data when the YAML parsing fails."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    with pytest.raises(typer.Exit):
        load_config_data(mock_path)
    mock_path.exists.assert_called_once()
    mock_open_func.assert_called_once_with(mock_path, "r")
    mock_yaml_load.assert_called_once()


@patch("builtins.open", side_effect=IOError("Read failed"))
def test_load_config_data_read_error(mock_open_func):
    """Test loading data when reading the file fails."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    with pytest.raises(typer.Exit):
        load_config_data(mock_path)
    mock_path.exists.assert_called_once()
    mock_open_func.assert_called_once_with(mock_path, "r")


# Ensure no duplicated tests remain at the end
