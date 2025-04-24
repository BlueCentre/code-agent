"""Tests for ADK package initialization."""


def test_adk_package_init():
    """Test ADK package initialization and version export."""
    # First, import the google.adk module to get the actual version
    import google.adk

    actual_adk_version = google.adk.__version__

    # Then import our ADK package
    import code_agent.adk

    # Test that our module correctly exports the google.adk version
    assert code_agent.adk.__adk_version__ == actual_adk_version

    # Test that the session config components are exported
    assert hasattr(code_agent.adk, "SessionConfig")
    assert hasattr(code_agent.adk, "SessionPersistenceType")
    assert hasattr(code_agent.adk, "SessionMemoryType")
    assert hasattr(code_agent.adk, "create_default_session_config")
    assert hasattr(code_agent.adk, "create_persistent_session_config")
