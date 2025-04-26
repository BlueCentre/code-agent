from pathlib import Path

import pytest
import yaml


@pytest.fixture
def mock_config_file(tmp_path: Path) -> Path:
    """Mock the config file with test configuration and return its Path."""
    config_content = {
        "default_provider": "file_provider",
        "default_model": "file_model",
        "api_keys": {"openai": "file_openai_key", "groq": "file_groq_key"},
        "auto_approve_edits": False,
        "auto_approve_native_commands": True,
        "native_command_allowlist": ["ls", "cat", "pwd"],
        "rules": ["Be concise", "Explain code"],
    }
    # Use a consistent name, maybe .code_agent.yaml, or make it unique per test?
    # Using unique per test run via tmp_path avoids conflicts.
    config_path = tmp_path / "mock_config.yaml"
    config_path.write_text(yaml.dump(config_content))
    return config_path  # Return the Path object
