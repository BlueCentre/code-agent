# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2024-07-22

### Added
- Support for tools/function calling in LLM integration.
- Timeout and working directory options for native tool execution.
- Use of `pydantic-settings` for more robust environment variable handling in configuration.
- Dynamic configuration validation with clearer error messages.
- "Thinking indicator" and step-by-step output for complex operations.
- Added tests for the 'chat' command.
- Completed tests for LLM interactions using mocked responses and tool calls.

### Changed
- Improved test coverage, particularly for edge cases in tools (Current: 80%).
- Refined error handling and user feedback across API errors, tool failures, configuration issues, and LLM runtime errors.
- Implemented more informative error messages specifically for file operation failures.
- Updated test assertions to align with the new error message format.
- Enhanced security checks for `apply_edit` and `run_native_command` (e.g., stricter path validation).
- Added size limits and pagination capabilities to the `read_file` tool.
- Fully implemented the CLI > Environment Variable > Configuration File hierarchy for all settings.
- Enhanced confirmation prompts to provide more context and better diff highlighting.

### Fixed
- (No specific fixes noted, included in general error handling refinements)

## [0.1.1] - 2024-12-07

### Added
- Shell completion support via `--install-completion` and `--show-completion` flags
- Automatic SonarCloud version reporting in CI pipeline
- Release documentation in `docs/release.md`

### Changed
- Improved version management by using `importlib.metadata` to read version from a single source
- CLI now shows help text when run without any arguments, instead of showing an error

### Fixed
- Fixed error when running the CLI without any arguments

## [0.1.0] - Initial Release

### Added
- Initial release of CLI Code Agent
- Support for multiple LLM providers: OpenAI, Anthropic, Google AI Studio, Groq
- Interactive chat mode
- Command execution capability
- File editing functionality
- Configuration management
