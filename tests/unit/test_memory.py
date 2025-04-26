import unittest
from unittest.mock import MagicMock

from google.adk.events.event import Event
from google.adk.sessions import Session

from code_agent.adk.memory import InMemoryMemoryService, SearchMemoryResponse


class TestInMemoryMemoryService(unittest.TestCase):
    """Test cases for the InMemoryMemoryService."""

    def setUp(self):
        self.memory_service = InMemoryMemoryService()

    def test_search_empty_memory(self):
        """Test search on an empty memory store."""
        response = self.memory_service.search_memory("test_app", "test_user", "query")
        self.assertIsInstance(response, SearchMemoryResponse)
        self.assertEqual(len(response.results), 0)

    def test_add_session_to_memory(self):
        """Test adding a session to memory."""
        # Create a mock session
        session = MagicMock(spec=Session)
        session.app_name = "test_app"
        session.user_id = "test_user"
        session.id = "test_session"

        # Create mock events
        user_event = MagicMock(spec=Event)
        user_event.author = "user"
        user_event.content = MagicMock()
        user_event.content.parts = [MagicMock()]
        user_event.content.parts[0].text = "Hello, this is a test message."

        assistant_event = MagicMock(spec=Event)
        assistant_event.author = "assistant"
        assistant_event.content = MagicMock()
        assistant_event.content.parts = [MagicMock()]
        assistant_event.content.parts[0].text = "Hi there! How can I help you?"

        session.events = [user_event, assistant_event]

        # Add session to memory
        self.memory_service.add_session_to_memory(session)

        # Verify memory was stored correctly
        self.assertIn("test_app", self.memory_service._memories)
        self.assertIn("test_user", self.memory_service._memories["test_app"])
        self.assertEqual(len(self.memory_service._memories["test_app"]["test_user"]), 1)

        # Verify the conversation was captured
        conversation = self.memory_service._memories["test_app"]["test_user"][0]["conversation"]
        self.assertEqual(len(conversation), 2)
        self.assertEqual(conversation[0]["author"], "user")
        self.assertEqual(conversation[0]["content"], "Hello, this is a test message.")
        self.assertEqual(conversation[1]["author"], "assistant")
        self.assertEqual(conversation[1]["content"], "Hi there! How can I help you?")

    def test_search_memory(self):
        """Test searching memory for relevant information."""
        # Add a session with specific content
        session = MagicMock(spec=Session)
        session.app_name = "test_app"
        session.user_id = "test_user"
        session.id = "test_session"

        user_event1 = MagicMock(spec=Event)
        user_event1.author = "user"
        user_event1.content = MagicMock()
        user_event1.content.parts = [MagicMock()]
        user_event1.content.parts[0].text = "I'm working on a Python project."

        assistant_event1 = MagicMock(spec=Event)
        assistant_event1.author = "assistant"
        assistant_event1.content = MagicMock()
        assistant_event1.content.parts = [MagicMock()]
        assistant_event1.content.parts[0].text = "Great, let me know how I can help with your Python project."

        user_event2 = MagicMock(spec=Event)
        user_event2.author = "user"
        user_event2.content = MagicMock()
        user_event2.content.parts = [MagicMock()]
        user_event2.content.parts[0].text = "I need help with JavaScript not Python."

        session.events = [user_event1, assistant_event1, user_event2]

        # Add session to memory
        self.memory_service.add_session_to_memory(session)

        # Search for 'Python'
        response = self.memory_service.search_memory("test_app", "test_user", "Python")

        # Verify results
        self.assertGreater(len(response.results), 0)

        # The first result should be most relevant
        has_python_result = False
        for result in response.results:
            if "Python" in result.text:
                has_python_result = True
                break

        self.assertTrue(has_python_result, "Should find results containing 'Python'")

        # Search for 'JavaScript'
        response = self.memory_service.search_memory("test_app", "test_user", "JavaScript")

        # Verify results
        self.assertGreater(len(response.results), 0)
        has_js_result = False
        for result in response.results:
            if "JavaScript" in result.text:
                has_js_result = True
                break

        self.assertTrue(has_js_result, "Should find results containing 'JavaScript'")

        # Search for something not in memory
        response = self.memory_service.search_memory("test_app", "test_user", "Ruby programming")

        # Results should not contain irrelevant items with high scores
        for result in response.results:
            if "Ruby" in result.text:
                self.fail("Found irrelevant result containing 'Ruby'")


if __name__ == "__main__":
    unittest.main()
