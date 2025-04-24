# Environment Configuration

This document describes all environment variables used in this project. Create a `.env` file in the repository root to set custom configuration values.

## PR Monitoring Configuration

These variables control the behavior of the PR monitoring script (`scripts/monitor-pr.sh`).

```bash
# Maximum time in minutes to wait for checks (default: 10)
PR_MONITOR_WAIT_MINUTES=10

# Polling interval in seconds (default: 15)
PR_MONITOR_POLL_SECONDS=15
```

The PR monitoring script checks GitHub pull request status and CI/CD checks after pushing changes. For more details, see [git_development.md](./git_development.md#pr-monitoring-and-validation).

## API Keys

Configure API keys for various services:

```bash
# Ollama API key (if using API authentication)
OLLAMA_API_KEY=your_key_here

# Google AI Studio API key (starts with "aip-")
AI_STUDIO_API_KEY=aip-your-key-here

# Default model to use with AI services
MODEL=gemini-2.5-pro-exp-03-25
```

## SonarQube Integration

Configure SonarQube integration for code quality analysis:

```bash
# SonarQube authentication token
SONAR_TOKEN=your_token_here

# SonarQube organization name
SONAR_ORGANIZATION=your_org_name
```

## Usage

1. Copy the example values to a new file named `.env` in the repository root
2. Replace placeholder values with your actual configuration
3. The application will automatically read these values at runtime

## Security Note

Never commit your `.env` file to version control. The `.env` file is included in `.gitignore` to prevent accidental commits of sensitive information. 