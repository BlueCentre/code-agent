# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-01

### Added
- Enhanced software engineer agent with specialized sub-agents:
  - Code Quality agent for linting and best practices
  - Improved Code Review capabilities
  - Enhanced Debugging sub-agent
  - Design Pattern recommendations
  - Improved DevOps assistant
  - Documentation generation
  - Testing support with framework detection
- New code analysis tools and capabilities in the software engineer agent
- Additional end-to-end test coverage for CLI commands and integrations

### Changed
- Improved CI/CD pipeline with uv build and publish workflows
- Enhanced GitHub Actions with trusted publishing support
- Updated documentation to reflect current features and usage
- Reorganized agent prompts for better specialized assistance
- Strengthened security in command execution

### Fixed
- Multiple end-to-end test pipeline issues
- Corrected license specifier in package metadata
- Fixed versioning mechanism to properly display CLI version
- Improved error handling across various modules

### Security
- Added secure token management for package publishing
- Enhanced validation of file operations

## [0.1.3] - 2025-04-29

### Added
- Feature: Migration to Google ADK (#18)
- Feature: Add web search tool using duckduckgo-search (#16)
- Feature (workflow-pipelines): Add PR validation documentation and feature (#15)
- Chore: Migrate Dev and Testing Setup to uv (#14)
- Add E2E test scripts for basic commands, file operations, Ollama, and providers
- Add test mode to Ollama commands
- Add thinking indicator and step-by-step output for complex operations (#10)

### Changed
- Update documentation to reflect current codebase
- Update and reorganize README
- Update pyproject.toml
- Enhance agent prompt
- Improve test coverage and implement Ollama integration (#12)
- Improve e2e with advanced tests

### Fixed
- Fix CLI test assertions to include quiet parameter in run_turn calls
- Fix E2E test failure by adding specific handler for arithmetic test case
- Fix E2E tests for JSON output, API key error handling, and context maintenance
- Fix e2e test? 
- Fix e2e pipeline #2
- Fix e2e pipeline #1

### Docs
- Final revised plan for google adk
- Additional planning refinements
- Additional planning for adk
- Update planning
- Fixing diagram 3
- Fixing diagram 2
- Fixing diagram 1
- Plans to migrate to google-adk fully
- Additional prompts
- Yet more updates =)
- Addional docs restructuring
- More updates to consolidate
- Capture useful prompts
- Minor updates renaming
- Updated docs 2025-04-23
- Additional instructions to our web_search planning
- Add plans for web_search tool

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
