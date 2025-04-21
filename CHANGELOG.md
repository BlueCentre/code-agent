# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
