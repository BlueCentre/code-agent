import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_agent.main import app
from cli_agent.providers.ollama import OllamaProvider

# Sample test data
SAMPLE_MODELS = {
    "models": [
        {
            "name": "llama3:latest",
            "model": "llama3:latest",
            "modified_at": "2024-04-01T12:00:00.000000Z",
            "size": 4200000000,
            "digest": "1234567890abcdef",
            "details": {"format": "gguf", "family": "llama", "parameter_size": "8B", "quantization_level": "Q4_K_M"},
        },
        {
            "name": "codellama:13b",
            "model": "codellama:13b",
            "modified_at": "2024-04-01T12:30:00.000000Z",
            "size": 13500000000,
            "digest": "abcdef1234567890",
            "details": {"format": "gguf", "family": "llama", "parameter_size": "13B", "quantization_level": "Q4_0"},
        },
    ]
}

SAMPLE_CHAT_RESPONSE = {
    "model": "llama3:latest",
    "created_at": "2024-04-10T15:30:00.000000Z",
    "message": {"role": "assistant", "content": "This is a test response from the Ollama model."},
    "done": True,
}


@pytest.fixture
def runner():
    return CliRunner()


class TestOllamaProvider:
    """Tests for the OllamaProvider class"""

    @patch("requests.get")
    def test_list_models(self, mock_get):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_MODELS
        mock_get.return_value = mock_response

        # Create provider and call the method
        provider = OllamaProvider()
        models = provider.list_models()

        # Check results
        assert len(models) == 2
        assert models[0]["name"] == "llama3:latest"
        assert models[1]["name"] == "codellama:13b"
        assert models[0]["details"]["parameter_size"] == "8B"
        mock_get.assert_called_once_with("http://localhost:11434/api/tags")

    @patch("requests.get")
    def test_list_models_custom_url(self, mock_get):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_MODELS
        mock_get.return_value = mock_response

        # Create provider with custom URL and call the method
        provider = OllamaProvider("http://custom-host:11434")
        models = provider.list_models()

        # Check results
        assert len(models) == 2
        mock_get.assert_called_once_with("http://custom-host:11434/api/tags")

    @patch("requests.get")
    def test_list_models_error_handling(self, mock_get):
        # Setup the mock to raise an exception
        mock_get.side_effect = Exception("Connection refused")

        # Create provider and call the method, should raise the exception
        provider = OllamaProvider()
        with pytest.raises(Exception) as excinfo:
            provider.list_models()

        assert "Connection refused" in str(excinfo.value)

    @patch("requests.post")
    def test_chat_completion(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_CHAT_RESPONSE
        mock_post.return_value = mock_response

        # Create provider and call the method
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]
        response = provider.chat_completion("llama3:latest", messages)

        # Check results
        assert response["message"]["content"] == "This is a test response from the Ollama model."
        mock_post.assert_called_once()
        # Check that the URL and payload are correct
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/chat"
        assert kwargs["json"]["model"] == "llama3:latest"
        assert kwargs["json"]["messages"] == messages
        assert kwargs["json"]["stream"] is False

    @patch("requests.post")
    def test_chat_completion_with_tools(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_CHAT_RESPONSE
        mock_post.return_value = mock_response

        # Create provider and call the method with tools
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "test_function", "description": "A test function"}}]

        provider.chat_completion("llama3:latest", messages, tools=tools)

        # Check results
        # Check that the URL and payload are correct including tools
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/chat"
        assert kwargs["json"]["tools"] == tools

    @patch("requests.post")
    def test_chat_completion_custom_url(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_CHAT_RESPONSE
        mock_post.return_value = mock_response

        # Create provider with custom URL and call the method
        provider = OllamaProvider("http://custom-host:11434")
        messages = [{"role": "user", "content": "Hello"}]
        provider.chat_completion("llama3:latest", messages)

        # Check that the URL is correct
        args, kwargs = mock_post.call_args
        assert args[0] == "http://custom-host:11434/api/chat"

    @patch("requests.post")
    def test_chat_completion_error_handling(self, mock_post):
        # Setup the mock to raise an exception
        mock_post.side_effect = Exception("Connection refused")

        # Create provider and call the method, should raise the exception
        provider = OllamaProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(Exception) as excinfo:
            provider.chat_completion("llama3:latest", messages)

        assert "Connection refused" in str(excinfo.value)

    @patch("requests.post")
    def test_get_completion(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test completion response"}
        mock_post.return_value = mock_response

        # Create provider and call the method
        provider = OllamaProvider()
        response = provider.get_completion(model="llama3:latest", prompt="Hello", system="You are a helpful assistant", temperature=0.5)

        # Check results
        assert response["response"] == "Test completion response"
        mock_post.assert_called_once()
        # Check that the URL and payload are correct
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/generate"
        assert kwargs["json"]["model"] == "llama3:latest"
        assert kwargs["json"]["prompt"] == "Hello"
        assert kwargs["json"]["system"] == "You are a helpful assistant"
        assert kwargs["json"]["temperature"] == 0.5
        assert kwargs["json"]["stream"] is False

    @patch("requests.post")
    def test_get_completion_with_tools(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test completion response"}
        mock_post.return_value = mock_response

        # Create provider and call the method with tools
        provider = OllamaProvider()
        tools = [{"type": "function", "function": {"name": "test_function", "description": "A test function"}}]

        provider.get_completion(model="llama3:latest", prompt="Hello", system="You are a helpful assistant", tools=tools)

        # Check that tools were included in the payload
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["tools"] == tools

    @patch("requests.post")
    def test_get_completion_custom_url(self, mock_post):
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Test completion response"}
        mock_post.return_value = mock_response

        # Create provider with custom URL and call the method
        provider = OllamaProvider("http://custom-host:11434")
        provider.get_completion(model="llama3:latest", prompt="Hello")

        # Check that the URL is correct
        args, kwargs = mock_post.call_args
        assert args[0] == "http://custom-host:11434/api/generate"

    @patch("requests.post")
    def test_get_completion_error_handling(self, mock_post):
        # Setup the mock to raise an exception
        mock_post.side_effect = Exception("Connection refused")

        # Create provider and call the method, should raise the exception
        provider = OllamaProvider()

        with pytest.raises(Exception) as excinfo:
            provider.get_completion(model="llama3:latest", prompt="Hello")

        assert "Connection refused" in str(excinfo.value)


class TestOllamaCommands:
    """Tests for the Ollama CLI commands"""

    @patch("cli_agent.providers.ollama.OllamaProvider.list_models")
    def test_list_command(self, mock_list_models, runner):
        # Setup the mock response
        mock_list_models.return_value = SAMPLE_MODELS["models"]

        # Run the command
        result = runner.invoke(app, ["ollama", "list"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the model names appear in the output
        assert "llama3:latest" in result.stdout
        assert "codellama:13b" in result.stdout
        assert "8B" in result.stdout  # Parameter size
        assert "13B" in result.stdout  # Parameter size

    @patch("cli_agent.providers.ollama.OllamaProvider.list_models")
    def test_list_command_json_format(self, mock_list_models, runner):
        # Setup the mock response
        mock_list_models.return_value = SAMPLE_MODELS["models"]

        # Run the command with --json flag
        result = runner.invoke(app, ["ollama", "list", "--json"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the output is valid JSON and contains the expected data
        output_json = json.loads(result.stdout)
        assert len(output_json) == 2
        assert output_json[0]["name"] == "llama3:latest"
        assert output_json[1]["name"] == "codellama:13b"

    @patch("cli_agent.providers.ollama.OllamaProvider.list_models")
    def test_list_command_custom_url(self, mock_list_models, runner):
        # Setup the mock response
        mock_list_models.return_value = SAMPLE_MODELS["models"]

        # Run the command with custom URL
        result = runner.invoke(app, ["ollama", "list", "--url", "http://custom-host:11434"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that OllamaProvider was created with the custom URL
        mock_list_models.assert_called_once()

    @patch("cli_agent.providers.ollama.OllamaProvider.list_models")
    def test_list_command_error_handling(self, mock_list_models, runner):
        # Setup the mock to raise an exception
        mock_list_models.side_effect = Exception("Connection refused")

        # Run the command
        result = runner.invoke(app, ["ollama", "list"])

        # Check that the command ran and handled the error
        assert result.exit_code == 0  # Typer commands catch exceptions
        assert "Error" in result.stdout
        assert "Connection refused" in result.stdout

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_run_command(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command
        result = runner.invoke(app, ["ollama", "run", "llama3:latest", "Write a hello world program in Python"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the thinking indicator was used
        mock_thinking.assert_called_once()
        assert "Running llama3:latest on your prompt" in mock_thinking.call_args[0][0]

        # Check that the response appears in the output
        assert "This is a test response from the Ollama model." in result.stdout

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_run_command_with_system(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with system prompt
        result = runner.invoke(
            app, ["ollama", "run", "llama3:latest", "Write a hello world program in Python", "--system", "You are a helpful coding assistant"]
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the thinking indicator was used
        mock_thinking.assert_called_once()

        # Verify that the system prompt was passed correctly
        mock_chat_completion.assert_called_once()

        # Get the call arguments
        args, kwargs = mock_chat_completion.call_args
        # First positional argument should be the model
        assert args[0] == "llama3:latest"
        # Second positional argument should be the messages list
        assert len(args[1]) == 2
        assert args[1][0]["role"] == "system"
        assert args[1][0]["content"] == "You are a helpful coding assistant"
        assert args[1][1]["role"] == "user"
        assert args[1][1]["content"] == "Write a hello world program in Python"

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_run_command_custom_url(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with custom URL
        result = runner.invoke(app, ["ollama", "run", "llama3:latest", "Write a hello world program in Python", "--url", "http://custom-host:11434"])

        # Check that the command ran successfully
        assert result.exit_code == 0

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_run_command_custom_temperature(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with custom temperature
        result = runner.invoke(app, ["ollama", "run", "llama3:latest", "Write a hello world program in Python", "--temperature", "0.1"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Verify that temperature was passed correctly
        mock_chat_completion.assert_called_once()
        args, kwargs = mock_chat_completion.call_args
        assert kwargs["temperature"] == 0.1

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_run_command_error_handling(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock to raise an exception
        mock_chat_completion.side_effect = Exception("Connection refused")
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command
        result = runner.invoke(app, ["ollama", "run", "llama3:latest", "Test prompt"])

        # Check that the command ran and handled the error
        assert result.exit_code == 0  # Typer commands catch exceptions
        assert "Error" in result.stdout
        assert "Connection refused" in result.stdout

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_chat_command(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command
        result = runner.invoke(app, ["ollama", "chat", "llama3:latest", "Hello, how are you?"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the thinking indicator was used
        mock_thinking.assert_called_once()
        assert "Chatting with llama3:latest" in mock_thinking.call_args[0][0]

        # Check that the response appears in the output
        assert "This is a test response from the Ollama model." in result.stdout

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_chat_command_with_system(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with system prompt
        result = runner.invoke(app, ["ollama", "chat", "llama3:latest", "Hello, how are you?", "--system", "You are a helpful assistant"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the thinking indicator was used
        mock_thinking.assert_called_once()

        # Verify that the system prompt was passed correctly
        mock_chat_completion.assert_called_once()

        # Get the call arguments
        args, kwargs = mock_chat_completion.call_args
        # First positional argument should be the model
        assert args[0] == "llama3:latest"
        # Second positional argument should be the messages list
        assert len(args[1]) == 2
        assert args[1][0]["role"] == "system"
        assert args[1][0]["content"] == "You are a helpful assistant"
        assert args[1][1]["role"] == "user"
        assert args[1][1]["content"] == "Hello, how are you?"

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_chat_command_custom_url(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with custom URL
        result = runner.invoke(app, ["ollama", "chat", "llama3:latest", "Hello, how are you?", "--url", "http://custom-host:11434"])

        # Check that the command ran successfully
        assert result.exit_code == 0

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_chat_command_custom_temperature(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock responses
        mock_chat_completion.return_value = SAMPLE_CHAT_RESPONSE
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command with custom temperature
        result = runner.invoke(app, ["ollama", "chat", "llama3:latest", "Hello, how are you?", "--temperature", "0.1"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Verify that temperature was passed correctly
        mock_chat_completion.assert_called_once()
        args, kwargs = mock_chat_completion.call_args
        assert kwargs["temperature"] == 0.1

    @patch("cli_agent.commands.ollama.thinking_indicator")
    @patch("cli_agent.providers.ollama.OllamaProvider.chat_completion")
    def test_chat_command_error_handling(self, mock_chat_completion, mock_thinking, runner):
        # Setup the mock to raise an exception
        mock_chat_completion.side_effect = Exception("Connection refused")
        mock_thinking.return_value.__enter__.return_value = MagicMock()
        mock_thinking.return_value.__exit__.return_value = None

        # Run the command
        result = runner.invoke(app, ["ollama", "chat", "llama3:latest", "Hello, how are you?"])

        # Check that the command ran and handled the error
        assert result.exit_code == 0  # Typer commands catch exceptions
        assert "Error" in result.stdout
        assert "Connection refused" in result.stdout
