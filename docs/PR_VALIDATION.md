# PR Monitoring Script (`monitor-pr.sh`)

This repository includes a script (`scripts/monitor-pr.sh`) to check the status of GitHub pull request checks after pushing changes. This provides immediate feedback on whether your CI/CD checks are passing without needing to manually check GitHub.

This script replaces the previous experimental post-push hook validation.

## Requirements

- GitHub CLI (`gh`) installed and authenticated.
  - Installation: [GitHub CLI Installation](https://cli.github.com/manual/installation)
  - Authentication: Run `gh auth login`

## How It Works

The `monitor-pr.sh` script is designed to be run manually after you push changes to a branch associated with an open pull request. The `post-commit` and `pre-push` Git hooks will remind you to use this script.

When executed, the script:

1.  Identifies the open PR for your current branch.
2.  Fetches the current status of all associated CI/CD checks (e.g., GitHub Actions workflows).
3.  By default, it polls the GitHub API periodically to wait for checks to complete.
4.  Displays the progress and final status (pass, fail, pending) of the checks.
5.  Provides a direct link to the PR on GitHub.

## Usage

```bash
# Run after pushing changes to a branch with an open PR
./scripts/monitor-pr.sh

# Specify a branch explicitly if not on the PR branch
./scripts/monitor-pr.sh your-feature-branch

# Check status once without polling/waiting
./scripts/monitor-pr.sh --no-poll
```

## Configuration

You can customize the script's polling behavior by creating a `.env` file in the repository root with specific variables.

For complete environment configuration details, see [Environment Configuration](./ENV_CONFIGURATION.md).

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

## Troubleshooting

If you encounter issues with the script:

1.  Ensure GitHub CLI is installed: `gh --version`
2.  Verify GitHub CLI authentication: `gh auth status`
3.  Confirm a PR exists for your branch: `gh pr list --head $(git branch --show-current)`
4.  Check the script's output for specific error messages from `gh` or the script itself.
