"""
Tests for code_agent.agent.__init__ module.
"""

import importlib


def test_agent_init_module_import():
    """Test that the agent.__init__ module can be imported successfully."""
    # Import the module
    import code_agent.agent

    # Check that it's a module
    assert hasattr(code_agent.agent, "__file__")

    # Force reload to ensure coverage is counted
    importlib.reload(code_agent.agent)


def test_agent_package_structure():
    """Test that the agent package has the expected structure."""
    # Import the module
    import code_agent.agent
    import code_agent.agent.multi_agent
    import code_agent.agent.prompt

    # The multi_agent module should be accessible through the package
    assert hasattr(code_agent.agent, "multi_agent")

    # The prompt module should be accessible
    assert hasattr(code_agent.agent, "prompt")

    # Check that essential functions are available
    assert hasattr(code_agent.agent.multi_agent, "get_root_agent")
