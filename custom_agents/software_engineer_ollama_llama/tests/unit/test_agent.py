"""Unit tests for the Software Engineer Agent."""

from unittest.mock import MagicMock, patch

from software_engineer import root_agent


def test_root_agent_exists():
    """Test that the root agent is properly initialized."""
    assert root_agent is not None
    assert root_agent.name == "root_agent"

    # Check that all sub-agents are properly defined
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    expected_names = [
        "code_review_agent",
        "design_pattern_agent",
        "testing_agent",
        "debugging_agent",
        "documentation_agent",
        "devops_agent",
    ]

    for name in expected_names:
        assert name in sub_agent_names, f"Sub-agent {name} not found in root_agent"


@patch("google.adk.agents.Agent.generate_content")
def test_root_agent_generate_content(mock_generate_content):
    """Test that the root agent can generate content."""
    # Mock the generate_content method to return a response
    mock_response = MagicMock()
    mock_response.text = "I am the Software Engineer Agent."
    mock_generate_content.return_value = mock_response

    # Call the generate_content method
    response = root_agent.generate_content("Hello, can you help me with software engineering?")

    # Check that the method was called once
    mock_generate_content.assert_called_once()

    # Check that the response is as expected
    assert response.text == "I am the Software Engineer Agent."
