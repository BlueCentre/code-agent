"""Tests for configuration loading, initialization, and helper functions."""

import os
from unittest.mock import MagicMock, mock_open, patch, PropertyMock, call
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

# Import the target module for side effects; ensure it exists and is correct
try:
    import code_agent.config.config
except ImportError:
    # Handle case where the module might not exist or path is wrong
    # This might indicate a setup issue, but allows tests to define mocks
    pass

# Import from the correct location now
from code_agent.config.config import get_api_key, get_config, initialize_config, _config as config_singleton

# Use the correct path for these models and functions
from code_agent.config.settings_based_config import ( # noqa: E402
    DEFAULT_CONFIG_PATH,
    TEMPLATE_CONFIG_PATH,
    ApiKeys,
    CodeAgentSettings,  # Use the final merged settings class
    SettingsConfig,
    build_effective_config,
    create_default_config_file,
    load_config_from_file,
    # settings_to_dict, # This function seems unused in tests
)
from rich import print as rich_print # Import rich_print from rich library


@pytest.fixture(autouse=True)
def reset_config_singleton_fixture(): # Renamed fixture to avoid name clash
    """Ensures the config singleton is reset before each test."""
    global config_singleton
    config_singleton = None
    yield
    config_singleton = None


@pytest.fixture
def temp_config_path(tmp_path):
    """Creates a temporary config path for testing."""
    config_dir = tmp_path / ".config" / "code-agent"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    # Ensure the template path is defined, even if dummy for some tests
    # If TEMPLATE_CONFIG_PATH is dynamic, adjust accordingly
    # global TEMPLATE_CONFIG_PATH
    # TEMPLATE_CONFIG_PATH = tmp_path / "template_config.yaml" # Example if needed
    return config_path


@pytest.fixture
def valid_config_data():
    """Returns a valid configuration dictionary for file loading tests."""
    # Based on SettingsConfig structure, but CodeAgentSettings is the final result
    return {
        "default_provider": "openai",
        "default_model": "gpt-4o",
        "api_keys": {
            "openai": "sk-" + "a" * 48,
            "ai_studio": "AIza" + "a" * 35,
            # Add other potential keys if needed by tests
            "groq": "gsk-" + "b" * 48,
        },
        "auto_approve_edits": False,
        "auto_approve_native_commands": False,
        "native_command_allowlist": ["git status", "ls -la"],
        "rules": ["rule1", "rule2"],
        "max_tokens": 1500,  # Add fields from CodeAgentSettings if needed
        "temperature": 0.8,
        "max_tool_calls": 5,
        "verbosity": 1,
    }


# --- Tests for Models (ApiKeys, SettingsConfig, CodeAgentSettings) ---


def test_api_keys_model():
    """Test the ApiKeys model."""
    keys = ApiKeys(openai="test-key", ai_studio="test-key-2")
    assert keys.openai == "test-key"
    assert keys.ai_studio == "test-key-2"
    # Test extra keys are allowed and accessible via model_dump
    extra_keys = ApiKeys(openai="test-key", custom_provider="custom-key")
    dump = extra_keys.model_dump(exclude_unset=True)
    assert dump["openai"] == "test-key"
    assert dump["custom_provider"] == "custom-key"


def test_settings_config_model_defaults():
    """Test the default values in SettingsConfig."""
    config = SettingsConfig()
    assert config.default_provider == "ai_studio"
    assert config.default_model == "gemini-2.0-flash"
    assert config.auto_approve_edits is False
    assert config.auto_approve_native_commands is False
    assert config.native_command_allowlist == []
    assert config.rules == []
    # Check defaults for fields inherited/added in CodeAgentSettings
    agent_settings = CodeAgentSettings()  # Should inherit defaults
    assert agent_settings.default_provider == "ai_studio"
    assert agent_settings.max_tokens == 1000  # Default from CodeAgentSettings
    assert agent_settings.temperature == 0.7  # Default from CodeAgentSettings


