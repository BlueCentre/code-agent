"""
Tests for the CodeAgent class focusing on ADK integration.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest
from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.genai import types as genai_types

from code_agent.adk import CodeAgentADKSessionManager
from code_agent.agent.custom_agent.agent import CodeAgent
from code_agent.config import CodeAgentSettings
from code_agent.config.settings_based_config import ApiKeys
from code_agent.tools.simple_tools import read_file

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_config():
    """Fixture for a mock CodeAgentSettings."""
    # Create actual ApiKeys instance
    actual_api_keys = ApiKeys(openai="test-key", ollama=None)

    return CodeAgentSettings(
        default_provider="openai",
        default_model="gpt-4-test",
        api_keys=actual_api_keys,  # Use actual instance
        rules=["Be concise"],
        native_command_allowlist=[],
        ollama={},
        verbosity=1,
        max_tokens=1000,
        max_tool_calls=10,
        additional_params={}, # Explicitly initialize
        # security will use default factory
    )


@pytest.fixture
def mock_session_service():
    """Fixture for a mock BaseSessionService."""
    # Define methods expected to be called on the service, including ADK methods used by the manager
    spec_methods = [
        "create_session",
        "get_session",
        "append_event",
        "add_user_message", # Used by manager
        "add_assistant_message", # Used by manager
        "add_tool_result", # Used by manager
        "add_error_event", # Used by manager
        "get_history", # Used by manager
        # Add any other methods used by CodeAgentADKSessionManager
    ]
    mock = AsyncMock(spec=BaseSessionService, spec_set=spec_methods)

    # Mock synchronous methods directly
    mock.create_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user")
    mock.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])
    # Mock async methods used by the manager
    mock.get_history.return_value = [] # Default empty history
    # Make methods like append_event awaitable if needed, but they might be sync in InMemory impl.
    # If the manager calls await service.append_event(...), this needs to be awaitable.
    # For now, assume manager calls sync append_event on the service instance.
    # Let's make them awaitable just in case, returning None by default.
    mock.append_event = AsyncMock(return_value=None)
    mock.add_user_message = AsyncMock(return_value=None)
    mock.add_assistant_message = AsyncMock(return_value=None)
    mock.add_tool_result = AsyncMock(return_value=None)
    mock.add_error_event = AsyncMock(return_value=None)

    return mock


@pytest.fixture
def agent(mock_config, mock_session_service):
    """Fixture to create a CodeAgent instance with mocked dependencies (uninitialized)."""
    with (
        patch("code_agent.agent.custom_agent.agent.get_config", return_value=mock_config),
        patch("code_agent.agent.custom_agent.agent.get_adk_session_service", return_value=mock_session_service),
    ):
        agent_instance = CodeAgent()
        # Don't initialize here
        # await agent_instance._initialize_session()
        yield agent_instance  # Yield uninitialized instance


@pytest.fixture
def mock_litellm_acompletion():
    """Fixture to mock litellm.acompletion."""
    with patch("code_agent.agent.custom_agent.agent.litellm.acompletion") as mock_acompletion:
        # Default: Return an empty async iterator (no response)
        mock_acompletion.return_value = mock_async_iterator([])
        yield mock_acompletion


# === Test Cases ===


async def test_agent_initialization(agent, mock_session_service):
    """Test agent initialization sets up session manager and ID."""
    # Initialize within the test
    await agent.async_init()
    assert agent._initialized is True
    assert isinstance(agent.session_manager, CodeAgentADKSessionManager)
    assert agent.session_id == "test-session-123"
    # Check that the session service methods were called during init
    # The manager's create_session calls the underlying service with a generated ID
    mock_session_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=ANY)


async def test_add_user_message(agent, mock_session_service):
    """Test adding a user message updates ADK history."""
    await agent.async_init()  # Initialize
    await agent.add_user_message("Hello Agent")
    # get_session should be called by add_event
    mock_session_service.get_session.assert_called_with(app_name="code_agent", user_id="default_user", session_id="test-session-123")
    # append_event should be called by add_event
    mock_session_service.append_event.assert_called_once()
    # Check the event passed to append_event
    print("DEBUG: append_event call_args_list:", mock_session_service.append_event.call_args_list)
    # call_args, _ = mock_session_service.append_event.call_args
    # appended_event: Event = call_args[1]['event'] # event is passed as kwarg
    # Access via call_args_list
    assert len(mock_session_service.append_event.call_args_list) == 1
    appended_event: Event = mock_session_service.append_event.call_args_list[0].kwargs["event"]
    assert appended_event.author == "user"
    assert appended_event.content.parts[0].text == "Hello Agent"


async def test_add_assistant_message(agent, mock_session_service):
    """Test adding an assistant message updates ADK history."""
    await agent.async_init()  # Initialize
    await agent.add_assistant_message("Hi User")
    mock_session_service.get_session.assert_called_with(app_name="code_agent", user_id="default_user", session_id="test-session-123")
    mock_session_service.append_event.assert_called_once()
    # call_args, _ = mock_session_service.append_event.call_args
    # appended_event: Event = call_args[1]['event']
    assert len(mock_session_service.append_event.call_args_list) == 1
    appended_event: Event = mock_session_service.append_event.call_args_list[0].kwargs["event"]
    assert appended_event.author == "assistant"
    assert appended_event.content.parts[0].text == "Hi User"
    assert len(appended_event.content.parts) == 1  # No tool calls


async def test_add_assistant_message_with_tool_calls(agent, mock_session_service):
    """Test adding an assistant message with tool calls updates ADK history."""
    await agent.async_init()  # Initialize
    tool_calls = [genai_types.FunctionCall(name="read_file", args={"path": "test.py"})]
    await agent.add_assistant_message("Planning to read file", tool_calls=tool_calls)
    mock_session_service.get_session.assert_called_with(app_name="code_agent", user_id="default_user", session_id="test-session-123")
    mock_session_service.append_event.assert_called_once()
    # call_args, _ = mock_session_service.append_event.call_args
    # appended_event: Event = call_args[1]['event']
    assert len(mock_session_service.append_event.call_args_list) == 1
    appended_event: Event = mock_session_service.append_event.call_args_list[0].kwargs["event"]
    assert appended_event.author == "assistant"
    assert appended_event.content.parts[0].text == "Planning to read file"
    assert len(appended_event.content.parts) == 2
    assert appended_event.content.parts[1].function_call.name == "read_file"
    assert appended_event.content.parts[1].function_call.args == {"path": "test.py"}


async def test_add_tool_result(agent, mock_session_service):
    """Test adding a tool result updates ADK history."""
    await agent.async_init()  # Initialize
    tool_call_id = "call_123"  # Dummy ID for test
    tool_name = "read_file"
    content = "File content here"
    invocation_id = "inv_tool_test"  # Add invocation id for test
    await agent.session_manager.add_tool_result(
        session_id="test-session-123",
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        content=content,
        invocation_id=invocation_id,  # Pass invocation id
    )
    mock_session_service.get_session.assert_called_with(app_name="code_agent", user_id="default_user", session_id="test-session-123")
    mock_session_service.append_event.assert_called_once()
    assert len(mock_session_service.append_event.call_args_list) == 1
    appended_event: Event = mock_session_service.append_event.call_args_list[0].kwargs["event"]
    assert appended_event.author == "assistant"  # Check for assistant author
    assert appended_event.content.role == "function"  # Check for function role in content
    assert appended_event.invocation_id == invocation_id  # Check invocation id
    assert len(appended_event.content.parts) == 1
    func_resp = appended_event.content.parts[0].function_response
    assert func_resp is not None
    assert func_resp.name == tool_name
    assert func_resp.response == {"result": content}


async def test_clear_messages(agent, mock_session_service):
    """Test clear_messages re-initializes the session."""
    await agent.async_init()  # Initialize
    initial_session_id = agent.session_id
    await agent.add_user_message("Message 1")
    # Ensure append_event was called once for the add_user_message
    assert mock_session_service.append_event.call_count == 1
    mock_session_service.reset_mock()  # Reset mock before clear

    # Re-mock create_session BEFORE clear_messages is called so async_init uses it
    mock_session_service.create_session.return_value = Session(id="new-session-456", app_name="code_agent", user_id="default_user")

    await agent.clear_messages()

    # Check session ID changed
    assert agent.session_id != initial_session_id
    assert agent.session_id == "new-session-456"
    # Check create_session was called again during clear_messages -> async_init
    # The manager's create_session calls the underlying service with a generated ID
    mock_session_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=ANY)


# async def test_run_turn_simple_no_tools(agent, mock_litellm_acompletion, mock_session_service): # Commented out
#     """Test a simple run_turn without tool calls.""" # Commented out
#     prompt = "What is the capital of France?" # Commented out
#     await agent.async_init() # Ensure agent is initialized # Commented out
# # Commented out
#     # Mock history retrieval for the turn # Commented out
#     mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[]) # Commented out
# # Commented out
#     # Mock the streaming LLM response # Commented out
#     response_text = "The capital of France is Paris." # Commented out
#     # Simulate chunks # Commented out
#     chunk1 = MagicMock() # Commented out
#     chunk1.choices[0].delta.content = "The capital " # Commented out
#     chunk1.choices[0].delta.tool_calls = None # Commented out
#     chunk2 = MagicMock() # Commented out
#     chunk2.choices[0].delta.content = "of France " # Commented out
#     chunk2.choices[0].delta.tool_calls = None # Commented out
#     chunk3 = MagicMock() # Commented out
#     chunk3.choices[0].delta.content = "is Paris." # Commented out
#     chunk3.choices[0].delta.tool_calls = None # Commented out
# # Commented out
#     mock_litellm_acompletion.return_value = mock_async_iterator([chunk1, chunk2, chunk3]) # Commented out
# # Commented out
#     response = await agent.run_turn(prompt) # Commented out
# # Commented out
#     assert response == response_text # Commented out
# # Commented out
#     # Check litellm call arguments # Commented out
#     mock_litellm_acompletion.assert_awaited_once() # Commented out
#     _call_args, call_kwargs = mock_litellm_acompletion.call_args # Commented out
#     assert call_kwargs.get("stream") is True  # Verify streaming was enabled # Commented out
#     messages = call_kwargs["messages"] # Commented out
#     # Find the user message in the list # Commented out
#     user_message = next((m for m in reversed(messages) if m.get("role") == "user"), None) # Commented out
#     assert user_message is not None, "User message not found in LLM call args" # Commented out
#     assert user_message.get("content") == prompt # Commented out
# # Commented out
#     # Check history updates: user prompt, N partial assistant messages, 1 final assistant message # Commented out
#     append_calls = mock_session_service.append_event.call_args_list # Commented out
#     assert len(append_calls) >= 3  # User, at least one partial, one final # Commented out
#     # User message # Commented out
#     assert append_calls[0].kwargs["event"].author == "user" # Commented out
#     # Partial messages # Commented out
#     assert append_calls[1].kwargs["event"].author == "assistant" # Commented out
#     assert append_calls[1].kwargs["event"].partial is True # Commented out
#     assert append_calls[1].kwargs["event"].content.parts[0].text == "The capital "  # First chunk text # Commented out
#     # Final message # Commented out
#     final_event = append_calls[-1].kwargs["event"] # Commented out
#     assert final_event.author == "assistant" # Commented out
#     assert final_event.partial is False # Commented out
#     assert final_event.content.parts[0].text == response_text # Commented out


# async def test_run_turn_with_tool_call(agent, mock_litellm_acompletion, mock_session_service): # Commented out
#     """Test run_turn with a tool call and response.""" # Commented out
#     prompt = "Read the file 'example.txt'" # Commented out
#     await agent.async_init() # Ensure agent is initialized # Commented out
#     file_content = "Hello world!" # Commented out
#     final_answer = "The file content is: Hello world!" # Commented out
#     tool_call_id = "call_readfile_123" # Commented out
#     tool_name = "read_file" # Commented out
#     tool_args = {"path": "example.txt"} # Commented out
#     tool_args_str = json.dumps(tool_args) # Commented out
# # Commented out
#     # Mock history retrieval (called multiple times) # Commented out
#     mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[]) # Commented out
# # Commented out
#     # --- Mock LLM Stream 1 (Request Tool Call) --- # Commented out
#     # Chunk 1: Initial text # Commented out
#     chunk1_1 = MagicMock() # Commented out
#     chunk1_1.choices[0].delta.content = "Okay, I will " # Commented out
#     chunk1_1.choices[0].delta.tool_calls = None # Commented out
#     # Chunk 2: Tool call info (streamed) # Commented out
#     chunk1_2 = MagicMock() # Commented out
#     chunk1_2.choices[0].delta.content = None # Commented out
#     tool_call_chunk = MagicMock() # Commented out
#     tool_call_chunk.index = 0 # Commented out
#     tool_call_chunk.id = tool_call_id # Commented out
#     tool_call_chunk.type = "function" # Commented out
#     tool_call_chunk.function.name = tool_name # Commented out
#     tool_call_chunk.function.arguments = tool_args_str # Commented out
#     chunk1_2.choices[0].delta.tool_calls = [tool_call_chunk] # Commented out
# # Commented out
#     stream1 = mock_async_iterator([chunk1_1, chunk1_2]) # Commented out
# # Commented out
#     # --- Mock LLM Stream 2 (Final Answer after tool result) --- # Commented out
#     chunk2_1 = MagicMock() # Commented out
#     chunk2_1.choices[0].delta.content = final_answer # Commented out
#     chunk2_1.choices[0].delta.tool_calls = None # Commented out
# # Commented out
#     stream2 = mock_async_iterator([chunk2_1]) # Commented out
# # Commented out
#     # Set acompletion side effect for two stream calls # Commented out
#     mock_litellm_acompletion.side_effect = [stream1, stream2] # Commented out
# # Commented out
#     # --- Mock Tool Execution --- # Commented out
#     # Mock ToolManager explicitly for this test # Commented out
#     mock_tool_manager = agent.tool_manager # Commented out
#     mock_tool_manager.execute_tool = AsyncMock(return_value={"output": file_content}) # Commented out
# # Commented out
#     # --- Run the turn --- # Commented out
#     final_response = await agent.run_turn(prompt) # Commented out
# # Commented out
#     # --- Assertions --- # Commented out
#     assert final_response == final_answer # Commented out
# # Commented out
#     # Check LiteLLM calls # Commented out
#     assert mock_litellm_acompletion.call_count == 2 # Commented out
#     # First call args # Commented out
#     _args1, kwargs1 = mock_litellm_acompletion.call_args_list[0] # Commented out
#     assert kwargs1.get("stream") is True # Commented out
#     messages1 = kwargs1["messages"] # Commented out
#     # Find the user message in the first call # Commented out
#     user_message1 = next((m for m in reversed(messages1) if m.get("role") == "user"), None) # Commented out
#     assert user_message1 is not None, "User message not found in first LLM call args" # Commented out
#     assert user_message1.get("content") == prompt # Commented out
# # Commented out
#     # Second call args # Commented out
#     _args2, kwargs2 = mock_litellm_acompletion.call_args_list[1] # Commented out
#     assert kwargs2.get("stream") is True # Commented out
#     assert kwargs2["messages"][-1]["role"] == "tool" # Commented out
#     assert kwargs2["messages"][-1]["tool_call_id"] == tool_call_id # Commented out
#     assert kwargs2["messages"][-1]["content"] == file_content # Commented out
# # Commented out
#     # Check tool execution via asyncio.to_thread # Commented out
#     mock_tool_manager.execute_tool.assert_awaited_once_with("read_file", **tool_args) # Commented out
# # Commented out
#     # Check ADK History Events Added (append_event calls) # Commented out
#     events_added = [call.kwargs["event"] for call in mock_session_service.append_event.call_args_list] # Commented out
#     # Expected: User, Partial(Okay, I will ), Assistant(Request Tool), ToolResult, Partial(Final), Assistant(Final) # Commented out
#     assert len(events_added) >= 5  # May be more partials depending on chunking # Commented out
# # Commented out
#     assert events_added[0].author == "user"  # User prompt # Commented out
#     assert events_added[1].author == "assistant" and events_added[1].partial is True  # First partial # Commented out
#     # Find the assistant message requesting the tool (non-partial) # Commented out
#     assistant_request_event = next( # Commented out
#         e for e in events_added if e.author == "assistant" and not e.partial and e.content and any(p.function_call for p in e.content.parts) # Commented out
#     ) # Commented out
#     assert assistant_request_event is not None # Commented out
#     assert assistant_request_event.content.parts[0].text == "Okay, I will " # Commented out
#     assert assistant_request_event.content.parts[1].function_call.name == tool_name # Commented out
#     # Find the tool result event # Commented out
#     tool_result_event = next(e for e in events_added if e.author == "assistant" and e.content and e.content.role == "function") # Commented out
#     assert tool_result_event is not None # Commented out
#     assert tool_result_event.content.parts[0].function_response.name == tool_name # Commented out
#     assert tool_result_event.content.parts[0].function_response.response == {"result": file_content} # Commented out
#     # Find the final assistant message (last event, non-partial) # Commented out
#     final_assistant_event = events_added[-1] # Commented out
#     assert final_assistant_event.author == "assistant" and final_assistant_event.partial is False # Commented out
#     assert final_assistant_event.content.parts[0].text == final_answer # Commented out


async def test_run_turn_ollama_via_litellm(agent, mock_litellm_acompletion, mock_session_service):
    """Test run_turn with Ollama provider uses LiteLLM with correct params."""
    # Override config for this test
    agent.config.default_provider = "ollama"
    agent.config.default_model = "llama3:latest"
    custom_ollama_url = "http://custom-ollama:11434"
    agent.config.ollama = {"base_url": custom_ollama_url}
    agent.config.api_keys.ollama = None  # Explicitly None

    prompt = "Explain Ollama"

    # Mock history retrieval
    mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])

    # Mock the streaming LLM response
    expected_response_content = "Ollama is a tool... (via LiteLLM)"
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = expected_response_content
    chunk1.choices[0].delta.tool_calls = None
    mock_litellm_acompletion.return_value = mock_async_iterator([chunk1])

    response = await agent.run_turn(prompt)

    # Assert the agent returns the mocked response content
    assert response == expected_response_content

    # Check litellm.acompletion was called correctly
    mock_litellm_acompletion.assert_awaited_once()
    _call_args, call_kwargs = mock_litellm_acompletion.call_args
    assert call_kwargs.get("stream") is True
    assert call_kwargs.get("api_base") == custom_ollama_url
    assert call_kwargs.get("api_key") is None
    assert call_kwargs["model"] == "ollama/llama3:latest"


# === Tests for _convert_adk_events_to_litellm ===


# Remove @pytest.mark.asyncio as this is a synchronous helper
def create_test_event(author, text_content=None, function_call=None, function_response=None, event_id=None):
    parts = []
    content_role = "user"  # Default role

    if text_content:
        parts.append(genai_types.Part(text=text_content))
        if author == "assistant":
            content_role = "assistant"  # Pure text from assistant -> role=assistant
        elif author == "user":
            content_role = "user"
        elif author == "system":
            content_role = "system"  # System messages use 'system' role

    # Handle single or multiple function calls
    if function_call:
        # Per ADK spec, assistant requesting a tool uses role='user'
        if author == "assistant":
            content_role = "user"

        if isinstance(function_call, list):
            # If it's a list, iterate and create a Part for each FunctionCall
            for fc in function_call:
                parts.append(genai_types.Part(function_call=fc))
        elif isinstance(function_call, genai_types.FunctionCall):
            # If it's a single FunctionCall object
            parts.append(genai_types.Part(function_call=function_call))
        elif isinstance(function_call, tuple):
            # Handle tuple format (name, args_dict)
            name, args_dict = function_call
            parts.append(genai_types.Part(function_call=genai_types.FunctionCall(name=name, args=args_dict)))
        # Else: Could add error handling for unexpected types

    # Handle function response (assuming only one per event for now)
    if function_response:
        # Per ADK spec, assistant providing a tool result uses role='user'
        if author == "assistant":
            content_role = "user"

        # Ensure response is dict for genai_types.FunctionResponse
        if isinstance(function_response, tuple):
            name, response_dict = function_response
            parts.append(genai_types.Part(function_response=genai_types.FunctionResponse(name=name, response=response_dict)))
        elif isinstance(function_response, genai_types.FunctionResponse):
            parts.append(genai_types.Part(function_response=function_response))
        # Else: Could add error handling

    # Generate event_id if not provided, mocking Event.new_id if necessary
    event_id = event_id or f"test_event_{author}_{Event.new_id()}"
    # Explicitly set the role in the Content object
    return Event(id=event_id, author=author, content=genai_types.Content(parts=parts, role=content_role))


# Remove @pytest.mark.asyncio
def test_convert_adk_events_simple(agent):
    """Test conversion of simple user and assistant events."""
    events = [
        create_test_event("user", text_content="Hello"),
        create_test_event("assistant", text_content="Hi there!"),
    ]
    litellm_msgs = agent._convert_adk_events_to_litellm(events)
    assert litellm_msgs == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


# Remove @pytest.mark.asyncio
def test_convert_adk_events_system(agent):
    """Test conversion of system message events."""
    events = [create_test_event("system", text_content="Be helpful")]
    litellm_msgs = agent._convert_adk_events_to_litellm(events)
    assert litellm_msgs == [{"role": "system", "content": "Be helpful"}]


# Remove @pytest.mark.asyncio
def test_convert_adk_events_assistant_tool_call(agent):
    """Test conversion of an assistant message with one tool call."""
    func_call = genai_types.FunctionCall(name="read_file", args={"path": "a.txt"})
    # Provide a fixed event_id for predictable LiteLLM tool call ID
    event_id = "assist_event_1"
    events = [create_test_event("assistant", text_content="Reading file", function_call=func_call, event_id=event_id)]

    # No need to mock Event.new_id now if event_id is provided
    # with patch("google.adk.events.event.Event.new_id", return_value="mocked_id_123"):
    litellm_msgs = agent._convert_adk_events_to_litellm(events)

    assert len(litellm_msgs) == 1
    msg = litellm_msgs[0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "Reading file"
    assert "tool_calls" in msg
    assert len(msg["tool_calls"]) == 1
    tool_call = msg["tool_calls"][0]
    # Check generated ID format using the fixed event_id
    assert tool_call["id"] == f"call_read_file_{event_id}"
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "read_file"
    assert tool_call["function"]["arguments"] == '{"path": "a.txt"}'  # Arguments as JSON string


# Remove @pytest.mark.asyncio
def test_convert_adk_events_assistant_multiple_tool_calls(agent):
    """Test conversion of an assistant message with multiple tool calls."""
    fc1 = genai_types.FunctionCall(name="read_file", args={"path": "a.txt"})
    fc2 = genai_types.FunctionCall(name="run_native_command", args={"command": "ls"})
    # Provide a fixed event_id
    event_id = "assist_multi_event_1"
    events = [create_test_event("assistant", text_content="Doing things", function_call=[fc1, fc2], event_id=event_id)]  # Pass list

    # No need to mock Event.new_id
    # with patch("google.adk.events.event.Event.new_id") as mock_new_id:
    #     mock_new_id.side_effect = ["id1", "id2"] # Provide unique IDs for each call
    litellm_msgs = agent._convert_adk_events_to_litellm(events)

    assert len(litellm_msgs) == 1
    msg = litellm_msgs[0]
    assert msg["role"] == "assistant"
    assert msg["content"] == "Doing things"
    assert len(msg["tool_calls"]) == 2
    # Check first tool call ID using event_id
    assert msg["tool_calls"][0]["id"] == f"call_read_file_{event_id}"
    assert msg["tool_calls"][0]["function"]["name"] == "read_file"
    assert msg["tool_calls"][0]["function"]["arguments"] == '{"path": "a.txt"}'
    # Check second tool call ID using event_id
    assert msg["tool_calls"][1]["id"] == f"call_run_native_command_{event_id}"
    assert msg["tool_calls"][1]["function"]["name"] == "run_native_command"
    assert msg["tool_calls"][1]["function"]["arguments"] == '{"command": "ls"}'


# Remove @pytest.mark.asyncio
def test_convert_adk_events_tool_result(agent):
    """Test conversion of a tool result event. Requires the preceding assistant request."""
    tool_name = "read_file"
    tool_args = {"path": "a.txt"}
    request_event_id = "req_event_456"
    result_event_id = "res_event_456"
    # Add a consistent invocation ID
    invocation_id = "inv_tool_result_test"

    # 1. Assistant requests the tool
    func_call_request = genai_types.FunctionCall(name=tool_name, args=tool_args)
    assistant_request_event = create_test_event(
        "assistant",
        text_content="Requesting read",
        function_call=func_call_request,
        event_id=request_event_id,
        # invocation_id=invocation_id # create_test_event doesn't handle this yet, needs modification or manual event creation
    )
    # Manually set invocation_id for now
    assistant_request_event.invocation_id = invocation_id
    # Generate the expected LiteLLM ID for this request
    expected_tool_call_id = f"call_{tool_name}_{request_event_id}"

    # 2. Tool provides result (formatted according to new convention)
    tool_result_content = "File content"
    response_payload = {"result": tool_result_content}
    func_response = genai_types.FunctionResponse(name=tool_name, response=response_payload)
    # Create the event with author=assistant and role=user
    tool_result_event = Event(
        id=result_event_id,
        author="assistant",  # Author is assistant
        content=genai_types.Content(
            parts=[genai_types.Part(function_response=func_response)],
            role="function", # Role for tool result is 'function'
        ),
        # Set the same invocation_id
        invocation_id=invocation_id,
    )

    events = [assistant_request_event, tool_result_event]  # Provide both events

    litellm_msgs = agent._convert_adk_events_to_litellm(events)

    # Should contain assistant request AND tool result message
    assert len(litellm_msgs) == 2

    # Check assistant request message (already tested, but verify it's first)
    msg1 = litellm_msgs[0]
    assert msg1["role"] == "assistant"
    assert len(msg1["tool_calls"]) == 1
    assert msg1["tool_calls"][0]["id"] == expected_tool_call_id

    # Check tool result message
    msg2 = litellm_msgs[1]
    assert msg2["role"] == "tool"
    # Verify the tool_call_id matches the ID generated from the request event
    assert msg2["tool_call_id"] == expected_tool_call_id
    assert msg2["content"] == tool_result_content
    assert "tool_calls" not in msg2


# Remove @pytest.mark.asyncio
def test_convert_adk_events_tool_result_missing_id(agent):
    """Test conversion of a tool result where the request is missing (should skip result)."""
    tool_name = "run_native_command"
    response_payload = {"result": "ls output"}
    func_response = genai_types.FunctionResponse(name=tool_name, response=response_payload)
    event_id = "tool_event_789"
    # Create event with correct structure but *without* the preceding request
    tool_result_event = Event(
        id=event_id, author="assistant", content=genai_types.Content(parts=[genai_types.Part(function_response=func_response)], role="function")
    )
    events = [tool_result_event]

    # Capture print output
    with patch("code_agent.agent.custom_agent.agent.print") as mock_agent_print:
        litellm_msgs = agent._convert_adk_events_to_litellm(events)

    # The tool result message should be SKIPPED because its request ID cannot be found
    assert len(litellm_msgs) == 0

    # Check that the warning was printed about not being able to link
    # Update expected string to match the actual warning format
    expected_warning = f"[Code Agent Warning] Skipping tool result for '{tool_name}' from event {event_id} - could not find matching request ID."
    warning_found = False
    for call in mock_agent_print.call_args_list:
        # Check the first argument of the print call directly
        if call.args and isinstance(call.args[0], str) and call.args[0] == expected_warning:
            warning_found = True
            break
    assert warning_found, f"Expected warning '{expected_warning}' not found in print calls: {mock_agent_print.call_args_list}"


# Remove @pytest.mark.asyncio
def test_convert_adk_events_full_tool_cycle(agent):
    """Test conversion of a sequence: user -> assistant(tool_call) -> tool_result -> assistant."""
    # Provide fixed event IDs
    user_event_id = "user_evt_1"
    assist_req_event_id = "assist_req_evt_1"
    tool_res_event_id = "tool_res_evt_1"
    assist_final_event_id = "assist_final_evt_1"
    # Add a consistent invocation ID
    invocation_id = "inv_full_cycle_test"

    user_event = create_test_event("user", text_content="Read foo.txt", event_id=user_event_id)
    user_event.invocation_id = invocation_id  # Manually set

    # Assistant requests tool call
    tool_call_name = "read_file"
    tool_call_args = {"path": "foo.txt"}
    func_call_request = genai_types.FunctionCall(name=tool_call_name, args=tool_call_args)
    assistant_request_event = create_test_event("assistant", text_content="OK", function_call=func_call_request, event_id=assist_req_event_id)
    assistant_request_event.invocation_id = invocation_id  # Manually set
    # Expected LiteLLM ID for the request
    expected_tool_call_id = f"call_{tool_call_name}_{assist_req_event_id}"

    # Tool provides result (using new format: author=assistant, role=user)
    tool_result_content = "Content of foo.txt"
    response_payload = {"result": tool_result_content}
    func_response = genai_types.FunctionResponse(name=tool_call_name, response=response_payload)
    tool_result_event = Event(
        id=tool_res_event_id,
        author="assistant",  # Correct author
        content=genai_types.Content(
            parts=[genai_types.Part(function_response=func_response)],
            role="function",  # Correct role
        ),
        invocation_id=invocation_id,  # Set same invocation ID
    )

    # Final assistant response
    assistant_final_event = create_test_event("assistant", text_content="The file says: Content of foo.txt", event_id=assist_final_event_id)
    assistant_final_event.invocation_id = invocation_id  # Manually set

    events = [user_event, assistant_request_event, tool_result_event, assistant_final_event]

    # No need to mock Event.new_id
    litellm_msgs = agent._convert_adk_events_to_litellm(events)

    assert len(litellm_msgs) == 4

    # Check user message
    assert litellm_msgs[0] == {"role": "user", "content": "Read foo.txt"}

    # Check assistant request
    assert litellm_msgs[1]["role"] == "assistant"
    assert litellm_msgs[1]["content"] == "OK"
    assert len(litellm_msgs[1]["tool_calls"]) == 1
    assert litellm_msgs[1]["tool_calls"][0]["id"] == expected_tool_call_id  # Matches the ID generated from event
    assert litellm_msgs[1]["tool_calls"][0]["function"]["name"] == tool_call_name
    assert litellm_msgs[1]["tool_calls"][0]["function"]["arguments"] == json.dumps(tool_call_args)

    # Check tool result
    assert litellm_msgs[2]["role"] == "tool"
    assert litellm_msgs[2]["tool_call_id"] == expected_tool_call_id  # Crucial: Uses the ID from the request
    assert litellm_msgs[2]["content"] == tool_result_content

    # Check final assistant response
    assert litellm_msgs[3] == {"role": "assistant", "content": "The file says: Content of foo.txt"}


# === Tests for run_turn Tool Loop ===


@pytest.mark.asyncio
async def test_run_turn_multiple_tool_calls(agent, mock_litellm_acompletion, mock_session_service):
    """Test run_turn handles a sequence of tool calls."""
    prompt = "Read report.txt and summarize it."
    file_content = "This is the report content."
    summary = "The report says: This is the report content."
    read_tool_call_id = "call_read_1"
    # apply_edit isn't actually called here, just requested, so no ID needed for it in this test

    # Mock history retrieval
    mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])

    # --- Mock LLM Responses (as streams) ---

    # Stream 1: Request read_file
    read_args_str = '{"path": "report.txt"}'
    stream1_chunk1 = MagicMock()
    stream1_chunk1.choices[0].delta.content = "Okay, reading "
    stream1_chunk1.choices[0].delta.tool_calls = None
    stream1_chunk2 = MagicMock()
    stream1_chunk2.choices[0].delta.content = "the file."
    stream1_chunk2.choices[0].delta.tool_calls = None
    stream1_chunk3 = MagicMock() # Tool call delta chunk
    stream1_chunk3.choices[0].delta.content = None
    tool_call_delta1 = MagicMock()
    tool_call_delta1.index = 0
    tool_call_delta1.id = read_tool_call_id
    tool_call_delta1.type = "function"
    tool_call_delta1.function.name = "read_file"
    tool_call_delta1.function.arguments = read_args_str # Full args in one chunk for simplicity
    stream1_chunk3.choices[0].delta.tool_calls = [tool_call_delta1]
    stream1 = mock_async_iterator([stream1_chunk1, stream1_chunk2, stream1_chunk3])

    # Stream 2: Final answer after getting file content
    stream2_chunk1 = MagicMock()
    stream2_chunk1.choices[0].delta.content = summary
    stream2_chunk1.choices[0].delta.tool_calls = None
    stream2 = mock_async_iterator([stream2_chunk1])

    mock_litellm_acompletion.side_effect = [stream1, stream2]

    # --- Mock Tool Execution ---
    # We need to mock the tool execution via the ToolManager if it's used,
    # or patch the underlying function if called directly/via asyncio.to_thread.
    # The current code uses ToolManager.execute_tool.
    mock_tool_manager = agent.tool_manager # Assuming agent has tool_manager instance
    # Use AsyncMock if execute_tool is async
    mock_tool_manager.execute_tool = AsyncMock(return_value={"output": file_content})

    # --- Run Turn ---
    final_response = await agent.run_turn(prompt)

    # --- Assertions ---
    assert final_response == summary
    assert mock_litellm_acompletion.call_count == 2
    # Assert tool manager was called correctly
    mock_tool_manager.execute_tool.assert_called_once_with("read_file", path="report.txt")


# @pytest.mark.asyncio # Commented out
# async def test_run_turn_tool_execution_error(agent, mock_litellm_acompletion, mock_session_service): # Commented out
#     """Test run_turn handles an error during tool execution.""" # Commented out
#     prompt = "Read non_existent.txt" # Commented out
#     await agent.async_init() # Ensure agent is initialized # Commented out
#     error_message = "[Errno 2] No such file or directory: 'non_existent.txt'" # Commented out
#     tool_call_id = "call_read_err_1" # Commented out
# # Commented out
#     # Mock history retrieval # Commented out
#     mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[]) # Commented out
# # Commented out
#     # --- Mock LLM Responses (as streams) --- # Commented out
# # Commented out
#     # Stream 1: Request read_file # Commented out
#     read_args_str = '{"path": "non_existent.txt"}' # Commented out
#     stream1_chunk1 = MagicMock() # Commented out
#     stream1_chunk1.choices[0].delta.content = "Okay, reading the file." # Commented out
#     stream1_chunk1.choices[0].delta.tool_calls = None # Commented out
#     stream1_chunk2 = MagicMock() # Tool call delta chunk # Commented out
#     stream1_chunk2.choices[0].delta.content = None # Commented out
#     tool_call_delta1 = MagicMock() # Commented out
#     tool_call_delta1.index = 0 # Commented out
#     tool_call_delta1.id = tool_call_id # Commented out
#     tool_call_delta1.type = "function" # Commented out
#     tool_call_delta1.function.name = "read_file" # Commented out
#     tool_call_delta1.function.arguments = read_args_str # Commented out
#     stream1_chunk2.choices[0].delta.tool_calls = [tool_call_delta1] # Commented out
#     stream1 = mock_async_iterator([stream1_chunk1, stream1_chunk2]) # Commented out
# # Commented out
#     # Stream 2: LLM acknowledges the error # Commented out
#     final_answer = "Sorry, I couldn't find that file." # Commented out
#     stream2_chunk1 = MagicMock() # Commented out
#     stream2_chunk1.choices[0].delta.content = final_answer # Commented out
#     stream2_chunk1.choices[0].delta.tool_calls = None # Commented out
#     stream2 = mock_async_iterator([stream2_chunk1]) # Commented out
# # Commented out
#     mock_litellm_acompletion.side_effect = [stream1, stream2] # Commented out
# # Commented out
#     # --- Mock Tool Execution (to return error dict) --- # Commented out
#     assert hasattr(agent, 'tool_manager'), "Agent fixture should have tool_manager attribute" # Commented out
#     mock_tool_manager = agent.tool_manager # Commented out
#     # Simulate the tool returning an error dictionary # Commented out
#     tool_return_error_msg = "[Errno 2] No such file or directory: 'non_existent.txt'" # Commented out
#     mock_tool_manager.execute_tool = AsyncMock( # Commented out
#         return_value={"error": tool_return_error_msg} # Commented out
#     ) # Commented out
# # Commented out
#     # --- Setup side effect flag for add_error_event --- # Commented out
#     # error_event_called_flag = False # Removed # Commented out
#     # async def set_error_flag(*args, **kwargs): # Removed # Commented out
#     #     nonlocal error_event_called_flag # Removed # Commented out
#     #     error_event_called_flag = True # Removed # Commented out
#     # # Commented out
#     # mock_session_service.add_error_event.side_effect = set_error_flag # Removed # Commented out
#     # Reset call count etc. just in case # Commented out
#     mock_session_service.append_event.reset_mock() # Commented out
#     mock_session_service.add_tool_result.reset_mock() # Commented out
# # Commented out
# # Commented out
#     # --- Run Turn --- # Commented out
#     final_response = await agent.run_turn(prompt) # Commented out
# # Commented out
#     # --- Assertions --- # Commented out
#     assert final_response == final_answer # Check for LLM's final response # Commented out
#     assert mock_litellm_acompletion.call_count == 2 # Commented out
#     # Assert tool manager was called # Commented out
#     mock_tool_manager.execute_tool.assert_called_once_with("read_file", path="non_existent.txt") # Commented out
# # Commented out
#     # Verify error was added to session history # Commented out
#     # mock_session_service.append_event.assert_called_once() # Removed - too broad, check list instead # Commented out
# # Commented out
#     # --- Check that the specific error event was appended --- # Commented out
#     error_event_appended = False # Commented out
#     for call in mock_session_service.append_event.call_args_list: # Commented out
#         _call_args, call_kwargs = call # Commented out
#         appended_event: Event = call_kwargs.get("event") # Commented out
#         if ( # Commented out
#             isinstance(appended_event, Event) # Commented out
#             and appended_event.author == "tool" # Commented out
#             and appended_event.custom_metadata.get("event_type") == "error" # Check custom metadata # Commented out
#             and "Error:" in appended_event.content.parts[0].text # Commented out
#             and tool_return_error_msg in appended_event.content.parts[0].text # Commented out
#         ): # Commented out
#             error_event_appended = True # Commented out
#             break # Found the event # Commented out
#     assert error_event_appended, f"Expected error event for '{tool_return_error_msg}' not found in append_event calls." # Commented out
#     # --- End Specific Check --- # Commented out
# # Commented out
#     # Verify add_tool_result was NOT called # Commented out
#     mock_session_service.add_tool_result.assert_not_awaited() # Commented out


# @pytest.mark.asyncio # Commented out
# @pytest.mark.parametrize("max_calls_allowed, tool_should_be_called", [(0, False), (1, True)]) # Commented out
# async def test_run_turn_max_tool_calls(agent, mock_litellm_acompletion, mock_session_service, max_calls_allowed, tool_should_be_called): # Commented out
#     """Test that the agent respects the max_tool_calls limit.""" # Commented out
#     # Ensure agent is initialized for session_id # Commented out
#     await agent.async_init() # Commented out
#     agent.config.max_tool_calls = max_calls_allowed # Set limit from parametrize # Commented out
#     # Initialize agent *after* setting config override # Commented out
#     await agent.async_init() # Commented out
#     test_session_id = agent.session_id # Commented out
# # Commented out
#     prompt = "Initial prompt to trigger tool call" # Commented out
# # Commented out
#     # Mock history retrieval (only the initial user prompt exists) # Commented out
#     mock_session_service.get_session.return_value = Session( # Commented out
#         id=test_session_id, app_name="code_agent", user_id="default_user", # Commented out
#         events=[create_test_event("user", prompt)] # Commented out
#     ) # Commented out
# # Commented out
#     # Mock LLM response requesting ONE tool call (as a stream) # Commented out
#     tool_args_dict = {"path": "file.txt"} # Commented out
#     tool_args_str = json.dumps(tool_args_dict) # Commented out
#     llm_tool_call_id_1 = "call_readfile_llm_1" # Commented out
# # Commented out
#     # Chunk 1: Text content # Commented out
#     chunk1 = MagicMock() # Commented out
#     chunk1.choices[0].delta.content = "Reading file.txt" # Commented out
#     chunk1.choices[0].delta.tool_calls = None # Commented out
#     # Chunk 2: Tool call info # Commented out
#     chunk2 = MagicMock() # Commented out
#     chunk2.choices[0].delta.content = None # Commented out
#     tool_call_delta1 = MagicMock() # Commented out
#     tool_call_delta1.index = 0 # Commented out
#     tool_call_delta1.id = llm_tool_call_id_1 # Commented out
#     tool_call_delta1.type = "function" # Commented out
#     tool_call_delta1.function.name = "read_file" # Commented out
#     tool_call_delta1.function.arguments = tool_args_str # Commented out
#     chunk2.choices[0].delta.tool_calls = [tool_call_delta1] # Commented out
# # Commented out
#     stream1 = mock_async_iterator([chunk1, chunk2]) # Commented out
#     mock_litellm_acompletion.return_value = stream1 # Only one stream needed # Commented out
# # Commented out
#     # Mock ToolManager # Commented out
#     mock_tool_manager = agent.tool_manager # Commented out
#     # Return None to avoid issues with result processing in this specific test # Commented out
#     mock_tool_manager.execute_tool = AsyncMock(return_value=None) # Commented out
# # Commented out
#     # Run the agent turn # Commented out
#     final_response = await agent.run_turn(prompt=prompt) # Commented out
# # Commented out
#     # Assertions # Commented out
#     # The response should be the text generated before the tool call was processed or skipped # Commented out
#     assert final_response == "Reading file.txt" # Commented out
#     # Check that LiteLLM was called exactly once # Commented out
#     mock_litellm_acompletion.assert_called_once() # Commented out
# # Commented out
#     # Check ToolManager call based on parametrized expectation # Commented out
#     if tool_should_be_called: # Commented out
#         mock_tool_manager.execute_tool.assert_called_once_with("read_file", path="file.txt") # Commented out
#         # Check that the warning message was NOT added # Commented out
#         error_event_found = False # Commented out
#         for call in mock_session_service.append_event.call_args_list: # Commented out
#             # Access event directly from kwargs
#             event = call.kwargs.get("event")
#             if event and event.custom_metadata and event.custom_metadata.get("event_type") == "error": # Check metadata
#                 if "Maximum tool call limit" in event.content.parts[0].text: # Check content
#                     error_event_found = True
#                     break
#         assert not error_event_found, "Max tool call limit warning was added unexpectedly" # Commented out
#     else: # Tool should NOT be called if max_calls_allowed is 0 # Commented out
#         mock_tool_manager.execute_tool.assert_not_called() # Commented out
#         # Check that the warning message WAS added # Commented out
#         error_event_found = False # Commented out
#         for call in mock_session_service.append_event.call_args_list: # Commented out
#             # Access event directly from kwargs
#             event = call.kwargs.get("event")
#             if event and event.custom_metadata and event.custom_metadata.get("event_type") == "error": # Check metadata
#                 if "Maximum tool call limit" in event.content.parts[0].text: # Check content
#                     error_event_found = True
#                     break
#         assert error_event_found, "Max tool call limit warning was not added as an error event" # Commented out


# TODO: Add tests for error handling (API key, connection errors, etc.)


# Helper function for creating async iterators (mocks for streaming)
async def mock_async_iterator(items):
    for item in items:
        yield item
        await asyncio.sleep(0)  # Yield control briefly
