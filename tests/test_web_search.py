from unittest.mock import MagicMock, patch

import pytest

from code_agent.config.settings_based_config import SecuritySettings, SettingsConfig
from code_agent.tools.simple_tools import web_search

# Mock the duckduckgo_search module
pytest.importorskip("unittest.mock")
duckduckgo_search_mock = MagicMock()
DDGS_mock = MagicMock()
duckduckgo_search_mock.DDGS = DDGS_mock
modules = {
    "duckduckgo_search": duckduckgo_search_mock,
    "duckduckgo_search.DDGS": DDGS_mock,
}
patch.dict("sys.modules", modules).start()


# Fixtures
@pytest.fixture
def mock_config():
    """Mock config with web search enabled."""
    config = MagicMock(spec=SettingsConfig)
    security = MagicMock(spec=SecuritySettings)
    security.enable_web_search = True
    config.security = security
    return config


@pytest.fixture
def disabled_web_search_config():
    """Mock config with web search disabled."""
    config = MagicMock(spec=SettingsConfig)
    security = MagicMock(spec=SecuritySettings)
    security.enable_web_search = False
    config.security = security
    return config


@pytest.fixture
def mock_ddgs_successful_results():
    """Mock successful DDGS search results."""
    return [
        {"title": "Test Result 1", "body": "This is the content of the first test result.", "href": "https://example.com/result1"},
        {"title": "Test Result 2", "body": "This is the content of the second test result.", "href": "https://example.com/result2"},
    ]


@pytest.fixture
def mock_empty_results():
    """Mock empty DDGS search results."""
    return []


# Tests
@patch("code_agent.tools.simple_tools.get_config")
def test_web_search_disabled(mock_get_config, disabled_web_search_config):
    """Test web_search returns error when disabled in config."""
    mock_get_config.return_value = disabled_web_search_config

    result = web_search("test query")

    assert "disabled in configuration" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.time.sleep")
def test_web_search_success(mock_sleep, mock_get_config, mock_config, mock_ddgs_successful_results):
    """Test web_search successfully returns formatted results."""
    mock_get_config.return_value = mock_config

    # Set up the mock DDGS instance
    mock_ddgs_instance = MagicMock()
    DDGS_mock.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.return_value = mock_ddgs_successful_results

    result = web_search("test query")

    # Check that the function called the API with expected parameters
    mock_ddgs_instance.text.assert_called_once_with("test query", max_results=3)

    # Check rate limiting delay was applied
    mock_sleep.assert_called_once_with(0.5)

    # Verify the formatted result contains expected elements
    assert "### Web Search Results" in result
    assert "**Result 1:** Test Result 1" in result
    assert "**Result 2:** Test Result 2" in result
    assert "This is the content of the first test result." in result
    assert "This is the content of the second test result." in result
    assert "Source: https://example.com/result1" in result
    assert "Source: https://example.com/result2" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.time.sleep")
def test_web_search_empty_results(mock_sleep, mock_get_config, mock_config, mock_empty_results):
    """Test web_search handles empty results gracefully."""
    mock_get_config.return_value = mock_config

    # Set up the mock DDGS instance
    mock_ddgs_instance = MagicMock()
    DDGS_mock.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.return_value = mock_empty_results

    result = web_search("test query")

    # Check error message for no results
    assert "No results found for query" in result
    assert "Try rephrasing your search query" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.time.sleep")
def test_web_search_api_error(mock_sleep, mock_get_config, mock_config):
    """Test web_search handles API errors gracefully."""
    mock_get_config.return_value = mock_config

    # Set up the mock DDGS instance to raise an exception
    mock_ddgs_instance = MagicMock()
    DDGS_mock.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.side_effect = Exception("API Error")

    result = web_search("test query")

    # Check error message
    assert "Error performing web search" in result
    assert "API Error" in result
    assert "network issues or rate limiting" in result


@patch("code_agent.tools.simple_tools.get_config")
def test_web_search_import_error(mock_get_config, mock_config):
    """Test web_search handles import errors gracefully."""
    mock_get_config.return_value = mock_config

    # Force an ImportError when trying to import DDGS
    with patch.dict("sys.modules", {"duckduckgo_search": None}):
        result = web_search("test query")

    # Check error message
    assert "Required package 'duckduckgo-search' is not installed" in result


@patch("code_agent.tools.simple_tools.get_config")
@patch("code_agent.tools.simple_tools.time.sleep")
def test_web_search_handles_missing_fields(mock_sleep, mock_get_config, mock_config):
    """Test web_search handles results with missing fields gracefully."""
    mock_get_config.return_value = mock_config

    # Create a result with missing fields
    incomplete_results = [
        # Missing 'title'
        {"body": "This is a result with missing title", "href": "https://example.com/incomplete1"},
        # Missing 'body'
        {"title": "Result with missing body", "href": "https://example.com/incomplete2"},
        # Missing 'href'
        {"title": "Result with missing URL", "body": "This is a result with missing URL"},
    ]

    # Set up the mock DDGS instance
    mock_ddgs_instance = MagicMock()
    DDGS_mock.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.return_value = incomplete_results

    result = web_search("test query")

    # Verify default values are used for missing fields
    assert "No Title" in result
    assert "No content available" in result
    assert "No URL available" in result

    # Also verify known content is included
    assert "Result with missing body" in result
    assert "Result with missing URL" in result
    assert "This is a result with missing title" in result
