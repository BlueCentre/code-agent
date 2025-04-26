# Placeholder for ADK Service unit tests

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Updated imports for ADK v0.3.0
from google.adk.events.event import Event
from google.adk.sessions import (
    BaseSessionService,  # Renamed from AbstractSessionService
    InMemorySessionService,
    Session,
    # SessionId, EventType removed
)
from google.genai import types as genai_types  # Added

from code_agent.adk.services import (
    CodeAgentADKSessionManager,
    get_adk_session_service,  # Stays, but implementation changed
)

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# Mock session ID
MOCK_SESSION_ID = "test-session-123"


@pytest_asyncio.fixture
def mock_session() -> MagicMock:
    """Fixture for a mocked Session object."""
    mock = MagicMock(spec=Session)
    mock.id = MOCK_SESSION_ID
    mock.events = []
    return mock


@pytest_asyncio.fixture
async def mock_adk_session_service(mock_session: MagicMock) -> AsyncMock:
    """Fixture for a mocked BaseSessionService."""
    mock = AsyncMock(spec=BaseSessionService)
    # Mock methods based on BaseSessionService and usage in SessionManager
    mock.create_session.return_value = mock_session
    mock.get_session.return_value = mock_session
    mock.append_event.return_value = None  # Used by add_event in manager
    # get_history is now implemented in the manager using get_session
    return mock


@pytest_asyncio.fixture
async def session_manager(mock_adk_session_service: AsyncMock) -> CodeAgentADKSessionManager:
    """Fixture for CodeAgentADKSessionManager with a mocked service."""
    return CodeAgentADKSessionManager(mock_adk_session_service)


async def test_create_session(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock):
    """Test creating a new session."""
    session_id = session_manager.create_session()
    assert session_id == MOCK_SESSION_ID
    # Verify underlying service call with expected args (based on services.py implementation)
    mock_adk_session_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user")


async def test_get_session(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock):
    """Test retrieving an existing session."""
    session_id = MOCK_SESSION_ID  # Use string directly
    session = await session_manager.get_session(session_id)
    assert session.id == session_id
    # Verify underlying service call
    mock_adk_session_service.get_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=session_id)


