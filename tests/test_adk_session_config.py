"""Tests for ADK session configuration."""

from code_agent.adk.session_config import (
    SessionConfig,
    SessionMemoryType,
    SessionPersistenceType,
    create_default_session_config,
    create_persistent_session_config,
)


def test_session_persistence_type_enum():
    """Test the SessionPersistenceType enum."""
    assert SessionPersistenceType.MEMORY.value == "memory"
    assert SessionPersistenceType.FILE.value == "file"
    assert SessionPersistenceType.CLOUD.value == "cloud"


def test_session_memory_type_enum():
    """Test the SessionMemoryType enum."""
    assert SessionMemoryType.BASIC.value == "basic"
    assert SessionMemoryType.STRUCTURED.value == "structured"
    assert SessionMemoryType.VECTOR.value == "vector"


def test_session_config_defaults():
    """Test SessionConfig with default values."""
    config = SessionConfig()
    assert config.session_id is None
    assert config.session_name is None
    assert config.persistence_type == SessionPersistenceType.MEMORY
    assert config.persistence_path is None
    assert config.memory_type == SessionMemoryType.BASIC
    assert config.memory_options == {}
    assert config.max_turns is None
    assert config.max_tokens is None
    assert config.metadata == {}
    assert config.tags == []
    assert config.agent_options == {}


def test_session_config_custom_values():
    """Test SessionConfig with custom values."""
    config = SessionConfig(
        session_id="test-id",
        session_name="Test Session",
        persistence_type=SessionPersistenceType.FILE,
        persistence_path="/tmp/sessions",
        memory_type=SessionMemoryType.STRUCTURED,
        memory_options={"max_entities": 100},
        max_turns=50,
        max_tokens=8000,
        metadata={"user_id": "123"},
        tags=["test", "demo"],
        agent_options={"temperature": 0.7},
    )

    assert config.session_id == "test-id"
    assert config.session_name == "Test Session"
    assert config.persistence_type == SessionPersistenceType.FILE
    assert config.persistence_path == "/tmp/sessions"
    assert config.memory_type == SessionMemoryType.STRUCTURED
    assert config.memory_options == {"max_entities": 100}
    assert config.max_turns == 50
    assert config.max_tokens == 8000
    assert config.metadata == {"user_id": "123"}
    assert config.tags == ["test", "demo"]
    assert config.agent_options == {"temperature": 0.7}


def test_session_config_to_dict():
    """Test conversion of SessionConfig to dictionary."""
    config = SessionConfig(
        session_id="test-id",
        session_name="Test Session",
        persistence_type=SessionPersistenceType.FILE,
        persistence_path="/tmp/sessions",
        memory_type=SessionMemoryType.STRUCTURED,
        memory_options={"max_entities": 100},
        max_turns=50,
        max_tokens=8000,
        metadata={"user_id": "123"},
        tags=["test", "demo"],
        agent_options={"temperature": 0.7},
    )

    config_dict = config.to_dict()

    assert config_dict["session_id"] == "test-id"
    assert config_dict["session_name"] == "Test Session"
    assert config_dict["persistence"]["type"] == "file"
    assert config_dict["persistence"]["path"] == "/tmp/sessions"
    assert config_dict["memory"]["type"] == "structured"
    assert config_dict["memory"]["options"] == {"max_entities": 100}
    assert config_dict["limits"]["max_turns"] == 50
    assert config_dict["limits"]["max_tokens"] == 8000
    assert config_dict["metadata"] == {"user_id": "123"}
    assert config_dict["tags"] == ["test", "demo"]
    assert config_dict["agent_options"] == {"temperature": 0.7}


def test_session_config_from_dict():
    """Test creation of SessionConfig from dictionary."""
    config_dict = {
        "session_id": "test-id",
        "session_name": "Test Session",
        "persistence": {
            "type": "file",
            "path": "/tmp/sessions",
        },
        "memory": {
            "type": "structured",
            "options": {"max_entities": 100},
        },
        "limits": {
            "max_turns": 50,
            "max_tokens": 8000,
        },
        "metadata": {"user_id": "123"},
        "tags": ["test", "demo"],
        "agent_options": {"temperature": 0.7},
    }

    config = SessionConfig.from_dict(config_dict)

    assert config.session_id == "test-id"
    assert config.session_name == "Test Session"
    assert config.persistence_type == SessionPersistenceType.FILE
    assert config.persistence_path == "/tmp/sessions"
    assert config.memory_type == SessionMemoryType.STRUCTURED
    assert config.memory_options == {"max_entities": 100}
    assert config.max_turns == 50
    assert config.max_tokens == 8000
    assert config.metadata == {"user_id": "123"}
    assert config.tags == ["test", "demo"]
    assert config.agent_options == {"temperature": 0.7}


def test_session_config_from_dict_with_defaults():
    """Test creation of SessionConfig from dictionary with minimal fields."""
    config_dict = {
        "session_id": "test-id",
    }

    config = SessionConfig.from_dict(config_dict)

    assert config.session_id == "test-id"
    assert config.session_name is None
    assert config.persistence_type == SessionPersistenceType.MEMORY
    assert config.persistence_path is None
    assert config.memory_type == SessionMemoryType.BASIC
    assert config.memory_options == {}
    assert config.max_turns is None
    assert config.max_tokens is None
    assert config.metadata == {}
    assert config.tags == []
    assert config.agent_options == {}


def test_create_default_session_config():
    """Test the default session config factory function."""
    config = create_default_session_config()

    assert config.persistence_type == SessionPersistenceType.MEMORY
    assert config.memory_type == SessionMemoryType.BASIC


def test_create_persistent_session_config():
    """Test the persistent session config factory function."""
    config = create_persistent_session_config("Persistent Session", "/tmp/sessions")

    assert config.session_name == "Persistent Session"
    assert config.persistence_type == SessionPersistenceType.FILE
    assert config.persistence_path == "/tmp/sessions"
    assert config.memory_type == SessionMemoryType.STRUCTURED


def test_create_persistent_session_config_without_path():
    """Test the persistent session config without a path."""
    config = create_persistent_session_config("Persistent Session")

    assert config.session_name == "Persistent Session"
    assert config.persistence_type == SessionPersistenceType.FILE
    assert config.persistence_path is None
    assert config.memory_type == SessionMemoryType.STRUCTURED