def test_settings_config_model_custom():
    """Test creating SettingsConfig with custom values."""
    custom_config = SettingsConfig(
        default_provider="openai",
        default_model="gpt-4o",
        auto_approve_edits=True,
        native_command_allowlist=["git status"],
    )
    assert custom_config.default_provider == "openai"
    assert custom_config.default_model == "gpt-4o"
    assert custom_config.auto_approve_edits is True
    assert custom_config.native_command_allowlist == ["git status"]


def test_code_agent_settings_merges_correctly():
    """Test that CodeAgentSettings merges fields from SettingsConfig correctly."""
    settings_config = SettingsConfig(default_provider="test_provider", max_tokens=500)
    # Simulate loading into CodeAgentSettings
    merged_settings = CodeAgentSettings(**settings_config.model_dump())
    assert merged_settings.default_provider == "test_provider"
    assert merged_settings.max_tokens == 500  # Takes value from SettingsConfig part
    assert merged_settings.temperature == 0.7  # Takes default from CodeAgentSettings
    assert merged_settings.max_tool_calls == 10  # Takes default from CodeAgentSettings


# --- Tests for File Loading ---


def test_load_config_from_file(temp_config_path, valid_config_data):
    """Test loading configuration from a YAML file."""
    with open(temp_config_path, "w") as f:
        yaml.dump(valid_config_data, f)

    loaded_config = load_config_from_file(temp_config_path)

    # Verify data loaded correctly from file
    assert isinstance(loaded_config, dict)
    assert loaded_config["default_provider"] == "openai"
    assert loaded_config["default_model"] == "gpt-4o"
    assert loaded_config["api_keys"]["openai"].startswith("sk-")
    assert loaded_config["native_command_allowlist"] == ["git status", "ls -la"]
    assert loaded_config["max_tokens"] == 1500  # Check field from CodeAgentSettings


def test_load_config_file_not_exists(temp_config_path):
    """Test loading when config file doesn't exist (should create default)."""
    if temp_config_path.exists():
        temp_config_path.unlink()  # Ensure it doesn't exist

    # Mock create_default_config_file to avoid actual file creation/copy
    with patch("code_agent.config.settings_based_config.create_default_config_file") as mock_create:
        # Mock Path.exists used inside load_config_from_file
        with patch("pathlib.Path.exists", return_value=False):
            loaded_config = load_config_from_file(temp_config_path)

    mock_create.assert_called_once_with(temp_config_path)
    # Should return an empty dict when file doesn't exist and is mocked
    assert loaded_config == {}


def test_load_config_from_empty_file(temp_config_path):
    """Test loading configuration from an empty file."""
    temp_config_path.touch()  # Create empty file

    loaded_config = load_config_from_file(temp_config_path)
    assert loaded_config == {}  # Loading empty YAML returns None, which we convert to {}


# Patch standard print as that's what load_config_from_file uses
@patch("builtins.print")
def test_load_config_from_invalid_yaml(mock_print, temp_config_path):
    """Test loading configuration from a file with invalid YAML."""
    invalid_yaml_content = "default_provider: openai\n  invalid_yaml: ["  # Invalid YAML
    with open(temp_config_path, "w") as f:
        f.write(invalid_yaml_content)

    # The function should catch the error and return empty dict
    loaded_config = load_config_from_file(temp_config_path)
    assert loaded_config == {}

    # Check that a warning was printed
    mock_print.assert_called_once()
    # More specific check for the warning content
    args, kwargs = mock_print.call_args
    assert "Warning: Could not read config file" in args[0]
    assert "Error: mapping values are not allowed here" in args[0]


# --- Tests for Config File Creation ---


