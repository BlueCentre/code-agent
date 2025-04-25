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

    # Test that the tool components are exported
    assert hasattr(code_agent.adk, "create_read_file_tool")
    assert hasattr(code_agent.adk, "create_delete_file_tool")
    assert hasattr(code_agent.adk, "create_apply_edit_tool")
    assert hasattr(code_agent.adk, "get_file_tools")