async def test_add_event(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding a generic event."""
    session_id = MOCK_SESSION_ID
    # Use the new Event structure
    event_content = genai_types.Content(parts=[genai_types.Part(text="generic")])
    event = Event(author="test_author", content=event_content)

    # Need to mock get_session as it's called by add_event
    mock_adk_session_service.get_session.return_value = mock_session

    await session_manager.add_event(session_id, event)

    # Verify get_session was called first
    mock_adk_session_service.get_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=session_id)
    # Verify append_event was called with the session and event
    mock_adk_session_service.append_event.assert_called_once_with(session=mock_session, event=event)


async def test_add_user_message(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding a user message event."""
    session_id = MOCK_SESSION_ID
    content = "Hello Agent"

    mock_adk_session_service.get_session.return_value = mock_session
    await session_manager.add_user_message(session_id, content)

    # Check that append_event was called with the correct Event object
    mock_adk_session_service.append_event.assert_called_once()
    call_args = mock_adk_session_service.append_event.call_args
    assert call_args[1]["session"] == mock_session  # Check session kwarg
    added_event: Event = call_args[1]["event"]  # Check event kwarg
    assert added_event.author == "user"
    assert len(added_event.content.parts) == 1
    assert added_event.content.parts[0].text == content


async def test_add_assistant_message(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding an assistant message event without tool calls."""
    session_id = MOCK_SESSION_ID
    content = "Hello User"

    mock_adk_session_service.get_session.return_value = mock_session
    await session_manager.add_assistant_message(session_id, content)

    mock_adk_session_service.append_event.assert_called_once()
    call_args = mock_adk_session_service.append_event.call_args
    added_event: Event = call_args[1]["event"]
    assert added_event.author == "assistant"
    assert len(added_event.content.parts) == 1
    assert added_event.content.parts[0].text == content


async def test_add_assistant_message_with_tool_calls(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding an assistant message event with tool calls."""
    session_id = MOCK_SESSION_ID
    content = "Using a tool"
    # Use genai_types.FunctionCall
    tool_calls = [genai_types.FunctionCall(name="read_file", args={"path": "a.txt"})]

    mock_adk_session_service.get_session.return_value = mock_session
    await session_manager.add_assistant_message(session_id, content, tool_calls=tool_calls)

    mock_adk_session_service.append_event.assert_called_once()
    call_args = mock_adk_session_service.append_event.call_args
    added_event: Event = call_args[1]["event"]
    assert added_event.author == "assistant"
    assert len(added_event.content.parts) == 2  # Text part + function call part
    assert added_event.content.parts[0].text == content
    assert added_event.content.parts[1].function_call == tool_calls[0]


async def test_add_tool_result(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding a tool result event."""
    session_id = MOCK_SESSION_ID
    tool_call_id = "call_1"  # Note: tool_call_id is not directly used in the new event structure
    tool_name = "read_file"
    content = "File content here"

    mock_adk_session_service.get_session.return_value = mock_session
    # Pass invocation_id for completeness, though not asserted here
    await session_manager.add_tool_result(session_id, tool_call_id, tool_name, content, invocation_id="inv_test")

    mock_adk_session_service.append_event.assert_called_once()
    # Correct way to get kwargs from async mock call
    added_event: Event = mock_adk_session_service.append_event.call_args.kwargs["event"]
    assert added_event.author == "assistant"  # Expect 'assistant' as author now
    assert added_event.content.role == "user"  # Verify role is 'user'
    assert added_event.invocation_id == "inv_test"  # Verify invocation_id was passed
    # Verify content structure
    assert len(added_event.content.parts) == 1
    func_resp = added_event.content.parts[0].function_response
    assert func_resp is not None
    assert func_resp.name == tool_name
    assert func_resp.response == {"result": content}  # Check payload structure


async def test_add_system_message(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test adding a system message event."""
    session_id = MOCK_SESSION_ID
    content = "System instruction"

    mock_adk_session_service.get_session.return_value = mock_session
    await session_manager.add_system_message(session_id, content)

    mock_adk_session_service.append_event.assert_called_once()
    call_args = mock_adk_session_service.append_event.call_args
    added_event: Event = call_args[1]["event"]
    # Check the chosen mapping for system messages
    assert added_event.author == "system"
    assert len(added_event.content.parts) == 1
    assert added_event.content.parts[0].text == content


async def test_get_history(session_manager: CodeAgentADKSessionManager, mock_adk_session_service: AsyncMock, mock_session: MagicMock):
    """Test retrieving history."""
    session_id = MOCK_SESSION_ID
    expected_event = Event(author="user", content=genai_types.Content(parts=[genai_types.Part(text="test")]))
    mock_session.events = [expected_event]  # Set history on the mock session
    mock_adk_session_service.get_session.return_value = mock_session

    history = await session_manager.get_history(session_id)
    assert history == [expected_event]
    mock_adk_session_service.get_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=session_id)


# Test for get_adk_session_service initialization
# Remove patch for default_runtime_factory
@patch("code_agent.adk.services.InMemorySessionService")  # Patch the class directly
async def test_get_adk_session_service_initialization(mock_in_memory_service_class):
    """Test the initialization logic of get_adk_session_service."""
    mock_service_instance = MagicMock(spec=InMemorySessionService)
    mock_in_memory_service_class.return_value = mock_service_instance

    # Config is no longer passed
    service = await get_adk_session_service()

    # Verify InMemorySessionService was instantiated
    mock_in_memory_service_class.assert_called_once_with()
    # Verify the instance is returned
    assert service == mock_service_instance


# TODO: Add test for clear_history if a concrete clear mechanism is decided
# async def test_clear_history(...): ...
