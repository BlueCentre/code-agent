"""
Tests for the code_agent.agent.prompt module.
"""

from code_agent.agent.prompt import ROOT_AGENT_INSTR


def test_root_agent_instr_exists():
    """Test that ROOT_AGENT_INSTR is defined and is a string."""
    assert ROOT_AGENT_INSTR is not None
    assert isinstance(ROOT_AGENT_INSTR, str)
    assert len(ROOT_AGENT_INSTR) > 0


def test_root_agent_instr_content():
    """Test that ROOT_AGENT_INSTR contains expected key phrases."""
    # Check for primary agent responsibilities
    assert "primary agent" in ROOT_AGENT_INSTR
    assert "Analyze the user's request" in ROOT_AGENT_INSTR

    # Check for agent delegation instructions
    assert "SearchAgent" in ROOT_AGENT_INSTR
    assert "LocalOpsAgent" in ROOT_AGENT_INSTR

    # Check for formatting placeholder
    assert "{user_profile}" in ROOT_AGENT_INSTR


def test_root_agent_instr_format():
    """Test that ROOT_AGENT_INSTR can be properly formatted."""
    user_profile = "Name: Test User\nPreferences: Python, CLI tools"
    formatted = ROOT_AGENT_INSTR.format(user_profile=user_profile)

    # Check that the user profile was inserted
    assert "Name: Test User" in formatted
    assert "Preferences: Python, CLI tools" in formatted

    # The original placeholder should be replaced
    assert "{user_profile}" not in formatted
