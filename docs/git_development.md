# Git Development Workflow and Tools

This document provides a comprehensive guide to the Git development workflow, automated quality controls, and PR validation processes used in the Code Agent project.

## Table of Contents

- [Introduction](#introduction)
- [Git Workflow](#git-workflow)
  - [Branch Naming Convention](#branch-naming-convention)
  - [Helper Script](#helper-script)
  - [Commit Message Convention](#commit-message-convention)
  - [Development Workflow](#development-workflow)
  - [Working with PRs](#working-with-prs)
  - [Maintaining Clean History](#maintaining-clean-history)
  - [Handling Merge Conflicts](#handling-merge-conflicts)
- [Automated Quality Controls (Git Hooks)](#automated-quality-controls-git-hooks)
  - [Pre-Commit Framework](#pre-commit-framework)
  - [Configuration (`.pre-commit-config.yaml`)](#configuration-pre-commit-configyaml)
  - [Available Hooks](#available-hooks)
  - [Installation](#installation)
- [PR Monitoring and Validation](#pr-monitoring-and-validation)
  - [Requirements](#requirements)
  - [How It Works](#how-it-works)
  - [Usage](#usage)
  - [Configuration](#configuration)
- [Examples and Reference](#examples-and-reference)
  - [Common Commands](#common-commands)
  - [Example PR Descriptions](#example-pr-descriptions)
  - [Troubleshooting](#troubleshooting)
  - [Quick Reference](#quick-reference)

## Introduction

This project follows a standardized Git workflow and uses automated tools to ensure code quality and consistency. These practices help maintain a clean repository history, enable efficient code reviews, and ensure all code changes meet the project's quality standards before being merged.

The key components of our Git development process include:

1. A consistent branch naming and commit message format
2. Automated quality checks via Git hooks
3. Pull request validation and CI/CD monitoring
4. Squash merging to maintain a clean history

## Git Workflow

### Branch Naming Convention

All feature branches should follow this naming pattern:
```
<type>/<description>
```

Where `<type>` is one of:
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools and libraries

Examples:
- `feat/add-user-authentication`
- `fix/login-validation-error`
- `docs/update-installation-guide`

### Helper Script

A helper script is provided to create branches with the correct naming convention:

```bash
# Example usage:
./scripts/create-branch.sh feat user-authentication
```

This will:
1. Check that you're using a valid branch type
2. Switch to the main branch
3. Pull the latest changes
4. Create and checkout a new branch with the correct naming convention

### Commit Message Convention

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat: add user authentication system`
- `fix(login): resolve validation error on empty email`
- `docs: update installation instructions`

A pre-commit hook is configured to enforce this convention.

### Development Workflow

1. **Create a feature branch**
   ```bash
   ./scripts/create-branch.sh <type> <description>
   # or manually:
   git checkout -b <type>/<description> main
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "<type>: <description>"
   ```

3. **Push changes and create a Pull Request**
   ```bash
   git push -u origin <type>/<description>
   ```

4. **Create a Pull Request on GitHub**
   - Go to the repository on GitHub
   - Click "Compare & pull request"
   - Set the base branch to `main`
   - Provide a title and description following the commit format
   - The PR template will load automatically with sections for:
     - Description of changes
     - Type of change (bug fix, new feature, etc.)
     - Testing details
     - Checklist of requirements
   - Fill out all required sections of the template
   - Submit the pull request

5. **Code Review Process**
   - The PR will automatically run tests and add coverage reports as comments
   - At least one reviewer must approve the PR
   - All CI checks must pass
   - Code coverage must not drop below 80%

6. **Merging**
   - Once approved and all checks pass, the PR can be merged
   - Prefer "Squash and merge" to keep a clean history on the main branch

### Working with PRs

When a PR is opened:
1. The CI pipeline will run all tests and generate coverage reports
2. Test results and coverage will be posted as comments on the PR
3. Reviewers can see these reports directly in the PR

### Maintaining Clean History

- Rebase your branch before merging if needed:
  ```bash
  git checkout <type>/<description>
  git rebase main
  git push --force-with-lease
  ```
- Use `git rebase -i` to squash multiple commits if needed
- Avoid merge commits by using squash merges in the GitHub UI

### Handling Merge Conflicts

When merge conflicts occur:

1. **Fetch the latest changes from main**:
   ```bash
   git fetch origin main
   ```

2. **Rebase your branch on the latest main**:
   ```bash
   git rebase origin/main
   ```

3. **Resolve conflicts**:
   - Git will pause the rebase when it encounters conflicts
   - Edit the conflicted files to resolve the conflicts
   - Use `git status` to see which files have conflicts
   - After resolving, mark them as resolved with `git add <file>`
   - Continue the rebase with `git rebase --continue`

4. **Push the updated branch**:
   ```bash
   git push --force-with-lease
   ```

5. **Seeking help with complex conflicts**:
   - For complex conflicts, consider asking another team member for help
   - Use `git rebase --abort` to undo a rebase if you get stuck

## Automated Quality Controls (Git Hooks)

### Pre-Commit Framework

This repository uses the [pre-commit](https://pre-commit.com/) framework to manage and maintain multi-language Git hooks. It ensures that code quality checks (like linting, formatting, and simple validation) run automatically before you create a commit.

Using the framework provides several benefits:
- Manages hook installation and execution.
- Ensures hooks run consistently across developer environments.
- Simplifies adding and configuring hooks for various tools.

### Configuration (`.pre-commit-config.yaml`)

The specific hooks and their configurations are defined in the `.pre-commit-config.yaml` file at the root of the repository. This file specifies which tools to run (e.g., Ruff, Conventional Commit checker) and how they should operate.

### Available Hooks

The configured hooks typically perform checks such as:
- **Linting:** Using Ruff to check for Python code style issues (PEP 8) and potential errors.
- **Formatting:** Using Ruff to automatically format Python code to match project standards.
- **Commit Message Validation:** Ensuring commit messages adhere to the [Conventional Commits](https://www.conventionalcommits.org/) format.
- **Other Checks:** May include checks for large files, unresolved merge conflicts, or basic security checks.

Refer to the `.pre-commit-config.yaml` file for the exact list of active hooks.

### Installation

To enable the pre-commit hooks for your local repository, you need to install them once after cloning:

1. Ensure you have set up the development environment (including running `uv sync --all-extras` which installs the `pre-commit` package).
2. Run the installation command:
   ```bash
   uv run pre-commit install
   ```

This command installs the hooks into your `.git/hooks` directory. From this point on, the configured checks will run automatically whenever you run `git commit`.

If a hook fails, the commit will be aborted. You'll need to fix the issues reported by the hook (often formatting changes applied automatically) and `git add` the modified files before attempting the commit again.

To temporarily skip hooks for a specific commit (use with caution):
```bash
git commit --no-verify -m "Your commit message"
```

## PR Monitoring and Validation

This repository includes a script (`scripts/monitor-pr.sh`) to check the status of GitHub pull request checks after pushing changes. This provides immediate feedback on whether your CI/CD checks are passing without needing to manually check GitHub.

This script provides an alternative to a post-push hook, which Git doesn't natively support in a reliable way.

### Requirements

- GitHub CLI (`gh`) installed and authenticated.
  - Installation: [GitHub CLI Installation](https://cli.github.com/manual/installation)
  - Authentication: Run `gh auth login`

### How It Works

The `monitor-pr.sh` script is designed to be run manually after you push changes to a branch associated with an open pull request. The `post-commit` and `pre-push` Git hooks will remind you to use this script.

When executed, the script:

1. Identifies the open PR for your current branch.
2. Fetches the current status of all associated CI/CD checks (e.g., GitHub Actions workflows).
3. By default, it polls the GitHub API periodically to wait for checks to complete.
4. Displays the progress and final status (pass, fail, pending) of the checks.
5. Provides a direct link to the PR on GitHub.

### Usage

```bash
# Run after pushing changes to a branch with an open PR
./scripts/monitor-pr.sh

# Specify a branch explicitly if not on the PR branch
./scripts/monitor-pr.sh your-feature-branch

# Check status once without polling/waiting
./scripts/monitor-pr.sh --no-poll
```

### Configuration

You can customize the script's polling behavior by creating a `.env` file in the repository root with specific variables.

For complete environment configuration details, see [Environment Configuration](./env_configuration.md).

```dotenv
# .env
PR_MONITOR_WAIT_MINUTES=10    # Optional: Maximum time to wait (default: 10 minutes)
PR_MONITOR_POLL_SECONDS=15    # Optional: Polling interval (default: 15 seconds)
```

| Variable                    | Default | Description                                       |
| --------------------------- | ------- | ------------------------------------------------- |
| `PR_MONITOR_WAIT_MINUTES` | `10`    | Maximum time in minutes to wait for checks.     |
| `PR_MONITOR_POLL_SECONDS` | `15`    | How often (in seconds) to poll for status updates. |

*Note: The script reads these variables if the `.env` file exists.*

## Examples and Reference

### Common Commands

Below are common commands used in our Git workflow:

```bash
# Create a new feature branch
./scripts/create-branch.sh feat new-feature

# Check the status of your changes
git status

# Stage specific files
git add file1.py file2.py

# Stage all changes
git add .

# Commit with a conventional commit message
git commit -m "feat: implement user authentication"

# Push changes to remote
git push -u origin feat/new-feature

# Monitor PR checks after pushing
./scripts/monitor-pr.sh

# Rebase on latest main
git fetch origin main
git rebase origin/main

# Squash local commits before pushing
git rebase -i HEAD~3  # Squash the last 3 commits
```

### Example PR Descriptions

A good PR description follows this format:

```
feat: Add user authentication system

This PR implements the user authentication system with the following features:
- Email/password authentication
- Password reset functionality
- Account lockout after failed attempts

Resolves: #123
```

Another example with more details:

```
fix(security): Resolve XSS vulnerability in user input

## What's changed
- Added input sanitization to prevent XSS attacks
- Updated validation logic to reject potentially harmful inputs
- Added unit tests for the sanitization functions

## Testing performed
- Manual testing with various attack vectors
- Unit tests for all new sanitization functions
- Integration tests with the front-end components

Fixes: #456
```

### Troubleshooting

#### Git Hooks Issues (Pre-Commit Framework)

If you encounter issues with pre-commit hooks:

1. **Ensure `pre-commit` is installed:** Verify it's listed in `pyproject.toml` [dev] dependencies and `uv sync --all-extras` was successful.
2. **Ensure hooks are installed locally:** Run `uv run pre-commit install` again.
3. **Check `.pre-commit-config.yaml`:** Ensure the file is valid YAML and the hook configurations are correct.
4. **Update Hooks:** Sometimes hooks need updating. Run `uv run pre-commit autoupdate` and commit the changes to `.pre-commit-config.yaml`.
5. **Run hooks manually:** Test hooks on all files: `uv run pre-commit run --all-files`. Test on specific files: `uv run pre-commit run --files path/to/file.py`.
6. **Check Tool Installation:** Pre-commit installs tools in its own environment (`~/.cache/pre-commit`). If a specific tool fails (like Ruff), try clearing the cache (`pre-commit clean`) or investigate issues with that tool specifically.
7. **Look for error messages:** Carefully read the output when hooks fail.
8. **Bypass (Temporary):** Use `git commit --no-verify` if you absolutely need to bypass the checks temporarily.

#### PR Monitoring Issues

If you encounter issues with the PR monitoring script:

1. Ensure GitHub CLI is installed: `gh --version`
2. Verify GitHub CLI authentication: `gh auth status`
3. Confirm a PR exists for your branch: `gh pr list --head $(git branch --show-current)`
4. Check the script's output for specific error messages from `gh` or the script itself.

#### Common Git Errors

**"Failed to push some refs"**
```
error: failed to push some refs to 'origin/feat/feature-name'
hint: Updates were rejected because the remote contains work that you do not have locally.
```
Solution: Pull the latest changes from the remote:
```bash
git pull --rebase origin feat/feature-name
```

**Merge conflicts during rebase**
```
CONFLICT (content): Merge conflict in file.py
```
Solution: Resolve conflicts, then continue:
```bash
# Edit the file to resolve conflicts
git add file.py
git rebase --continue
```

### Quick Reference

#### Hook Functions Reference Table (Pre-Commit)

| Hook Trigger | When It Runs             | Key Checks (Examples - see config file) | Bypass Flag            |
|--------------|--------------------------|-----------------------------------------|------------------------|
| `pre-commit` | Before commit is created | Formatting, Linting, Commit Msg Format  | `git commit --no-verify` |
| `pre-push`   | Before changes are pushed| Can be configured, but often less used than pre-commit | `git push --no-verify` |
*Note: This project primarily relies on `pre-commit` stage hooks defined in `.pre-commit-config.yaml`.*

#### Branch Types Reference

| Type | Description | Example |
|------|-------------|---------|
| feat | New feature | `feat/user-auth` |
| fix | Bug fix | `fix/login-bug` |
| docs | Documentation | `docs/api-guide` |
| style | Formatting | `style/code-format` |
| refactor | Code restructuring | `refactor/auth-module` |
| perf | Performance | `perf/query-optimize` |
| test | Testing | `test/auth-unit-tests` |
| chore | Maintenance | `chore/dependency-update` |

# Git Development Workflow and Tools

This document provides a comprehensive guide to the Git development workflow, automated quality controls, and PR validation processes used in the Code Agent project.

## Table of Contents

- [Introduction](#introduction)
- [Git Workflow](#git-workflow)
  - [Branch Naming Convention](#branch-naming-convention)
  - [Helper Script](#helper-script)
  - [Commit Message Convention](#commit-message-convention)
  - [Development Workflow](#development-workflow)
  - [Working with PRs](#working-with-prs)
  - [Maintaining Clean History](#maintaining-clean-history)
  - [Handling Merge Conflicts](#handling-merge-conflicts)
- [Automated Quality Controls (Git Hooks)](#automated-quality-controls-git-hooks)
  - [Pre-Commit Framework](#pre-commit-framework)
  - [Configuration (`.pre-commit-config.yaml`)](#configuration-pre-commit-configyaml)
  - [Available Hooks](#available-hooks)
  - [Installation](#installation)
- [PR Monitoring and Validation](#pr-monitoring-and-validation)
  - [Requirements](#requirements)
  - [How It Works](#how-it-works)
  - [Usage](#usage)
  - [Configuration](#configuration)
- [Examples and Reference](#examples-and-reference)
  - [Common Commands](#common-commands)
  - [Example PR Descriptions](#example-pr-descriptions)
  - [Troubleshooting](#troubleshooting)
  - [Quick Reference](#quick-reference)

## Introduction

This project follows a standardized Git workflow and uses automated tools to ensure code quality and consistency. These practices help maintain a clean repository history, enable efficient code reviews, and ensure all code changes meet the project's quality standards before being merged.

The key components of our Git development process include:

1. A consistent branch naming and commit message format
2. Automated quality checks via Git hooks
3. Pull request validation and CI/CD monitoring
4. Squash merging to maintain a clean history

## Git Workflow

### Branch Naming Convention

All feature branches should follow this naming pattern:
```
<type>/<description>
```

Where `<type>` is one of:
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools and libraries

Examples:
- `feat/add-user-authentication`
- `fix/login-validation-error`
- `docs/update-installation-guide`

### Helper Script

A helper script is provided to create branches with the correct naming convention:

```bash
# Example usage:
./scripts/create-branch.sh feat user-authentication
```

This will:
1. Check that you're using a valid branch type
2. Switch to the main branch
3. Pull the latest changes
4. Create and checkout a new branch with the correct naming convention

### Commit Message Convention

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat: add user authentication system`
- `fix(login): resolve validation error on empty email`
- `docs: update installation instructions`

A pre-commit hook is configured to enforce this convention.

### Development Workflow

1. **Create a feature branch**
   ```bash
   ./scripts/create-branch.sh <type> <description>
   # or manually:
   git checkout -b <type>/<description> main
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "<type>: <description>"
   ```

3. **Push changes and create a Pull Request**
   ```bash
   git push -u origin <type>/<description>
   ```

4. **Create a Pull Request on GitHub**
   - Go to the repository on GitHub
   - Click "Compare & pull request"
   - Set the base branch to `main`
   - Provide a title and description following the commit format
   - The PR template will load automatically with sections for:
     - Description of changes
     - Type of change (bug fix, new feature, etc.)
     - Testing details
     - Checklist of requirements
   - Fill out all required sections of the template
   - Submit the pull request

5. **Code Review Process**
   - The PR will automatically run tests and add coverage reports as comments
   - At least one reviewer must approve the PR
   - All CI checks must pass
   - Code coverage must not drop below 80%

6. **Merging**
   - Once approved and all checks pass, the PR can be merged
   - Prefer "Squash and merge" to keep a clean history on the main branch

### Working with PRs

When a PR is opened:
1. The CI pipeline will run all tests and generate coverage reports
2. Test results and coverage will be posted as comments on the PR
3. Reviewers can see these reports directly in the PR

### Maintaining Clean History

- Rebase your branch before merging if needed:
  ```bash
  git checkout <type>/<description>
  git rebase main
  git push --force-with-lease
  ```
- Use `git rebase -i` to squash multiple commits if needed
- Avoid merge commits by using squash merges in the GitHub UI

### Handling Merge Conflicts

When merge conflicts occur:

1. **Fetch the latest changes from main**:
   ```bash
   git fetch origin main
   ```

2. **Rebase your branch on the latest main**:
   ```bash
   git rebase origin/main
   ```

3. **Resolve conflicts**:
   - Git will pause the rebase when it encounters conflicts
   - Edit the conflicted files to resolve the conflicts
   - Use `git status` to see which files have conflicts
   - After resolving, mark them as resolved with `git add <file>`
   - Continue the rebase with `git rebase --continue`

4. **Push the updated branch**:
   ```bash
   git push --force-with-lease
   ```

5. **Seeking help with complex conflicts**:
   - For complex conflicts, consider asking another team member for help
   - Use `git rebase --abort` to undo a rebase if you get stuck

## Automated Quality Controls (Git Hooks)

### Pre-Commit Framework

This repository uses the [pre-commit](https://pre-commit.com/) framework to manage and maintain multi-language Git hooks. It ensures that code quality checks (like linting, formatting, and simple validation) run automatically before you create a commit.

Using the framework provides several benefits:
- Manages hook installation and execution.
- Ensures hooks run consistently across developer environments.
- Simplifies adding and configuring hooks for various tools.

### Configuration (`.pre-commit-config.yaml`)

The specific hooks and their configurations are defined in the `.pre-commit-config.yaml` file at the root of the repository. This file specifies which tools to run (e.g., Ruff, Conventional Commit checker) and how they should operate.

### Available Hooks

The configured hooks typically perform checks such as:
- **Linting:** Using Ruff to check for Python code style issues (PEP 8) and potential errors.
- **Formatting:** Using Ruff to automatically format Python code to match project standards.
- **Commit Message Validation:** Ensuring commit messages adhere to the [Conventional Commits](https://www.conventionalcommits.org/) format.
- **Other Checks:** May include checks for large files, unresolved merge conflicts, or basic security checks.

Refer to the `.pre-commit-config.yaml` file for the exact list of active hooks.

### Installation

To enable the pre-commit hooks for your local repository, you need to install them once after cloning:

1. Ensure you have set up the development environment (including running `uv sync --all-extras` which installs the `pre-commit` package).
2. Run the installation command:
   ```bash
   uv run pre-commit install
   ```

This command installs the hooks into your `.git/hooks` directory. From this point on, the configured checks will run automatically whenever you run `git commit`.

If a hook fails, the commit will be aborted. You'll need to fix the issues reported by the hook (often formatting changes applied automatically) and `git add` the modified files before attempting the commit again.

To temporarily skip hooks for a specific commit (use with caution):
```bash
git commit --no-verify -m "Your commit message"
```

## PR Monitoring and Validation

This repository includes a script (`scripts/monitor-pr.sh`) to check the status of GitHub pull request checks after pushing changes. This provides immediate feedback on whether your CI/CD checks are passing without needing to manually check GitHub.

This script provides an alternative to a post-push hook, which Git doesn't natively support in a reliable way.

### Requirements

- GitHub CLI (`gh`) installed and authenticated.
  - Installation: [GitHub CLI Installation](https://cli.github.com/manual/installation)
  - Authentication: Run `gh auth login`

### How It Works

The `monitor-pr.sh` script is designed to be run manually after you push changes to a branch associated with an open pull request. The `post-commit` and `pre-push` Git hooks will remind you to use this script.

When executed, the script:

1. Identifies the open PR for your current branch.
2. Fetches the current status of all associated CI/CD checks (e.g., GitHub Actions workflows).
3. By default, it polls the GitHub API periodically to wait for checks to complete.
4. Displays the progress and final status (pass, fail, pending) of the checks.
5. Provides a direct link to the PR on GitHub.

### Usage

```bash
# Run after pushing changes to a branch with an open PR
./scripts/monitor-pr.sh

# Specify a branch explicitly if not on the PR branch
./scripts/monitor-pr.sh your-feature-branch

# Check status once without polling/waiting
./scripts/monitor-pr.sh --no-poll
```

### Configuration

You can customize the script's polling behavior by creating a `.env` file in the repository root with specific variables.

For complete environment configuration details, see [Environment Configuration](./env_configuration.md).

```dotenv
# .env
PR_MONITOR_WAIT_MINUTES=10    # Optional: Maximum time to wait (default: 10 minutes)
PR_MONITOR_POLL_SECONDS=15    # Optional: Polling interval (default: 15 seconds)
```

| Variable                    | Default | Description                                       |
| --------------------------- | ------- | ------------------------------------------------- |
| `PR_MONITOR_WAIT_MINUTES` | `10`    | Maximum time in minutes to wait for checks.     |
| `PR_MONITOR_POLL_SECONDS` | `15`    | How often (in seconds) to poll for status updates. |

*Note: The script reads these variables if the `.env` file exists.*

## Examples and Reference

### Common Commands

Below are common commands used in our Git workflow:

```bash
# Create a new feature branch
./scripts/create-branch.sh feat new-feature

# Check the status of your changes
git status

# Stage specific files
git add file1.py file2.py

# Stage all changes
git add .

# Commit with a conventional commit message
git commit -m "feat: implement user authentication"

# Push changes to remote
git push -u origin feat/new-feature

# Monitor PR checks after pushing
./scripts/monitor-pr.sh

# Rebase on latest main
git fetch origin main
git rebase origin/main

# Squash local commits before pushing
git rebase -i HEAD~3  # Squash the last 3 commits
```

### Example PR Descriptions

A good PR description follows this format:

```
feat: Add user authentication system

This PR implements the user authentication system with the following features:
- Email/password authentication
- Password reset functionality
- Account lockout after failed attempts

Resolves: #123
```

Another example with more details:

```
fix(security): Resolve XSS vulnerability in user input

## What's changed
- Added input sanitization to prevent XSS attacks
- Updated validation logic to reject potentially harmful inputs
- Added unit tests for the sanitization functions

## Testing performed
- Manual testing with various attack vectors
- Unit tests for all new sanitization functions
- Integration tests with the front-end components

Fixes: #456
```

### Troubleshooting

#### Git Hooks Issues (Pre-Commit Framework)

If you encounter issues with pre-commit hooks:

1. **Ensure `pre-commit` is installed:** Verify it's listed in `pyproject.toml` [dev] dependencies and `uv sync --all-extras` was successful.
2. **Ensure hooks are installed locally:** Run `uv run pre-commit install` again.
3. **Check `.pre-commit-config.yaml`:** Ensure the file is valid YAML and the hook configurations are correct.
4. **Update Hooks:** Sometimes hooks need updating. Run `uv run pre-commit autoupdate` and commit the changes to `.pre-commit-config.yaml`.
5. **Run hooks manually:** Test hooks on all files: `uv run pre-commit run --all-files`. Test on specific files: `uv run pre-commit run --files path/to/file.py`.
6. **Check Tool Installation:** Pre-commit installs tools in its own environment (`~/.cache/pre-commit`). If a specific tool fails (like Ruff), try clearing the cache (`pre-commit clean`) or investigate issues with that tool specifically.
7. **Look for error messages:** Carefully read the output when hooks fail.
8. **Bypass (Temporary):** Use `git commit --no-verify` if you absolutely need to bypass the checks temporarily.

#### PR Monitoring Issues

If you encounter issues with the PR monitoring script:

1. Ensure GitHub CLI is installed: `gh --version`
2. Verify GitHub CLI authentication: `gh auth status`
3. Confirm a PR exists for your branch: `gh pr list --head $(git branch --show-current)`
4. Check the script's output for specific error messages from `gh` or the script itself.

#### Common Git Errors

**"Failed to push some refs"**
```
error: failed to push some refs to 'origin/feat/feature-name'
hint: Updates were rejected because the remote contains work that you do not have locally.
```
Solution: Pull the latest changes from the remote:
```bash
git pull --rebase origin feat/feature-name
```

**Merge conflicts during rebase**
```
CONFLICT (content): Merge conflict in file.py
```
Solution: Resolve conflicts, then continue:
```bash
# Edit the file to resolve conflicts
git add file.py
git rebase --continue
```

### Quick Reference

#### Hook Functions Reference Table (Pre-Commit)

| Hook Trigger | When It Runs             | Key Checks (Examples - see config file) | Bypass Flag            |
|--------------|--------------------------|-----------------------------------------|------------------------|
| `pre-commit` | Before commit is created | Formatting, Linting, Commit Msg Format  | `git commit --no-verify` |
| `pre-push`   | Before changes are pushed| Can be configured, but often less used than pre-commit | `git push --no-verify` |
*Note: This project primarily relies on `pre-commit` stage hooks defined in `.pre-commit-config.yaml`.*

#### Branch Types Reference

| Type | Description | Example |
|------|-------------|---------|
| feat | New feature | `feat/user-auth` |
| fix | Bug fix | `fix/login-bug` |
| docs | Documentation | `docs/api-guide` |
| style | Formatting | `style/code-format` |
| refactor | Code restructuring | `refactor/auth-module` |
| perf | Performance | `perf/query-optimize` |
| test | Testing | `test/auth-unit-tests` |
| chore | Maintenance | `chore/dependency-update` |

## Customization and Advanced Usage

### Customizing Hook Behavior

You can customize the behavior of the Git hooks by creating or modifying environment variables in your `.env` file:

```bash
# .env
SKIP_LARGE_FILE_CHECK=true  # Skip the large file check in pre-commit
LINT_LEVEL=warning          # Only treat errors as failures, not warnings
```

### Integration with Testing Framework

The hooks integrate with the project's testing framework as follows:

1. The pre-push hook can optionally run basic tests before pushing
2. After pushing, the PR monitoring script tracks the full test suite running in CI
3. For more information about testing, see [Testing](testing.md)

### Bypassing Hooks

While not recommended, you can bypass hooks for specific operations:

- Skip pre-commit checks: `git commit --no-verify`
- Skip pre-push checks: `git push --no-verify`

**⚠️ WARNING**: Bypassing these checks may lead to lower code quality, failing CI checks, and delayed PR approvals. Only use these options in exceptional circumstances.

If you frequently need to bypass certain checks, consider addressing the underlying issues or customizing the hook behavior using environment variables instead. 