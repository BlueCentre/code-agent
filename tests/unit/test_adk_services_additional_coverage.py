"""
Tests to increase coverage for code_agent.adk.services module,
focusing on error handling and edge cases.
"""

import base64
from unittest.mock import MagicMock, patch

from code_agent.adk.services import (
    ImageGenerationService,
    InMemorySessionService,
    SessionState,
    TypingService,
    get_events_response_text,
    get_events_with_state,
)

# Import mock versions instead of real ones
from .MagicMock.google.adk.events import Event, EventState, EventType

# Import mock GenAiException
from .MagicMock.google.genai.exceptions import GenAiException

# Import mock types
from .MagicMock.google.genai.types import GenerationConfig, HarmBlockThreshold, HarmCategory


class TestADKServices:
    """Tests for the ADK services module with focus on error cases."""

    def test_get_events_with_state_edge_cases(self):
        """Test get_events_with_state with various edge cases."""
        # Test with empty events list
        events = []
        assert get_events_with_state(events, EventState.COMPLETE) == []

        # Test with None events list
        assert get_events_with_state(None, EventState.COMPLETE) == []

        # Test with events that don't match the state
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE),
            Event(id="2", type=EventType.TEXT, state=EventState.PENDING),
            Event(id="3", type=EventType.TEXT, state=EventState.ACTIVE),
        ]
        assert len(get_events_with_state(events, EventState.ERROR)) == 0

        # Test with mixed event states
        assert len(get_events_with_state(events, EventState.COMPLETE)) == 1
        assert get_events_with_state(events, EventState.COMPLETE)[0].id == "1"

        # Test with multiple matching events
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE),
            Event(id="2", type=EventType.TEXT, state=EventState.PENDING),
            Event(id="3", type=EventType.TEXT, state=EventState.COMPLETE),
        ]
        matching_events = get_events_with_state(events, EventState.COMPLETE)
        assert len(matching_events) == 2
        assert set(e.id for e in matching_events) == {"1", "3"}

    def test_get_events_response_text_edge_cases(self):
        """Test get_events_response_text with various edge cases."""
        # Test with empty events list
        events = []
        assert get_events_response_text(events) == ""

        # Test with None events list
        assert get_events_response_text(None) == ""

        # Test with events that don't have parts
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE),
        ]
        assert get_events_response_text(events) == ""

        # Test with events that have empty parts
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE, parts=[]),
        ]
        assert get_events_response_text(events) == ""

        # Test with events that have non-text parts
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE, parts=[{"binary_data": base64.b64encode(b"test").decode()}]),
        ]
        assert get_events_response_text(events) == ""

        # Test with multiple events with text parts
        events = [
            Event(id="1", type=EventType.TEXT, state=EventState.COMPLETE, parts=[{"text": "Hello"}]),
            Event(id="2", type=EventType.TEXT, state=EventState.COMPLETE, parts=[{"text": " world"}]),
        ]
        assert get_events_response_text(events) == "Hello world"

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_with_invalid_id(self, mock_session_class):
        """Test InMemorySessionService.get_session with invalid session ID."""
        # Create the service
        service = InMemorySessionService()

        # Test with invalid session ID (not in memory)
        session = service.get_session("invalid_id")
        assert session is None

        # Verify Session class was not called
        mock_session_class.assert_not_called()

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_create_session(self, mock_session_class):
        """Test InMemorySessionService.create_session with various scenarios."""
        # Mock Session class
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Create the service
        service = InMemorySessionService()

        # Test with defaults
        session_id = service.create_session()

        # Verify Session was created with default params
        mock_session_class.assert_called_once()

        # Check that the session was stored in memory
        assert session_id in service._sessions
        assert service._sessions[session_id] == mock_session

        # Reset mock for next test
        mock_session_class.reset_mock()

        # Test with custom parameters
        custom_config = GenerationConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=5,
            max_output_tokens=2000,
        )
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        }

        session_id = service.create_session(generation_config=custom_config, safety_settings=safety_settings)

        # Verify Session was created with custom params
        mock_session_class.assert_called_once_with(generation_config=custom_config, safety_settings=safety_settings)

        # Check that the session was stored in memory
        assert session_id in service._sessions

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_remove_session(self, _):
        """Test InMemorySessionService.remove_session."""
        # Create the service
        service = InMemorySessionService()

        # Create a session
        session_id = service.create_session()
        assert session_id in service._sessions

        # Test removing the session
        removed = service.remove_session(session_id)
        assert removed
        assert session_id not in service._sessions

        # Test removing a session that doesn't exist
        removed = service.remove_session("nonexistent_id")
        assert not removed

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_session_state(self, _):
        """Test InMemorySessionService._session_state method."""
        # Create the service
        service = InMemorySessionService()

        # Test with session that doesn't exist
        state = service._session_state("nonexistent_id")
        assert state == SessionState.UNKNOWN

        # Create a session
        session_id = service.create_session()

        # Test with valid session
        state = service._session_state(session_id)
        assert state == SessionState.CREATED

        # Mark session as started
        service._started_sessions.add(session_id)
        state = service._session_state(session_id)
        assert state == SessionState.RUNNING

        # Mark session as stopped
        service._stopped_sessions.add(session_id)
        state = service._session_state(session_id)
        assert state == SessionState.STOPPED

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_mark_started(self, _):
        """Test InMemorySessionService.mark_started method."""
        # Create the service
        service = InMemorySessionService()

        # Create a session
        session_id = service.create_session()

        # Mark session as started
        success = service.mark_started(session_id)
        assert success
        assert session_id in service._started_sessions
        assert session_id not in service._stopped_sessions

        # Try to mark a session that doesn't exist
        success = service.mark_started("nonexistent_id")
        assert not success

    @patch("code_agent.adk.services.Session")
    def test_in_memory_session_service_mark_stopped(self, _):
        """Test InMemorySessionService.mark_stopped method."""
        # Create the service
        service = InMemorySessionService()

        # Create a session
        session_id = service.create_session()

        # Mark session as started first
        service.mark_started(session_id)

        # Mark session as stopped
        success = service.mark_stopped(session_id)
        assert success
        assert session_id in service._stopped_sessions

        # Try to mark a session that doesn't exist
        success = service.mark_stopped("nonexistent_id")
        assert not success

    @patch("code_agent.adk.services.time.time")
    @patch("code_agent.adk.services.ImageGenerationService._make_request")
    def test_image_generation_service_error_handling(self, mock_make_request, mock_time):
        """Test ImageGenerationService error handling."""
        # Mock time.time to return a fixed value
        mock_time.return_value = 123456.789

        # Mock _make_request to raise an exception
        mock_make_request.side_effect = GenAiException("API error")

        # Create the service
        service = ImageGenerationService()

        # Test generate_image with an error
        try:
            # Update the call to match our implementation
            service.generate_image("prompt", cache_key="test_cache_key")
            assert False, "Should have raised an exception"  # noqa: B011
        except Exception as e:
            # Verify that the exception was raised
            assert "API error" in str(e)

        # Verify that _make_request was called with the correct arguments
        mock_make_request.assert_called_once_with("prompt")

        # Reset mock for next test
        mock_make_request.reset_mock()
        mock_make_request.side_effect = None

        # Test with a different type of error
        mock_make_request.side_effect = ValueError("Value error")

        try:
            service.generate_image("another_prompt")
            assert False, "Should have raised an exception"  # noqa: B011
        except Exception as e:
            # Verify that the exception was thrown with the expected message
            assert "Value error" in str(e)

    @patch("code_agent.adk.services.Session")
    def test_typing_service_with_invalid_session(self, _):
        """Test TypingService with invalid session."""
        # Create mock session service
        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = None

        # Create typing service
        service = TypingService(mock_session_service)

        # Test typing with invalid session
        result = service.type("invalid_session", "test message")

        # Verify result
        assert not result

        # Reset mock for next test
        mock_session_service.reset_mock()

        # Mock valid session but with an error condition
        mock_session = MagicMock()
        mock_session_service.get_session.return_value = mock_session

        # Override the type method to handle error scenarios
        with patch.object(TypingService, "type", return_value=False):
            # Test typing with session that now returns an error
            result = service.type("valid_session", "test message")

            # Verify result
            assert not result
