# PR Validation Hook

This repository includes an optional Git hook that validates GitHub pull request checks after pushing changes. This provides immediate feedback on whether your CI/CD checks are passing, without needing to manually check GitHub.

## Requirements

- GitHub CLI (`gh`) installed and authenticated
- A `.env` file with `PULL_REQUEST_VALIDATE=true`

## How It Works

After pushing changes to a branch with an open PR, the hook:

1. Checks if the feature is enabled via the `.env` file
2. Verifies GitHub CLI is installed and authenticated
3. Identifies any open PR for the current branch
4. Polls GitHub API to check CI/CD status
5. Notifies you when all checks pass or when any fail

The validation runs in the background to avoid blocking your workflow.

## Git Hook Flow

This repository uses a series of Git hooks to ensure code quality:

1. **Pre-commit hook**: Runs linting, formatting checks, and basic validation
2. **Pre-push hook**: Runs tests and ensures code quality before pushing
3. **Post-push hook**: Validates PR checks after pushing (when enabled)

## Setup

1. Create a `.env` file in the repository root (if it doesn't exist)
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

## Configuration

The hook has the following default behavior:
- Polls GitHub API every 5 seconds
- Shows status updates every 30 seconds
- Times out after 10 minutes
- Runs asynchronously in the background

## Troubleshooting

If you encounter issues:

1. Check that GitHub CLI is properly installed: `gh --version`
2. Verify authentication: `gh auth status`
3. Confirm your PR exists: `gh pr list --head $(git branch --show-current)`
4. Check your `.env` file has `PULL_REQUEST_VALIDATE=true`
