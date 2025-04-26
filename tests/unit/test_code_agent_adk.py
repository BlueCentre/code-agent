"""
Tests for the CodeAgent class focusing on ADK integration.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

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
        # security will use default factory
    )


@pytest.fixture
def mock_session_service():
    """Fixture for a mock BaseSessionService."""
    mock = AsyncMock(spec=BaseSessionService)
    # Mock synchronous methods directly
    mock.create_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user")
    mock.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])
    # append_event doesn't need specific return value unless checked
    mock.append_event = MagicMock()
    return mock


@pytest.fixture
def agent(mock_config, mock_session_service):
    """Fixture to create a CodeAgent instance with mocked dependencies (uninitialized)."""
    with (
        patch("code_agent.agent.agent.get_config", return_value=mock_config),
        patch("code_agent.agent.agent.get_adk_session_service", return_value=mock_session_service),
    ):
        agent_instance = CodeAgent()
        # Don't initialize here
        # await agent_instance._initialize_session()
        yield agent_instance  # Yield uninitialized instance


@pytest.fixture
def mock_litellm_acompletion():
    """Fixture to mock litellm.acompletion."""
    with patch("code_agent.agent.agent.litellm.acompletion") as mock_acompletion:
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
    mock_session_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user")


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
    assert appended_event.content.role == "user"  # Check for user role in content
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
    mock_session_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user")


async def test_run_turn_simple_no_tools(agent, mock_litellm_acompletion, mock_session_service):
    """Test a simple run_turn without tool calls."""
    prompt = "What is the capital of France?"

    # Mock history retrieval for the turn
    mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])

    # Mock the streaming LLM response
    response_text = "The capital of France is Paris."
    # Simulate chunks
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = "The capital "
    chunk1.choices[0].delta.tool_calls = None
    chunk2 = MagicMock()
    chunk2.choices[0].delta.content = "of France "
    chunk2.choices[0].delta.tool_calls = None
    chunk3 = MagicMock()
    chunk3.choices[0].delta.content = "is Paris."
    chunk3.choices[0].delta.tool_calls = None

    mock_litellm_acompletion.return_value = mock_async_iterator([chunk1, chunk2, chunk3])

    response = await agent.run_turn(prompt)

    assert response == response_text

    # Check litellm call arguments
    mock_litellm_acompletion.assert_awaited_once()
    _call_args, call_kwargs = mock_litellm_acompletion.call_args
    assert call_kwargs.get("stream") is True  # Verify streaming was enabled
    messages = call_kwargs["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == prompt
    assert call_kwargs["model"] == "gpt-4-test"

    # Check history updates: user prompt, N partial assistant messages, 1 final assistant message
    append_calls = mock_session_service.append_event.call_args_list
    assert len(append_calls) >= 3  # User, at least one partial, one final
    # User message
    assert append_calls[0].kwargs["event"].author == "user"
    # Partial messages
    assert append_calls[1].kwargs["event"].author == "assistant"
    assert append_calls[1].kwargs["event"].partial is True
    assert append_calls[1].kwargs["event"].content.parts[0].text == "The capital "  # First chunk text
    # Final message
    final_event = append_calls[-1].kwargs["event"]
    assert final_event.author == "assistant"
    assert final_event.partial is False
    assert final_event.content.parts[0].text == response_text


async def test_run_turn_with_tool_call(agent, mock_litellm_acompletion, mock_session_service):
    """Test run_turn with a tool call and response."""
    prompt = "Read the file 'example.txt'"
    file_content = "Hello world!"
    final_answer = "The file content is: Hello world!"
    tool_call_id = "call_readfile_123"
    tool_name = "read_file"
    tool_args = {"path": "example.txt"}
    tool_args_str = json.dumps(tool_args)

    # Mock history retrieval (called multiple times)
    mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])

    # --- Mock LLM Stream 1 (Request Tool Call) ---
    # Chunk 1: Initial text
    chunk1_1 = MagicMock()
    chunk1_1.choices[0].delta.content = "Okay, I will "
    chunk1_1.choices[0].delta.tool_calls = None
    # Chunk 2: Tool call info (streamed)
    chunk1_2 = MagicMock()
    chunk1_2.choices[0].delta.content = None
    tool_call_chunk = MagicMock()
    tool_call_chunk.index = 0
    tool_call_chunk.id = tool_call_id
    tool_call_chunk.type = "function"
    tool_call_chunk.function.name = tool_name
    tool_call_chunk.function.arguments = tool_args_str
    chunk1_2.choices[0].delta.tool_calls = [tool_call_chunk]

    stream1 = mock_async_iterator([chunk1_1, chunk1_2])

    # --- Mock LLM Stream 2 (Final Answer after tool result) ---
    chunk2_1 = MagicMock()
    chunk2_1.choices[0].delta.content = final_answer
    chunk2_1.choices[0].delta.tool_calls = None

    stream2 = mock_async_iterator([chunk2_1])

    # Set acompletion side effect for two stream calls
    mock_litellm_acompletion.side_effect = [stream1, stream2]

    # --- Mock Tool Execution ---
    with patch("asyncio.to_thread") as mock_to_thread:
        mock_to_thread.return_value = file_content

        # --- Run the turn ---
        final_response = await agent.run_turn(prompt)

    # --- Assertions ---
    assert final_response == final_answer

    # Check LiteLLM calls
    assert mock_litellm_acompletion.call_count == 2
    # First call args
    _args1, kwargs1 = mock_litellm_acompletion.call_args_list[0]
    assert kwargs1.get("stream") is True
    assert kwargs1["messages"][-1]["role"] == "user"
    assert kwargs1["messages"][-1]["content"] == prompt
    # Second call args
    _args2, kwargs2 = mock_litellm_acompletion.call_args_list[1]
    assert kwargs2.get("stream") is True
    assert kwargs2["messages"][-1]["role"] == "tool"
    assert kwargs2["messages"][-1]["tool_call_id"] == tool_call_id
    assert kwargs2["messages"][-1]["content"] == file_content

    # Check tool execution via asyncio.to_thread
    mock_to_thread.assert_awaited_once_with(read_file, **tool_args)

    # Check ADK History Events Added (append_event calls)
    events_added = [call.kwargs["event"] for call in mock_session_service.append_event.call_args_list]
    # Expected: User, Partial(Okay, I will ), Assistant(Request Tool), ToolResult, Partial(Final), Assistant(Final)
    assert len(events_added) >= 5  # May be more partials depending on chunking

    assert events_added[0].author == "user"  # User prompt
    assert events_added[1].author == "assistant" and events_added[1].partial is True  # First partial
    # Find the assistant message requesting the tool (non-partial)
    assistant_request_event = next(
        e for e in events_added if e.author == "assistant" and not e.partial and e.content and any(p.function_call for p in e.content.parts)
    )
    assert assistant_request_event is not None
    assert assistant_request_event.content.parts[0].text == "Okay, I will "
    assert assistant_request_event.content.parts[1].function_call.name == tool_name
    # Find the tool result event
    tool_result_event = next(e for e in events_added if e.author == "assistant" and e.content and e.content.role == "user")
    assert tool_result_event is not None
    assert tool_result_event.content.parts[0].function_response.name == tool_name
    assert tool_result_event.content.parts[0].function_response.response == {"result": file_content}
    # Find the final assistant message (last event, non-partial)
    final_assistant_event = events_added[-1]
    assert final_assistant_event.author == "assistant" and final_assistant_event.partial is False
    assert final_assistant_event.content.parts[0].text == final_answer


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
            role="user",  # Role is user
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
        id=event_id, author="assistant", content=genai_types.Content(parts=[genai_types.Part(function_response=func_response)], role="user")
    )
    events = [tool_result_event]

    # Capture print output
    with patch("code_agent.agent.agent.print") as mock_agent_print:
        litellm_msgs = agent._convert_adk_events_to_litellm(events)

    # The tool result message should be SKIPPED because its request ID cannot be found
    assert len(litellm_msgs) == 0

    # Check that the warning was printed about not being able to link
    # Update expected string to match the actual warning format
    expected_warning_substring = (
        f"Warning: Could not link tool result for '{tool_name}' (Invocation: {tool_result_event.invocation_id or ''}) to a corresponding tool request. Skipping event in conversion."
        # f"Warning: Could not link tool result {tool_name} in event {event_id} to a request"
    )
    warning_found = False
    for call in mock_agent_print.call_args_list:
        # Check the first argument of the print call directly
        if call.args and isinstance(call.args[0], str) and expected_warning_substring in call.args[0]:
            warning_found = True
            break
    assert warning_found, f"Expected warning containing '{expected_warning_substring}' not found in print calls: {mock_agent_print.call_args_list}"


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
            role="user",  # Correct role
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

    # --- Mock LLM Responses ---
    # 1. Request read_file
    read_call = MagicMock()
    read_call.id = read_tool_call_id
    read_call.type = "function"
    read_call.function.name = "read_file"
    read_call.function.arguments = '{"path": "report.txt"}'
    mock_message1 = MagicMock()
    mock_message1.content = "Okay, reading the file."
    mock_message1.tool_calls = [read_call]
    mock_choice1 = MagicMock()
    mock_choice1.message = mock_message1
    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]

    # 2. Final answer after getting file content
    mock_message2 = MagicMock()
    mock_message2.content = summary
    mock_message2.tool_calls = None
    mock_choice2 = MagicMock()
    mock_choice2.message = mock_message2
    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]

    mock_litellm_acompletion.side_effect = [mock_response1, mock_response2]

    # --- Mock Tool Execution ---
    with patch("asyncio.to_thread") as mock_to_thread:
        # Mock the return value of read_file when called via to_thread
        mock_to_thread.return_value = file_content

        # --- Run Turn ---
        final_response = await agent.run_turn(prompt)

    # --- Assertions ---
    assert final_response == summary

    # Check LLM calls
    assert mock_litellm_acompletion.call_count == 2
    # Check first call (user prompt)
    _call_args1, call_kwargs1 = mock_litellm_acompletion.call_args_list[0]
    assert any(msg["role"] == "user" and msg["content"] == prompt for msg in call_kwargs1["messages"]), "User prompt not found in first LLM call"
    # Check second call (includes tool result)
    _call_args2, call_kwargs2 = mock_litellm_acompletion.call_args_list[1]
    assert call_kwargs2["messages"][-1]["role"] == "tool"
    assert call_kwargs2["messages"][-1]["tool_call_id"] == read_tool_call_id
    assert call_kwargs2["messages"][-1]["content"] == file_content

    # Check tool execution
    mock_to_thread.assert_awaited_once()
    assert mock_to_thread.call_args.args[0].__name__ == "read_file"  # Check correct func passed
    assert mock_to_thread.call_args.kwargs == {"path": "report.txt"}

    # Check history (User, Assistant+ToolCall[read], ToolResult[read], FinalAssistant)
    assert mock_session_service.append_event.call_count == 3  # User, ToolResult, FinalAssistant
    events_added = [call.kwargs["event"] for call in mock_session_service.append_event.call_args_list]
    assert events_added[0].author == "user"
    assert events_added[1].author == "tool"  # Tool result added by run_turn loop
    assert events_added[1].content.parts[0].function_response.name == "read_file"
    assert events_added[1].content.parts[0].function_response.response == {"tool_call_id": read_tool_call_id, "content": file_content}
    assert events_added[2].author == "assistant"  # Final assistant message added at end
    assert events_added[2].content.parts[0].text == summary


@pytest.mark.asyncio
async def test_run_turn_tool_execution_error(agent, mock_litellm_acompletion, mock_session_service):
    """Test run_turn handles an error during tool execution."""
    prompt = "Read non_existent.txt"
    error_message = "Error executing read_file: [Errno 2] No such file or directory: 'non_existent.txt'"
    tool_call_id = "call_read_err_1"

    # Mock history retrieval
    mock_session_service.get_session.return_value = Session(id="test-session-123", app_name="code_agent", user_id="default_user", events=[])

    # --- Mock LLM Responses ---
    # 1. Request read_file
    read_call = MagicMock()
    read_call.id = tool_call_id
    read_call.type = "function"
    read_call.function.name = "read_file"
    read_call.function.arguments = '{"path": "non_existent.txt"}'
    mock_message1 = MagicMock()
    mock_message1.content = "Okay, reading the file."
    mock_message1.tool_calls = [read_call]
    mock_choice1 = MagicMock()
    mock_choice1.message = mock_message1
    mock_response1 = MagicMock()
    mock_response1.choices = [mock_choice1]

    # 2. LLM acknowledges the error
    mock_message2 = MagicMock()
    mock_message2.content = "Sorry, I couldn't find that file."
    mock_message2.tool_calls = None
    mock_choice2 = MagicMock()
    mock_choice2.message = mock_message2
    mock_response2 = MagicMock()
    mock_response2.choices = [mock_choice2]

    mock_litellm_acompletion.side_effect = [mock_response1, mock_response2]

    # --- Mock Tool Execution (to raise error) ---
    # Patch the actual tool function to raise the error
    # Also patch format_tool_error to ensure consistent error message format
    with (
        patch("code_agent.agent.agent.read_file") as mock_read_file,
        patch("code_agent.agent.agent.format_tool_error") as mock_format_error,
        patch("asyncio.to_thread") as mock_to_thread,
    ):
        # Simulate asyncio.to_thread raising the exception caught in run_turn
        mock_to_thread.side_effect = FileNotFoundError(2, "No such file or directory", "non_existent.txt")
        # Configure format_tool_error to return the expected string
        mock_format_error.return_value = error_message

        # --- Run Turn ---
        final_response = await agent.run_turn(prompt)

    # --- Assertions ---
    assert final_response == "Sorry, I couldn't find that file."

    # Check LLM calls
    assert mock_litellm_acompletion.call_count == 2
    # Check second call (includes error message as tool result)
    _call_args2, call_kwargs2 = mock_litellm_acompletion.call_args_list[1]
    assert call_kwargs2["messages"][-1]["role"] == "tool"
    assert call_kwargs2["messages"][-1]["tool_call_id"] == tool_call_id
    assert call_kwargs2["messages"][-1]["content"] == error_message

    # Check tool execution attempt
    mock_to_thread.assert_awaited_once()
    mock_format_error.assert_called_once()  # Ensure error was formatted

    # Check history (User, ToolResult[error], FinalAssistant)
    # Note: Assistant message requesting the tool is NOT saved if the tool fails immediately?
    # Let's re-verify run_turn logic: It adds the tool result to history even on error.
    # The final assistant message IS added.
    assert mock_session_service.append_event.call_count == 3
    events_added = [call.kwargs["event"] for call in mock_session_service.append_event.call_args_list]
    assert events_added[0].author == "user"
    assert events_added[1].author == "tool"  # Tool ERROR result is added
    assert events_added[1].content.parts[0].function_response.name == "read_file"
    assert events_added[1].content.parts[0].function_response.response == {"tool_call_id": tool_call_id, "content": error_message}
    assert events_added[2].author == "assistant"  # Final assistant message
    assert events_added[2].content.parts[0].text == "Sorry, I couldn't find that file."


@pytest.mark.asyncio
async def test_run_turn_max_tool_calls(agent, mock_litellm_acompletion, mock_session_service):
    """Test that the agent stops immediately when max_tool_calls is 1 and a tool is requested."""
    await agent.async_init()
    agent.config.max_tool_calls = 1
    test_session_id_str = agent.session_id
    initial_session = Session(id=test_session_id_str, app_name="code_agent", user_id="default_user", events=[])

    # Mock LLM response requesting ONE tool call
    tool_args_dict = {"path": "file.txt"}
    tool_args_str = json.dumps(tool_args_dict)
    llm_tool_call_id_1 = "call_readfile_llm_1"
    mock_function_1 = MagicMock()
    mock_function_1.name = "read_file"
    mock_function_1.arguments = tool_args_str

    mock_message_1 = MagicMock()
    mock_message_1.content = "Reading file.txt"
    mock_message_1.tool_calls = [MagicMock(id=llm_tool_call_id_1, type="function", function=mock_function_1)]
    mock_choice_1 = MagicMock()
    mock_choice_1.message = mock_message_1
    mock_response_1 = MagicMock()
    mock_response_1.choices = [mock_choice_1]

    mock_litellm_acompletion.side_effect = [mock_response_1]

    # Define events for history simulation
    user_prompt_event = create_test_event("user", "Initial prompt")
    # Assistant should request the tool
    assistant_msg1_event = create_test_event("assistant", "Reading file.txt", function_call=genai_types.FunctionCall(name="read_file", args=tool_args_dict))
    # Tool result event is NOT expected because the loop breaks BEFORE execution

    # Define session states needed
    session_after_user = Session(id=test_session_id_str, app_name="code_agent", user_id="default_user", events=[user_prompt_event])
    # State after assistant requested the tool (needed for final message persistence)
    session_after_assist1 = Session(id=test_session_id_str, app_name="code_agent", user_id="default_user", events=[user_prompt_event, assistant_msg1_event])

    # Mock get_session calls needed (3 calls)
    # 1. add_user_message -> get_session
    # 2. get_history before LLM call -> get_session
    # 3. add_assistant_message (final "max calls" msg) -> get_session
    mock_session_service.get_session.side_effect = [
        initial_session,  # Call 1: For add_user_message at start
        session_after_user,  # Call 2: For get_history before LLM call 1
        session_after_assist1,  # Call 3: For add_assistant_message (final "max calls" msg)
        # Add potential extra call if duplicate check runs get_history again
        session_after_assist1,  # Call 4: For potential duplicate check in post-loop
    ]

    # Mock the streaming response for the first (and only) LLM call
    # Chunk 1: Text content
    chunk1 = MagicMock()
    chunk1.choices[0].delta.content = "Reading file.txt"
    chunk1.choices[0].delta.tool_calls = None
    # Chunk 2: Tool call info
    chunk2 = MagicMock()
    chunk2.choices[0].delta.content = None
    tool_call_chunk = MagicMock()
    tool_call_chunk.index = 0
    tool_call_chunk.id = llm_tool_call_id_1
    tool_call_chunk.type = "function"
    tool_call_chunk.function.name = "read_file"
    tool_call_chunk.function.arguments = tool_args_str
    chunk2.choices[0].delta.tool_calls = [tool_call_chunk]

    mock_litellm_acompletion.return_value = mock_async_iterator([chunk1, chunk2])

    # Run the agent turn
    final_response = await agent.run_turn(prompt="Initial prompt")

    # Assertions
    assert "Reached maximum tool calls" in final_response
    mock_litellm_acompletion.assert_awaited_once()  # Only one LLM call

    # Check append_event calls
    # Expected:
    # 1. User prompt
    # 2. Partial Assistant ('Reading file.txt')
    # 3. Final Assistant ('Reached maximum...')
    # Note: Tool call request event is *not* added because max calls is reached *before* adding it
    append_calls = mock_session_service.append_event.call_args_list
    assert len(append_calls) >= 2  # At least user and final assistant message

    assert append_calls[0].kwargs["event"].author == "user"
    assert append_calls[0].kwargs["event"].content.parts[0].text == "Initial prompt"

    # Check for at least one partial message event
    assert any(call.kwargs["event"].author == "assistant" and call.kwargs["event"].partial for call in append_calls), "No partial assistant message found"

    # Check final assistant message event (should be the last one)
    final_event = append_calls[-1].kwargs["event"]
    assert final_event.author == "assistant"
    assert final_event.partial is False  # Should be final
    assert "Reached maximum tool calls" in final_event.content.parts[0].text
    # Verify the tool calls are NOT part of this final assistant message event
    assert len(final_event.content.parts) == 1 or not any(hasattr(p, "function_call") and p.function_call for p in final_event.content.parts)


# TODO: Add tests for error handling (API key, connection errors, etc.)
# TODO: Add tests for different providers (Gemini, Anthropic if keys available)
# TODO: Add test for quiet mode suppressing output


# Helper function for creating async iterators (mocks for streaming)
async def mock_async_iterator(items):
    for item in items:
        yield item
        await asyncio.sleep(0)  # Yield control briefly
