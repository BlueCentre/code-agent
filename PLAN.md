# Code Agent Project Plan

> **Note**: Future enhancements from this document have been consolidated into the main task list at [docs/planning_priorities.md](docs/planning_priorities.md). Please refer to that file for the current list of planned improvements, prioritized tasks, and future enhancements.

## Current Status: ADK CLI Rewrite

We are currently implementing the rewrite of the CLI to integrate with Google's Agent Development Kit (ADK) as outlined in [docs/planning_adk_interface_migration.md](docs/planning_adk_interface_migration.md).

### Completed:
- ✅ **Milestone 1: Core Setup & Basic ADK `run` Integration**
  - Created new CLI structure with Typer app
  - Implemented basic ADK agent loading and execution
  - Integrated with configuration system

- ✅ **Milestone 2: Enhanced `run` Command with Rich & Progress** (Partial)
  - Added Typer arguments/options to `run` command
  - Integrated Rich for console output formatting
  - Added progress indicators for agent execution
  - Implemented interactive mode and session management
  - Added support for default_agent_path from config

### In Progress:
- 🔄 **Milestone 2: Enhanced `run` Command with Rich & Progress** (Completion)
  - Create comprehensive test suite for the `run` command
  - Refine error handling and user feedback

### Next Steps:
- 🔜 **Milestone 3: `web` and `fastapi` Commands Integration**
  - Implement `web` command using ADK browser module
  - Implement `fastapi` command using ADK FastAPI module
  - Ensure configuration is properly passed to ADK
  - Create tests for new commands

- 🔜 **Milestone 4: Configuration & Multi-Model Provider Integration**
  - Refine configuration integration with ADK
  - Test support for different model providers (Gemini, LiteLLM)
  - Ensure seamless model switching based on config
  - Add provider-specific commands if needed

## Test Plan
- Create new unit tests for `run` command functionality
- Create integration tests for ADK agent execution
- Create tests for configuration integration
- Test model provider integration
- Maintain 80% test coverage

## Legacy Notes

### 1. Introduction & Vision

This document outlines the plan for building a versatile Command-Line Interface (CLI) tool designed to enhance developer productivity by leveraging AI language models directly within the terminal.

**Vision:** To create a powerful, flexible CLI tool that allows users to leverage various AI language models for tasks such as code generation, explanation, refactoring, terminal command assistance, and general question answering, directly within the terminal environment.

**Core Goal:** Provide a unified interface to interact with multiple AI model providers (supporting the OpenAI API standard) and empower the agent with capabilities to interact with the user's local environment (files, terminal commands) in a controlled and secure manner.

### 2. Configuration Hierarchy
Prioritize configuration settings: CLI flags > Environment Variables > config.yaml file (e.g., ~/.config/code-agent/config.yaml).

### 3. Build & Development Process

#### 3.1 Environment Management
- Support both Poetry (standard) and UV (enhanced speed) for dependency management
- Maintain a standardized virtual environment structure (.venv)
- Provide user-friendly setup scripts for easy onboarding

#### 3.2 Testing Framework
- Maintain comprehensive test suite with pytest
- Enforce 80% minimum test coverage
- Support both unit and integration testing
- Provide specialized test targets for focused testing

#### 3.3 CI/CD Pipeline
- Use GitHub Actions for automated testing
- Leverage UV for faster dependency installation in CI
- Maintain SonarCloud integration for code quality metrics

## Future Enhancements

> **Note**: All future enhancements have been moved to the consolidated priority task list at [docs/planning_priorities.md](docs/planning_priorities.md) under the "Future Enhancements" section.