def test_create_default_config_file_copies_template(mocker, tmp_path):
    """Test creating default config when template exists (module patching)."""
    # Arrange
    config_path_str = str(tmp_path / ".config" / "code-agent" / "config.yaml")

    # Mock the TEMPLATE_CONFIG_PATH directly
    mock_template_instance = MagicMock(spec=Path)
    mock_template_instance.exists.return_value = True # Template exists
    mocker.patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH", mock_template_instance)

    # Keep other necessary mocks
    mock_copy2 = mocker.patch("shutil.copy2", autospec=True)
    mock_makedirs = mocker.patch("os.makedirs", autospec=True) # Keep in case logic changes
    mock_rich_print = mocker.patch("code_agent.config.settings_based_config.rich_print")

    # Act
    # Pass the string path, which shutil.copy2 handles
    create_default_config_file(config_path_str)

    # Assert
    # Check exists was called on the template mock
    mock_template_instance.exists.assert_called_once()

    mock_makedirs.assert_not_called()
    # copy2 should be called with the mock template instance and the config string path
    mock_copy2.assert_called_once_with(mock_template_instance, config_path_str)
    mock_rich_print.assert_not_called()


def test_create_default_config_file_creates_empty_if_no_template(mocker, tmp_path):
    """Test creating default config when template does NOT exist (module patching)."""
    # Arrange
    config_path_str = str(tmp_path / ".config" / "code-agent" / "config.yaml")

    # Mock the TEMPLATE_CONFIG_PATH directly
    mock_template_instance = MagicMock(spec=Path)
    mock_template_instance.exists.return_value = False # Template does NOT exist
    mocker.patch("code_agent.config.settings_based_config.TEMPLATE_CONFIG_PATH", mock_template_instance)

    # Keep other necessary mocks
    mock_makedirs = mocker.patch("os.makedirs", autospec=True)
    mock_yaml_dump = mocker.patch("yaml.dump", autospec=True)
    m_open = mock_open()
    mocker.patch("builtins.open", m_open)
    mock_rich_print = mocker.patch("code_agent.config.settings_based_config.rich_print")

    # Act
    # Pass the string path, which open() handles
    create_default_config_file(config_path_str)

    # Assert
    # Check exists was called on the template mock
    mock_template_instance.exists.assert_called_once()

    mock_makedirs.assert_not_called()
    # open should be called with the string path
    m_open.assert_called_once_with(config_path_str, "w")
    mock_yaml_dump.assert_called_once()
    dump_args, _ = mock_yaml_dump.call_args
    assert isinstance(dump_args[0], dict)
    assert dump_args[0]["default_provider"] == "ai_studio"
    assert dump_args[1] == m_open()
    mock_rich_print.assert_not_called()


# --- Tests for Building Effective Config ---


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_defaults(mock_load_config):
    """Test building config with only defaults."""
    mock_load_config.return_value = {} # Simulate no config file found or empty

    # Pass arguments individually as expected by the function signature
    effective_config = build_effective_config(
        config_file_path=DEFAULT_CONFIG_PATH, # Assuming default path if not specified
        # Pass None for CLI args not provided
        cli_provider=None,
        cli_model=None,
        cli_auto_approve_edits=None,
        cli_auto_approve_native_commands=None
    )

    # Check defaults from CodeAgentSettings
    assert isinstance(effective_config, CodeAgentSettings)
    assert effective_config.default_provider == "ai_studio" # Default from SettingsConfig/CodeAgentSettings
    assert effective_config.default_model == "gemini-2.0-flash"
    assert effective_config.max_tokens == 1000 # Default from CodeAgentSettings
    # Ensure api_keys is an ApiKeys instance even when defaults are used
    assert isinstance(effective_config.api_keys, ApiKeys)
    # Compare specific attributes to avoid model_dump linter issue
    api_keys: ApiKeys = effective_config.api_keys
    assert api_keys.openai is None
    assert api_keys.ai_studio is None
    assert api_keys.groq is None


