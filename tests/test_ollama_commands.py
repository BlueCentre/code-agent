import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cli_agent.commands.ollama import app

runner = CliRunner()


def test_list_models_test_mode():
    """Test the list command in test mode."""
    result = runner.invoke(app, ["list", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Ollama Models (Test Mode)" in result.stdout
    assert "llama2:latest" in result.stdout
    assert "mistral:latest" in result.stdout


def test_list_models_test_mode_json():
    """Test the list command in test mode with JSON output."""
    result = runner.invoke(app, ["list", "--test", "--json"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout

    # Find JSON in the output
    json_str = ""
    capture = False
    for line in result.stdout.splitlines():
        if line.strip().startswith("{"):
            capture = True
            json_str += line
        elif capture and line.strip():
            json_str += line
        elif capture and line.strip() == "":
            break

    assert json_str, "No JSON output found"
    try:
        json_data = json.loads(json_str)
        assert "models" in json_data
        assert len(json_data["models"]) >= 2

        # Verify model data
        models = {model["name"]: model for model in json_data["models"]}
        assert "llama2:latest" in models
        assert "mistral:latest" in models
        assert models["llama2:latest"]["details"]["family"] == "Llama"
        assert models["mistral:latest"]["details"]["family"] == "Mistral"
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {json_str}")
        raise


def test_run_prompt_test_mode():
    """Test the run command in test mode."""
    result = runner.invoke(app, ["run", "llama2", "Hello, world!", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Model: llama2" in result.stdout
    assert "Prompt: Hello, world!" in result.stdout
    assert "This is a test response" in result.stdout


def test_run_prompt_test_mode_with_system():
    """Test the run command in test mode with a system prompt."""
    result = runner.invoke(app, ["run", "llama2", "Hello, world!", "--system", "You are a helpful assistant.", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Model: llama2" in result.stdout
    assert "Prompt: Hello, world!" in result.stdout
    assert "System: You are a helpful assistant." in result.stdout
    assert "This is a test response" in result.stdout


def test_chat_with_model_test_mode():
    """Test the chat command in test mode."""
    result = runner.invoke(app, ["chat", "llama2", "Hello, world!", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Model: llama2" in result.stdout
    assert "Prompt: Hello, world!" in result.stdout
    assert "This is a test response" in result.stdout


def test_chat_with_model_test_mode_with_system():
    """Test the chat command in test mode with a system prompt."""
    result = runner.invoke(app, ["chat", "llama2", "Hello, world!", "--system", "You are a helpful assistant.", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Model: llama2" in result.stdout
    assert "Prompt: Hello, world!" in result.stdout
    assert "System: You are a helpful assistant." in result.stdout
    assert "This is a test response" in result.stdout


def test_chat_with_model_test_mode_custom_temperature():
    """Test the chat command in test mode with custom temperature."""
    result = runner.invoke(app, ["chat", "llama2", "Hello, world!", "--temperature", "0.5", "--test"])
    assert result.exit_code == 0
    assert "Running in test mode" in result.stdout
    assert "Model: llama2" in result.stdout
    assert "Prompt: Hello, world!" in result.stdout
    assert "Temperature: 0.5" in result.stdout
    assert "This is a test response" in result.stdout


# Tests for non-test mode with mocks
@patch("cli_agent.commands.ollama.OllamaProvider")
def test_list_models_normal(mock_provider):
    """Test the list command in normal mode."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.list_models.return_value = [
        {"name": "llama2:latest", "details": {"parameter_size": "7B", "family": "Llama", "format": "GGUF", "quantization_level": "Q4_0"}}
    ]

    # Run command
    result = runner.invoke(app, ["list"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once_with("http://localhost:11434")
    mock_instance.list_models.assert_called_once()
    assert "Ollama Models" in result.stdout
    assert "llama2:latest" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_list_models_json(mock_provider):
    """Test the list command in normal mode with JSON output."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.list_models.return_value = [
        {"name": "llama2:latest", "details": {"parameter_size": "7B", "family": "Llama", "format": "GGUF", "quantization_level": "Q4_0"}}
    ]

    # Run command
    result = runner.invoke(app, ["list", "--json"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once_with("http://localhost:11434")
    mock_instance.list_models.assert_called_once()
    assert "llama2:latest" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_list_models_error(mock_provider):
    """Test the list command when an error occurs."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.list_models.side_effect = Exception("Connection error")

    # Run command
    result = runner.invoke(app, ["list"])

    # Check results
    assert result.exit_code == 0  # Typer suppresses exceptions by default
    assert "Error:" in result.stdout
    assert "Connection error" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_run_prompt(mock_provider):
    """Test the run command in normal mode."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.chat_completion.return_value = {"message": {"content": "I'm a helpful AI assistant", "role": "assistant"}, "model": "llama2"}

    # Run command
    result = runner.invoke(app, ["run", "llama2", "Hello, world!"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once_with("http://localhost:11434")
    mock_instance.chat_completion.assert_called_once()
    assert "Response:" in result.stdout
    assert "I'm a helpful AI assistant" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_run_prompt_with_system(mock_provider):
    """Test the run command with system prompt."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.chat_completion.return_value = {"message": {"content": "I'm a helpful AI assistant", "role": "assistant"}, "model": "llama2"}

    # Run command
    result = runner.invoke(app, ["run", "llama2", "Hello, world!", "--system", "You are an assistant"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once()

    # Verify system message was included
    call_args = mock_instance.chat_completion.call_args[0]
    messages = call_args[1]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "You are an assistant"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hello, world!"


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_run_prompt_error(mock_provider):
    """Test the run command when an error occurs."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.chat_completion.side_effect = Exception("Connection error")

    # Run command
    result = runner.invoke(app, ["run", "llama2", "Hello, world!"])

    # Check results
    assert result.exit_code == 0  # Typer suppresses exceptions by default
    assert "Error:" in result.stdout
    assert "Connection error" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_chat_with_model(mock_provider):
    """Test the chat command in normal mode."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.chat_completion.return_value = {"message": {"content": "I'm a helpful AI assistant", "role": "assistant"}, "model": "llama2"}

    # Run command
    result = runner.invoke(app, ["chat", "llama2", "Hello, world!"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once_with("http://localhost:11434")
    mock_instance.chat_completion.assert_called_once()
    assert "Response:" in result.stdout
    assert "I'm a helpful AI assistant" in result.stdout


@patch("cli_agent.commands.ollama.OllamaProvider")
def test_chat_with_custom_temperature(mock_provider):
    """Test the chat command with custom temperature."""
    # Setup mock
    mock_instance = MagicMock()
    mock_provider.return_value = mock_instance
    mock_instance.chat_completion.return_value = {"message": {"content": "I'm a helpful AI assistant", "role": "assistant"}, "model": "llama2"}

    # Run command
    result = runner.invoke(app, ["chat", "llama2", "Hello, world!", "--temperature", "0.5"])

    # Check results
    assert result.exit_code == 0
    mock_provider.assert_called_once()

    # Verify temperature was passed
    call_args = mock_instance.chat_completion.call_args
    assert call_args[1]["temperature"] == 0.5
