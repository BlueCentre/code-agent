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
- [Automated Quality Controls](#automated-quality-controls)
  - [Git Hooks Overview](#git-hooks-overview)
  - [Available Hooks](#available-hooks)
  - [Hook Installation](#hook-installation)
  - [Hook Configuration](#hook-configuration)
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
- [Customization and Advanced Usage](#customization-and-advanced-usage)

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

## Automated Quality Controls

### Git Hooks Overview

This repository uses a set of custom Git hooks to ensure code quality and provide a streamlined workflow. All hooks are implemented as simple bash scripts without external dependencies to ensure they work in any environment.

The hooks perform various checks such as lint validation, code formatting, and detecting potential security issues before committing or pushing changes.

### Available Hooks

#### pre-commit
The pre-commit hook runs before each commit and performs quick checks on your code:

- Scans Python files for large file sizes
- Detects debug print statements
- Checks for unresolved merge conflicts
- Runs ruff linting and formatting if available

Example output:
```
Running pre-commit hook...
✅ All files are within size limits
✅ No debug print statements found
✅ No merge conflicts detected
✅ Formatting looks good
Commit validation passed!
```

#### post-commit
The post-commit hook provides helpful information after each commit:

- Shows a summary of the commit (author, message, files changed)
- Provides hints about PR status
- Reminds you to push your changes
- Suggests using the PR monitoring script after pushing

Example output:
```
Commit successful!
Author: Your Name <your.email@example.com>
Message: feat: add new authentication feature

Files changed: 3 inserted, 1 deleted

Remember to push your changes and monitor your PR status:
  git push
  ./scripts/monitor-pr.sh
```

#### pre-push
The pre-push hook runs more thorough checks before pushing to the remote:

- Runs code formatting with ruff (if available)
- Performs linting checks on changed Python files
- Checks for large files in the commit
- Scans for potentially sensitive information (API keys, tokens, passwords)

Example output:
```
Running pre-push checks...
✅ Code formatting looks good
✅ Linting passed
✅ No large files detected
✅ No potential secrets found in changes
Push validation passed!
```

### Hook Installation

The Git hooks are stored in the `.githooks` directory in the repository. After cloning the repository, you need to install them using the provided script:

```bash
# Run the installation script
./scripts/install-hooks.sh
```

This script will copy the hooks to your local `.git/hooks` directory and make them executable.

#### Alternative Installation Methods

You can also configure Git to use the hooks directly from the repository:

```bash
# Tell Git to use hooks from the .githooks directory
git config core.hooksPath .githooks
```

This approach doesn't copy the hooks but uses them directly from the source location.

### Hook Configuration

For configuration options and environment variables:

* See [Environment Configuration](./env_configuration.md) for all available settings
* Hook behavior can be customized in your `.env` file

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

#### Git Hooks Issues

If you encounter issues with any of the hooks:

1. Make sure the hook scripts are executable
2. Check if you have the required tools installed (ruff, gh CLI)
3. Look for error messages in the hook output
4. If needed, temporarily disable a specific hook by renaming it (e.g., `mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled`)
5. Try reinstalling the hooks using `./scripts/install-hooks.sh`

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

#### Hook Functions Reference Table

| Hook | When It Runs | Key Checks | Bypass Flag |
|------|--------------|------------|-------------|
| pre-commit | Before commit is created | File size, debug statements, merge conflicts, formatting | `git commit --no-verify` |
| post-commit | After commit is created | N/A (informational only) | N/A |
| pre-push | Before changes are pushed | Code formatting, linting, large files, sensitive info | `git push --no-verify` |

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