@patch("code_agent.config.settings_based_config.load_config_from_file")
def test_build_effective_config_file_values(mock_load_config, valid_config_data):
    """Test building config using values from a loaded file."""
    mock_load_config.return_value = valid_config_data

    # Pass arguments individually
    effective_config = build_effective_config(
        config_file_path=DEFAULT_CONFIG_PATH, # Assuming default path
        cli_provider=None,
        cli_model=None,
        cli_auto_approve_edits=None,
        cli_auto_approve_native_commands=None
    )

    assert effective_config.default_provider == valid_config_data["default_provider"]
    assert effective_config.default_model == valid_config_data["default_model"]
    # Ensure api_keys is an ApiKeys instance when loaded from file
    assert isinstance(effective_config.api_keys, ApiKeys)
    api_keys: ApiKeys = effective_config.api_keys
    expected_keys_dict = valid_config_data["api_keys"]
    # Compare specific attributes
    assert api_keys.openai == expected_keys_dict["openai"]
    assert api_keys.ai_studio == expected_keys_dict["ai_studio"]
    assert api_keys.groq == expected_keys_dict["groq"]
    assert effective_config.max_tokens == valid_config_data["max_tokens"]


@pytest.mark.parametrize(
    "cli_args, expected_values_overrides", # Renamed second param
    [
        # Test overriding provider and model
        (
            {"default_provider": "cli_provider", "default_model": "cli_model"},
            # Only specify the fields *overridden* by CLI or expected to change
            {"default_provider": "cli_provider", "default_model": "cli_model"},
        ),
        # Test overriding auto_approve_edits
        (
            {"auto_approve_edits": True},
            {"auto_approve_edits": True},
        ),
         # Test overriding auto_approve_native_commands
        (
            {"auto_approve_native_commands": True},
            {"auto_approve_native_commands": True},
        ),
        # Test providing no overrides (no overrides specified)
        (
            {},
            {},
        ),
    ],
)
@patch("code_agent.config.settings_based_config.load_config_from_file")
@patch("code_agent.config.settings_based_config.rich_print")
def test_build_effective_config_cli_overrides(
    mock_rich_print, mock_load_config, cli_args, expected_values_overrides, valid_config_data # Fixture added
):
    """Test CLI arguments overriding file and default values."""
    mock_load_config.return_value = valid_config_data

    # Pass CLI args individually to build_effective_config
    config = build_effective_config(
        config_file_path=DEFAULT_CONFIG_PATH, # Assuming default path
        cli_provider=cli_args.get("default_provider"),
        cli_model=cli_args.get("default_model"),
        cli_auto_approve_edits=cli_args.get("auto_approve_edits"),
        cli_auto_approve_native_commands=cli_args.get("auto_approve_native_commands")
    )

    # Construct the full expected dictionary: start with file data, apply overrides
    full_expected_values = valid_config_data.copy()
    full_expected_values.update(expected_values_overrides) # Apply the overrides from parametrize

    # Check all expected values (excluding api_keys for now)
    for key, expected_value in full_expected_values.items():
        if key != "api_keys":
            assert getattr(config, key) == expected_value

    # Check API keys specifically - CLI overrides don't affect API keys in current build_effective_config
    api_keys = config.api_keys
    assert isinstance(api_keys, ApiKeys) # Explicit type check
    # Expected keys should always match the file data in this test setup
    expected_keys_dict = valid_config_data["api_keys"]

    # Use model_dump().get() for safety
    assert api_keys.model_dump().get("openai") == expected_keys_dict.get("openai")
    assert api_keys.model_dump().get("ai_studio") == expected_keys_dict.get("ai_studio")
    assert api_keys.model_dump().get("groq") == expected_keys_dict.get("groq")

    # Optionally, compare the whole object if needed
    expected_api_keys_obj = ApiKeys.model_validate(expected_keys_dict)
    assert api_keys == expected_api_keys_obj


