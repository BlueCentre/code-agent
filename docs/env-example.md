# Environment Configuration Example

To enable the PR validation features in the post-push hook, create a `.env` file in the repository root with the following configuration:

```bash
# Enable PR validation after git push
PULL_REQUEST_VALIDATE=true

# Enable waiting for CI/CD checks to complete
PULL_REQUEST_WAIT=true

# Maximum time to wait for checks (in minutes)
PULL_REQUEST_WAIT_MINUTES=10

# Polling interval (in seconds)
PULL_REQUEST_POLL_SECONDS=15
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `PULL_REQUEST_VALIDATE` | `false` | Enable PR validation in post-push hook |
| `PULL_REQUEST_WAIT` | `false` | Enable polling and waiting for checks to complete |
| `PULL_REQUEST_WAIT_MINUTES` | `10` | Maximum time to wait for checks (in minutes) |
| `PULL_REQUEST_POLL_SECONDS` | `15` | How often to check for updates (in seconds) |

## Usage

1. Copy the example above to a file named `.env` in your repository root
2. Adjust the values as needed for your workflow
3. Ensure you have the GitHub CLI installed and authenticated

The post-push hook will now validate your PR and optionally wait for CI/CD checks to complete after pushing changes. 