# Git Hooks

This repository uses a set of custom Git hooks to ensure code quality and provide a streamlined workflow. All hooks are implemented as simple bash scripts without external dependencies to ensure they work in any environment.

## Available Hooks

### pre-commit
The pre-commit hook runs before each commit and performs quick checks on your code:

- Scans Python files for large file sizes
- Detects debug print statements
- Checks for unresolved merge conflicts
- Runs ruff linting and formatting if available

### post-commit
The post-commit hook provides helpful information after each commit:

- Shows a summary of the commit (author, message, files changed)
- Provides hints about PR status
- Reminds you to push your changes
- Suggests using the PR monitoring script after pushing

### pre-push
The pre-push hook runs more thorough checks before pushing to the remote:

- Runs code formatting with ruff (if available)
- Performs linting checks on changed Python files
- Checks for large files in the commit
- Scans for potentially sensitive information (API keys, tokens, passwords)

## PR Monitoring

Since Git doesn't provide a reliable post-push hook mechanism, we use a standalone script to monitor pull request status:

### monitor-pr.sh
The PR monitoring script can be run after pushing to check CI/CD status:

```bash
./scripts/monitor-pr.sh [branch-name]
```

This script:
- Finds the open PR for your branch
- Checks the current status of CI/CD checks
- Optionally polls and waits for checks to complete
- Shows detailed status of all checks (passed, failed, or pending)
- Provides direct links to GitHub for more information

## Setup

The Git hooks are automatically installed in the `.git/hooks` directory. Make sure they are executable:

```bash
chmod +x .git/hooks/pre-commit .git/hooks/post-commit .git/hooks/pre-push
```

Ensure the monitoring script is also executable:

```bash
chmod +x scripts/monitor-pr.sh
```

## Configuration

You can customize the PR monitoring script behavior by adding the following to your `.env` file:

```
PR_MONITOR_WAIT_MINUTES=10    # Maximum wait time in minutes (default: 10)
PR_MONITOR_POLL_SECONDS=15    # Polling interval in seconds (default: 15)
```

## Requirements

For PR monitoring functionality:

1. Install GitHub CLI if not already installed:
   - [GitHub CLI Installation](https://cli.github.com/manual/installation)
2. Authenticate GitHub CLI:
   ```
   gh auth login
   ```

## Disabling Hooks

If you need to bypass the hooks for a specific operation:

- Skip pre-commit checks: `git commit --no-verify`
- Skip pre-push checks: `git push --no-verify`

Note: It's generally not recommended to bypass these checks as they help maintain code quality.

## Troubleshooting

If you encounter issues with any of the hooks:

1. Make sure the hook scripts are executable
2. Check if you have the required tools installed (ruff, gh CLI)
3. Look for error messages in the hook output
4. If needed, temporarily disable a specific hook by renaming it (e.g., `mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled`)

## Performance

The hooks are designed to be fast and lightweight, with minimal dependencies. They should add very little overhead to your Git operations. 