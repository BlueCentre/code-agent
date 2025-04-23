# Contributing to Code Agent

Thank you for your interest in contributing to Code Agent! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct (to be created).

## Getting Started

### Setup Development Environment

We recommend using [`uv`](https://github.com/astral-sh/uv) for faster dependency management. If you don't have it, install it first (see [README Quick Start](../README.md#quick-start)).

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/code-agent.git
   cd code-agent
   ```
3. **Create virtual environment and install dependencies (Recommended: using `uv`)**:
   ```bash
   # 1. Create the virtual environment
   uv venv .venv

   # 2. Activate the environment (Linux/macOS)
   source .venv/bin/activate
   #    Activate the environment (Windows - Command Prompt/PowerShell)
   #    .venv\Scripts\activate

   # 3. Install dependencies (including development extras)
   uv pip install '.[dev]'
   ```
4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

**Alternative Setup (using `poetry`):**

If you prefer not to use `uv`:

1. **Follow steps 1 & 2 above (Fork & Clone).**
2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install poetry # Ensure poetry is installed
   poetry install     # Installs main and development dependencies
   ```
4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Creating a Feature Branch

We use a structured branch naming convention:

```bash
# Create a new branch using our helper script
./scripts/create-branch.sh <type> <description>

# Example:
./scripts/create-branch.sh feat add-pagination
```

Where `<type>` is one of:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Changes that don't affect code function (formatting, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Code change that improves performance
- `test`: Adding or modifying tests
- `chore`: Changes to build process or auxiliary tools

## Development Workflow

### Coding Standards

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Add docstrings to all functions, classes, and modules
- Keep functions focused and small
- Write tests for all new functionality

### Testing Requirements

- All code should be tested
- Maintain minimum 80% test coverage
- Run tests locally before submitting a PR
- Create both unit tests and integration tests where appropriate

To run tests:

```bash
# Run all tests
./scripts/run_tests.sh

# Run tests with coverage reporting
./scripts/run_coverage_pipeline_venv.sh
```

### Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Example:
```
feat(file-tools): add pagination to read_file tool

Implements page size limits and offset controls to handle large files.
The default max size is 1MB or 1000 lines, configurable in settings.

Closes #123
```

## Pull Request Process

1. **Create a Pull Request** from your feature branch to the main repository
2. **Fill out the PR template** with a description of changes, related issues, etc.
3. **Ensure all checks pass** (tests, code coverage, linting)
4. **Request review** from at least one maintainer
5. **Address feedback** from reviewers
6. **Squash merge** once approved (this will be done by maintainers)

### PR Requirements

- PRs must include appropriate tests
- Documentation must be updated for any user-facing changes
- Code coverage cannot drop below 80%
- All CI checks must pass

## Documentation

When adding new features, please update the documentation:

- Add or update documentation in the `docs/` directory
- Update the relevant sections in README.md if applicable
- Include examples of how to use new features

## Feature Development

When developing major new features:

1. First open an issue to discuss the feature
2. Create a design document if the feature is complex
3. Break the implementation into smaller PRs when possible
4. Add appropriate tests and documentation

## Getting Help

If you need help during the contribution process:

- Open a discussion on GitHub
- Ask questions in the issue you're working on
- Contact the maintainers directly

Thank you for contributing to Code Agent!