@pytest.mark.parametrize(
    "env_vars, expected_values",
    [
        # Test overriding provider and model
        (
            {"CODE_AGENT_DEFAULT_PROVIDER": "env_provider", "CODE_AGENT_DEFAULT_MODEL": "env_model"},
            {"default_provider": "env_provider", "default_model": "env_model"},
        ),
        # Test overriding a nested API key
        (
            {"CODE_AGENT_API_KEYS__OPENAI": "env-openai-key"},
            {
                "api_keys": {
                    "openai": "env-openai-key", # Override
                    "ai_studio": "AIza" + "a" * 35, # From file
                    "groq": "gsk-" + "b" * 48, # From file
                }
            },
        ),
        # Test overriding max_tokens (needs conversion from string)
        (
            {"CODE_AGENT_MAX_TOKENS": "3000"},
            {"max_tokens": 3000}, # Should be int
        ),
        # Test adding a new API key via env
        (
             {"CODE_AGENT_API_KEYS__NEW_PROVIDER": "env-new-key"},
             {
                "api_keys": {
                    "openai": "sk-" + "a" * 48, # From file
                    "ai_studio": "AIza" + "a" * 35, # From file
                    "groq": "gsk-" + "b" * 48, # From file
                    "new_provider": "env-new-key", # Added
                }
             }
        )
    ],
)
@patch("code_agent.config.settings_based_config.load_config_from_file")
@patch("code_agent.config.settings_based_config.rich_print")
def test_build_effective_config_env_vars(
    mock_rich_print, mock_load_config, env_vars, expected_values, valid_config_data, monkeypatch # Added fixtures
):
    """Test environment variables overriding file and defaults."""
    # Set environment variables for the test duration
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    # Load config from file (base layer)
    mock_load_config.return_value = valid_config_data

    # Build config (will pick up env vars via Pydantic settings)
    config = build_effective_config(
        config_file_path=DEFAULT_CONFIG_PATH, # Assuming default path
        cli_provider=None, # No CLI overrides in this test
        cli_model=None,
        cli_auto_approve_edits=None,
        cli_auto_approve_native_commands=None
    )

    # Check all expected values, defaulting to file values if not in expected_values
    for key, file_value in valid_config_data.items():
        expected_value = expected_values.get(key, file_value) # Get override or fallback to file
        if key != "api_keys": # Skip api_keys comparison here
             assert getattr(config, key) == expected_value

    # Check API keys specifically
    api_keys = config.api_keys
    assert isinstance(api_keys, ApiKeys) # Explicit type check

    # Construct expected keys dict: start with file keys, override with env keys
    expected_keys_dict = valid_config_data["api_keys"].copy()
    if "api_keys" in expected_values:
        expected_keys_dict.update(expected_values["api_keys"])

    # Use model_dump().get() for safety
    assert api_keys.model_dump().get("openai") == expected_keys_dict.get("openai")
    assert api_keys.model_dump().get("ai_studio") == expected_keys_dict.get("ai_studio")
    assert api_keys.model_dump().get("groq") == expected_keys_dict.get("groq")
    # Check any potentially added keys
    if "new_provider" in expected_keys_dict:
        assert api_keys.model_dump().get("new_provider") == expected_keys_dict.get("new_provider")

    # Compare the whole object
    expected_api_keys_obj = ApiKeys.model_validate(expected_keys_dict)
    assert api_keys == expected_api_keys_obj

