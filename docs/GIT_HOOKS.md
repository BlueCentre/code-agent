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

### pre-push
The pre-push hook runs more thorough checks before pushing to the remote:

- Runs code formatting with ruff (if available)
- Performs linting checks on changed Python files
- Checks for large files in the commit
- Scans for potentially sensitive information (API keys, tokens, passwords)

### post-push
The post-push hook validates GitHub PR status after pushing changes:

- Checks if PR validation is enabled in `.env` via `PULL_REQUEST_VALIDATE=true`
- Identifies open PRs for the current branch
- Checks the current status of CI/CD checks
- Can optionally poll and wait for checks to complete (configurable timeout)
- Shows you the status of all checks (passed, failed, or pending)

## Setup

These hooks are automatically installed in the `.git/hooks` directory. Make sure they are executable:

```bash
chmod +x .git/hooks/pre-commit .git/hooks/post-commit .git/hooks/pre-push .git/hooks/post-push
```

## Enabling PR Validation

To enable automatic PR validation after pushing changes:

1. Create a `.env` file in the repository root (copy from `.env.example`)
2. Add the following line to enable validation:
   ```
   PULL_REQUEST_VALIDATE=true
   ```
3. Install GitHub CLI if not already installed:
   - [GitHub CLI Installation](https://cli.github.com/manual/installation)
4. Authenticate GitHub CLI:
   ```
   gh auth login
   ```

### Waiting for CI/CD Checks

To enable polling for CI/CD check completion:

1. Add the following to your `.env` file:
   ```
   PULL_REQUEST_WAIT=true
   ```
   
2. Optionally configure wait time and polling interval:
   ```
   PULL_REQUEST_WAIT_MINUTES=10    # Maximum wait time in minutes (default: 10)
   PULL_REQUEST_POLL_SECONDS=15    # Polling interval in seconds (default: 15)
   ```

See the `.env.example` file in the root directory for a complete example.

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