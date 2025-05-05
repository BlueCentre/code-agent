"""
Tests for the code_agent.adk.services module.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Updated imports for ADK v0.3.0
from google.adk.events.event import Event
from google.adk.sessions import (
    BaseSessionService,  # Renamed from AbstractSessionService
    Session,
)
from google.adk.sessions import (
    InMemorySessionService as ADKInMemorySessionService,
)

# SessionId, EventType removed
from google.genai import types as genai_types  # Added

from code_agent.adk.services import (
    CodeAgentADKSessionManager,
    SessionSecurityManager,  # Import placeholder for mocking
    get_adk_session_service,  # Stays, but implementation changed
)

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# Mock session ID
MOCK_SESSION_ID = "test-session-123"
MOCK_AUTH_TOKEN = "mock-auth-token-456"


@pytest_asyncio.fixture
def mock_session() -> MagicMock:
    """Fixture for a mocked Session object."""
    mock = MagicMock(spec=Session)
    mock.id = MOCK_SESSION_ID
    mock.events = []
    return mock


@pytest_asyncio.fixture
def mock_security_manager() -> MagicMock:
    """Fixture for a mocked SessionSecurityManager."""
    mock = MagicMock(spec=SessionSecurityManager)
    mock.register_session.return_value = MOCK_AUTH_TOKEN
    mock.verify_session_access.return_value = True  # Assume valid access for tests not focused on auth
    mock.is_session_expired.return_value = False  # Assume not expired
    return mock


@pytest_asyncio.fixture
async def mock_adk_session_service_placeholder():
    """Placeholder fixture, mocking will happen in tests."""
    # Returning None or a simple object to avoid AsyncMock in fixture setup
    return None


@pytest_asyncio.fixture
async def session_manager(mock_security_manager: MagicMock) -> CodeAgentADKSessionManager:  # Add mock_security_manager fixture
    """Fixture for CodeAgentADKSessionManager, service will be mocked in tests."""
    # Initialize with None, patch the _session_service attribute in tests
    # Inject the mock security manager
    manager = CodeAgentADKSessionManager(None)
    manager.security_manager = mock_security_manager  # Inject the mock
    # Explicitly enable authentication for testing security checks
    manager.config.security.enable_authentication = True
    return manager


async def test_create_session(
    session_manager: CodeAgentADKSessionManager,
    mock_session: MagicMock,
    mock_security_manager: MagicMock,
):  # Reformat long line
    """Test creating a new session."""
    # Create and configure the mock service here
    mock_service = AsyncMock(spec=BaseSessionService)
    # Set the mock session id correctly
    mock_session.id = MOCK_SESSION_ID
    # The underlying service returns the Session object
    mock_service.create_session.return_value = mock_session

    # Patch the service and the security manager
    with patch.object(session_manager, "_session_service", mock_service):
        # No need to patch security_manager as it's already injected via fixture
        session_id, auth_token = session_manager.create_session()  # Capture tuple
        assert session_id == MOCK_SESSION_ID
        assert auth_token == MOCK_AUTH_TOKEN  # Use constant
        # Verify underlying service call with app_name, user_id, and session_id=ANY
        mock_service.create_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=ANY)
        # Verify security manager call
        mock_security_manager.register_session.assert_called_once_with(MOCK_SESSION_ID, "default_user")


async def test_get_session(session_manager: CodeAgentADKSessionManager, mock_session: MagicMock, mock_security_manager: MagicMock):  # Add mock_security_manager
    """Test retrieving an existing session."""
    session_id = MOCK_SESSION_ID
    auth_token = MOCK_AUTH_TOKEN  # Use constant

    # Create and configure the mock service here
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.get_session.return_value = mock_session

    with patch.object(session_manager, "_session_service", mock_service):
        # No need to patch security_manager as it's already injected via fixture
        session = await session_manager.get_session(session_id, auth_token=auth_token)
        assert session.id == session_id
        # Verify underlying service call with app_name, user_id, session_id
        mock_service.get_session.assert_called_once_with(app_name="code_agent", user_id="default_user", session_id=session_id)
        # Verify security manager calls for access check
        mock_security_manager.verify_session_access.assert_called_once_with(session_id, auth_token)
        mock_security_manager.is_session_expired.assert_called_once_with(session_id)


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_event(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test adding a generic event."""
    session_id = MOCK_SESSION_ID
    event_content = genai_types.Content(parts=[genai_types.Part(text="generic")])
    event = Event(author="test_author", content=event_content)

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        await session_manager.add_event(session_id, event)
        # Verify manager's get_session was called first, expecting auth_token=None internally
        mock_get_session.assert_called_once_with(session_id, None)
        # Verify underlying append_event was called with the session object
        mock_service.append_event.assert_called_once_with(session=mock_session, event=event)


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_user_message(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test adding a user message event."""
    session_id = MOCK_SESSION_ID
    content = "Hello Agent"

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        # Remove auth_token from this call
        await session_manager.add_user_message(session_id, content)
        # Verify manager's get_session was called first (internally by add_event with auth_token=None)
        mock_get_session.assert_called_once_with(session_id, None)
        # Check that underlying append_event was called with the correct Event object
        mock_service.append_event.assert_called_once()
        call_args = mock_service.append_event.call_args
        assert call_args[1]["session"] == mock_session
        added_event: Event = call_args[1]["event"]
        assert added_event.author == "user"
        assert len(added_event.content.parts) == 1
        assert added_event.content.parts[0].text == content


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_assistant_message(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test adding an assistant message event without tool calls."""
    session_id = MOCK_SESSION_ID
    content = "Hello User"

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        # Remove auth_token from this call
        await session_manager.add_assistant_message(session_id, content)
        # Verify manager's get_session was called first (internally by add_event with auth_token=None)
        mock_get_session.assert_called_once_with(session_id, None)
        # Check that underlying append_event was called
        mock_service.append_event.assert_called_once()
        call_args = mock_service.append_event.call_args
        assert call_args[1]["session"] == mock_session
        added_event: Event = call_args[1]["event"]
        assert added_event.author == "assistant"
        assert len(added_event.content.parts) == 1
        assert added_event.content.parts[0].text == content


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_assistant_message_with_tool_calls(
    mock_get_session,
    session_manager: CodeAgentADKSessionManager,
    mock_session: MagicMock,
):  # Reformat long line
    """Test adding an assistant message event with tool calls."""
    session_id = MOCK_SESSION_ID
    content = "Using a tool"
    tool_calls = [genai_types.FunctionCall(name="read_file", args={"path": "a.txt"})]

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        # Remove auth_token from this call
        await session_manager.add_assistant_message(session_id, content, tool_calls=tool_calls)
        # Verify manager's get_session was called first (internally by add_event with auth_token=None)
        mock_get_session.assert_called_once_with(session_id, None)
        # Check that underlying append_event was called
        mock_service.append_event.assert_called_once()
        call_args = mock_service.append_event.call_args
        assert call_args[1]["session"] == mock_session
        added_event: Event = call_args[1]["event"]
        assert added_event.author == "assistant"
        assert len(added_event.content.parts) == 2
        assert added_event.content.parts[0].text == content
        assert added_event.content.parts[1].function_call == tool_calls[0]


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_tool_result(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test adding a tool result event."""
    session_id = MOCK_SESSION_ID
    tool_call_id = "call_1"
    tool_name = "read_file"
    content = "File content here"

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        # Remove auth_token from this call
        await session_manager.add_tool_result(session_id, tool_call_id, tool_name, content, invocation_id="inv_test")
        # Verify manager's get_session was called first (internally by add_event, which receives auth_token=None, resulting in this call signature)
        mock_get_session.assert_called_once_with(session_id)
        # Check that underlying append_event was called
        mock_service.append_event.assert_called_once()
        added_event: Event = mock_service.append_event.call_args.kwargs["event"]
        assert added_event.author == "assistant"
        assert added_event.content.role == "function"  # Role for tool result is 'function'
        assert added_event.invocation_id == "inv_test"
        assert len(added_event.content.parts) == 1
        func_resp = added_event.content.parts[0].function_response
        assert func_resp is not None
        assert func_resp.name == tool_name  # name is the tool name
        assert func_resp.response == {"result": content}  # response structure wraps content


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_add_system_message(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test adding a system message event."""
    session_id = MOCK_SESSION_ID
    content = "System instruction"

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session

    # Create and configure the underlying service mock
    mock_service = AsyncMock(spec=BaseSessionService)
    mock_service.append_event = AsyncMock(return_value=None)

    with patch.object(session_manager, "_session_service", mock_service):
        # Remove auth_token from this call
        await session_manager.add_system_message(session_id, content)
        # Verify manager's get_session was called first (internally by add_event with auth_token=None)
        mock_get_session.assert_called_once_with(session_id, None)
        # Check that underlying append_event was called
        mock_service.append_event.assert_called_once()
        call_args = mock_service.append_event.call_args
        assert call_args[1]["session"] == mock_session
        added_event: Event = call_args[1]["event"]
        assert added_event.author == "system"
        assert len(added_event.content.parts) == 1
        assert added_event.content.parts[0].text == content


@patch("code_agent.adk.services.CodeAgentADKSessionManager.get_session", new_callable=AsyncMock)
async def test_get_history(mock_get_session, session_manager: CodeAgentADKSessionManager, mock_session: MagicMock):  # Patch manager's get_session
    """Test retrieving history."""
    session_id = MOCK_SESSION_ID
    expected_event = Event(author="user", content=genai_types.Content(parts=[genai_types.Part(text="test")]))

    # Mock the manager's get_session directly
    mock_get_session.return_value = mock_session
    mock_session.events = [expected_event]  # Set history on the mock session

    # The underlying service is not directly called by get_history in the manager
    with patch.object(session_manager, "_session_service", AsyncMock(spec=BaseSessionService)):  # Need a basic mock service
        # Remove auth_token from this call
        history = await session_manager.get_history(session_id)
        assert history == [expected_event]
        # Verify manager's get_session was called (internally, without auth_token)
        mock_get_session.assert_called_once_with(session_id)


# Test for get_adk_session_service initialization
@pytest.mark.asyncio
@patch("code_agent.adk.services.ADKInMemorySessionService")
@patch("code_agent.adk.services.initialize_adk_with_api_key")  # Also patch initialization
# Correct order: patch argument comes after fixtures
async def test_get_adk_session_service_initialization(mock_init_key, mock_adk_in_memory_service_class):
    """Test the initialization logic of get_adk_session_service."""
    mock_service_instance = MagicMock(spec=ADKInMemorySessionService)
    mock_adk_in_memory_service_class.return_value = mock_service_instance

    # Clear any existing service to force re-initialization for the test
    with patch("code_agent.adk.services._adk_session_service", None):
        service = await get_adk_session_service()

    # Verify initialization was called
    mock_init_key.assert_called_once()
    # Verify InMemorySessionService was instantiated
    mock_adk_in_memory_service_class.assert_called_once_with()
    # Verify the instance is returned
    assert service == mock_service_instance


# TODO: Add test for clear_history if a concrete clear mechanism is decided
# async def test_clear_history(...): ...