# Env vars override file, CLI overrides env vars
# Note: Test depends on structure in valid_config_data fixture
@patch("code_agent.config.settings_based_config.load_config_from_file")
@patch("code_agent.config.settings_based_config.rich_print") # Patch rich_print
def test_build_effective_config_all_layers(mock_rich_print, mock_load_config, valid_config_data, monkeypatch):
    """Test the layering: CLI > Env > File > Defaults."""
    # Arrange
    # 1. File Config (Base)
    mock_load_config.return_value = valid_config_data
    file_api_keys = valid_config_data["api_keys"]

    # 2. Environment Variables
    env_vars = {
        "CODE_AGENT_DEFAULT_PROVIDER": "env_provider",
        "CODE_AGENT_API_KEYS__AI_STUDIO": "env-aistudio-key", # Override file
        "CODE_AGENT_MAX_TOKENS": "3000",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    env_api_keys = {"ai_studio": env_vars["CODE_AGENT_API_KEYS__AI_STUDIO"]}


    # 3. CLI Arguments
    cli_args = {
        "default_model": "cli_model", # Override file (env didn't set)
        "default_provider": "cli_provider", # Override env
        "auto_approve_edits": True, # Override file
    }
    # Simulate how CLI might provide API keys if it were supported directly
    # For this test, we'll assume build_effective_config *could* take them if designed differently,
    # but standard build_effective_config does not. We test the actual behaviour.
    # We do NOT pass cli_api_keys to build_effective_config below.

    # Act - Pass CLI args individually
    config = build_effective_config(
        config_file_path=DEFAULT_CONFIG_PATH, # Assuming default path
        cli_provider=cli_args["default_provider"],
        cli_model=cli_args["default_model"],
        cli_auto_approve_edits=cli_args["auto_approve_edits"],
        cli_auto_approve_native_commands=None # Not set in CLI for this test
    )

    # Assert Layering
    # Provider: CLI > Env > File
    assert config.default_provider == cli_args["default_provider"]
    # Model: CLI > File (Env didn't set)
    assert config.default_model == cli_args["default_model"]
    # Max Tokens: Env > File
    assert config.max_tokens == 3000 # Comes from env
    # Auto Approve Edits: CLI > File
    assert config.auto_approve_edits == cli_args["auto_approve_edits"]
    # Auto Approve Native Commands: File (not set elsewhere)
    assert config.auto_approve_native_commands == valid_config_data["auto_approve_native_commands"]

    # Check API keys specifically (Env > File) - CLI doesn't override keys here
    api_keys = config.api_keys
    assert isinstance(api_keys, ApiKeys) # Explicit check

    # Construct expected based on Env > File
    expected_keys_dict = file_api_keys.copy()
    expected_keys_dict["ai_studio"] = env_api_keys["ai_studio"] # Env override

    # Use model_dump().get() for safety
    assert api_keys.model_dump().get("openai") == expected_keys_dict.get("openai") # From file
    assert api_keys.model_dump().get("ai_studio") == expected_keys_dict.get("ai_studio") # From Env
    assert api_keys.model_dump().get("groq") == expected_keys_dict.get("groq") # From file

    # Compare the final object
    expected_api_keys_obj = ApiKeys.model_validate(expected_keys_dict)
    assert api_keys == expected_api_keys_obj


@patch("code_agent.config.settings_based_config.load_config_from_file")
@patch.dict(os.environ, {"CODE_AGENT_MAX_TOKENS": "not-an-integer"}, clear=True) # Clear others, set invalid
def test_build_effective_config_validation_error(mock_load_config):
    """Test that build_effective_config raises ValidationError for invalid merged data (from env)."""
    mock_load_config.return_value = {} # No file config
    # Invalid data comes from environment variables via SettingsConfig

    with pytest.raises(ValidationError) as excinfo:
        build_effective_config(
            config_file_path=DEFAULT_CONFIG_PATH,
            cli_provider=None,
            cli_model=None,
            cli_auto_approve_edits=None,
            cli_auto_approve_native_commands=None
        )
    # Check the error details if needed
    assert "max_tokens" in str(excinfo.value) # Check that the error relates to max_tokens
    assert "Input should be a valid integer" in str(excinfo.value)


# --- Tests for Initialization and Global Access ---


# Remove patches for Path and create_default_config_file, as we mock build_effective_config
@patch("code_agent.config.config.build_effective_config")
@patch("code_agent.config.config._config", None) # Reset singleton before test
def test_initialize_config_calls_build(
    mock_build_effective_config, # Mock for build_effective_config
    # mocker # We can get mocker fixture implicitly if needed
):
    """Test initialize_config calls build_effective_config with correct args when singleton is None."""
    # Arrange
    # Mock the return value of build_effective_config
    mock_config_obj = CodeAgentSettings(default_provider="test_init_build")
    mock_build_effective_config.return_value = mock_config_obj

    # Define a dummy path and CLI args for the call
    dummy_path = Path("/fake/config.yaml")
    cli_args = {"cli_provider": "cli_test", "cli_model": "test_model"}

    # Act
    # Call initialize_config with the dummy path and CLI args
    initialize_config(
        config_file_path=dummy_path,
        cli_provider=cli_args["cli_provider"],
        cli_model=cli_args["cli_model"],
        cli_auto_approve_edits=None,      # Pass None if not provided
        cli_auto_approve_native_commands=None # Pass None if not provided
    )

    # Assert
    # Check that build_effective_config was called once with the expected arguments
    mock_build_effective_config.assert_called_once_with(
        config_file_path=dummy_path, # Check the path object was passed
        cli_provider="cli_test",
        cli_model="test_model",
        cli_auto_approve_edits=None,
        cli_auto_approve_native_commands=None
    )

    # Check the global config singleton was set correctly
    # Access the actual global variable for verification
    from code_agent.config.config import _config as global_config_singleton
    assert global_config_singleton is mock_config_obj


@patch("code_agent.config.config.build_effective_config")
def test_initialize_config_does_nothing_if_already_set(mock_build_effective_config):
    """Test initialize_config doesn't call build if singleton is already set."""
    # Arrange
    # Set the global singleton *before* the test function runs
    initial_config = CodeAgentSettings(default_provider="already_set")
    code_agent.config.config._config = initial_config

    # Act
    # Pass dummy args, they shouldn't matter
    initialize_config(config_file_path=Path("/another/fake/path"), cli_provider="other")

    # Assert
    mock_build_effective_config.assert_not_called()
    # Check the global singleton was not changed
    assert code_agent.config.config._config == initial_config

    # Cleanup: Reset the global singleton after the test
    code_agent.config.config._config = None


# Fixture to provide a mock config object for tests
@pytest.fixture
def mock_config_instance():
    return CodeAgentSettings(default_provider="mocked_for_get")

# Test get_config()
@patch("code_agent.config.config._config", None) # Ensure config is None initially
@patch("code_agent.config.config.initialize_config") # Mock initialize_config
def test_get_config_initializes_if_needed(mock_initialize_config, mock_config_instance):
    """Test get_config calls initialize_config if config is not set and uses its result."""
    # Arrange: Configure the mock initialize_config to set the global _config
    def side_effect_init(*args, **kwargs):
        code_agent.config.config._config = mock_config_instance

    mock_initialize_config.side_effect = side_effect_init

    # Act
    retrieved_config = get_config()

    # Assert
    mock_initialize_config.assert_called_once() # initialize_config was called
    assert retrieved_config == mock_config_instance # Returned the object set by initialize_config


@patch("code_agent.config.config._config") # Patch the global variable itself
def test_get_config_returns_existing_if_set(mock_config_global):
    """Test get_config returns the existing config if it's already set."""
    # Arrange
    existing_config = CodeAgentSettings(default_provider="existing")
    mock_config_global = existing_config # Set the patched global
    code_agent.config.config._config = existing_config # Also set the real one for consistency

    # Act
    retrieved_config = get_config()

    # Assert
    assert retrieved_config == existing_config
    # Ensure initialize_config was NOT called (implicitly checked by not patching it)

    # Cleanup
    code_agent.config.config._config = None

# Test for the RuntimeError case (though ideally unreachable if init is always called first)
@patch("code_agent.config.config._config", None) # Ensure config is None initially
@patch("code_agent.config.config.initialize_config") # Mock initialize_config
def test_get_config_raises_error_if_init_fails(mock_initialize_config):
    """Test get_config raises RuntimeError if initialize_config fails to set _config."""
    # Arrange: Mock initialize_config to *not* set the global _config
    mock_initialize_config.side_effect = lambda *args, **kwargs: None

    # Act & Assert
    with pytest.raises(RuntimeError, match="Configuration failed to initialize."):
        get_config()
    mock_initialize_config.assert_called_once()


# Ensure the return type hint for the actual get_config function is fixed
# (This requires editing the source file, not the test file)
