#!/bin/bash

# PR Monitor Script
# Run this after pushing to monitor CI/CD check status
# Usage: ./scripts/monitor-pr.sh [branch-name] [--no-poll]

# Process arguments
BRANCH_NAME=""
AUTO_POLL=true

for arg in "$@"; do
  if [[ "$arg" == "--no-poll" ]]; then
    AUTO_POLL=false
  elif [[ -z "$BRANCH_NAME" && "$arg" != --* ]]; then
    BRANCH_NAME="$arg"
  fi
done

# Function to check if command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for GitHub CLI
if ! command_exists gh; then
    echo "❌ GitHub CLI not found. This script requires the 'gh' command."
    echo "   To install: https://cli.github.com/manual/installation"
    exit 1
fi

# Check gh authentication
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI not authenticated. Please login with 'gh auth login'"
    exit 1
fi

# Get branch name from argument or current branch
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
fi

# Get repository info
REMOTE_URL=$(git remote get-url origin)
if [[ "$REMOTE_URL" =~ github.com[/:](.*)(\.git)?$ ]]; then
    REPO_NAME="${BASH_REMATCH[1]}"
else
    echo "❌ Unable to determine GitHub repository from remote URL."
    exit 1
fi

echo "🔍 Looking for open PR from branch $BRANCH_NAME..."

# Get PR number
PR_JSON=$(gh pr list --head "$BRANCH_NAME" --json number,title,url 2>/dev/null)
PR_NUMBER=$(echo "$PR_JSON" | sed -n 's/.*"number":\s*\([0-9]*\).*/\1/p')

if [ -z "$PR_NUMBER" ]; then
    echo "ℹ️ No open PR found for branch $BRANCH_NAME."
    echo "   Create a PR first using: gh pr create"
    exit 0
fi

PR_TITLE=$(echo "$PR_JSON" | sed -n 's/.*"title":\s*"\([^"]*\)".*/\1/p')
PR_URL=$(echo "$PR_JSON" | sed -n 's/.*"url":\s*"\([^"]*\)".*/\1/p')
echo "📊 Found PR #$PR_NUMBER: \"$PR_TITLE\""
echo "   URL: $PR_URL"

# Configure polling
MAX_WAIT_MINUTES=10
POLL_INTERVAL_SECONDS=15

# Load configuration from .env if exists
if [ -f .env ]; then
    # Get custom wait time if set
    CUSTOM_WAIT=$(grep "PR_MONITOR_WAIT_MINUTES=" .env 2>/dev/null | cut -d'=' -f2)
    if [[ "$CUSTOM_WAIT" =~ ^[0-9]+$ ]]; then
        MAX_WAIT_MINUTES=$CUSTOM_WAIT
    fi
    
    # Get custom poll interval if set
    CUSTOM_INTERVAL=$(grep "PR_MONITOR_POLL_SECONDS=" .env 2>/dev/null | cut -d'=' -f2)
    if [[ "$CUSTOM_INTERVAL" =~ ^[0-9]+$ ]]; then
        POLL_INTERVAL_SECONDS=$CUSTOM_INTERVAL
    fi
fi

# Function to check PR status
check_pr_status() {
    local pr_number=$1
    local check_status=$(gh pr checks "$pr_number" 2>/dev/null)
    
    if [ -z "$check_status" ]; then
        echo "⏳ No checks running yet for PR #$pr_number"
        echo "   GitHub might still be setting up the CI workflows"
        return 1
    fi
    
    # Count different check states - ensure we have default values
    local total_checks=0
    local pending_checks=0
    local failed_checks=0
    
    total_checks=$(echo "$check_status" | wc -l | xargs)
    # Use grep with || true to avoid exit on no matches
    pending_checks=$(echo "$check_status" | grep -c "pending\|queued\|in_progress" || true)
    failed_checks=$(echo "$check_status" | grep -c "fail\|error\|cancelled\|timed_out\|action_required" || true)
    
    # Ensure we have numeric values
    [[ "$total_checks" =~ ^[0-9]+$ ]] || total_checks=0
    [[ "$pending_checks" =~ ^[0-9]+$ ]] || pending_checks=0
    [[ "$failed_checks" =~ ^[0-9]+$ ]] || failed_checks=0
    
    # All checks passed
    if [ "${pending_checks:-0}" -eq 0 ] && [ "${failed_checks:-0}" -eq 0 ]; then
        echo "✅ All $total_checks checks passed for PR #$pr_number!"
        echo "   $PR_URL"
        return 0
    fi
    
    # Some checks failed
    if [ "${failed_checks:-0}" -gt 0 ]; then
        echo "❌ $failed_checks of $total_checks checks failed for PR #$pr_number."
        echo "   Failed checks:"
        echo "$check_status" | grep -E "fail|error|cancelled|timed_out|action_required" || echo "   No details available"
        echo "   See details: $PR_URL/checks"
        return 2
    fi
    
    # Some checks still pending
    if [ "${pending_checks:-0}" -gt 0 ]; then
        echo "⏳ $pending_checks of $total_checks checks still running for PR #$pr_number."
        echo "   $total_checks total checks, $((total_checks - pending_checks - failed_checks)) passed, $failed_checks failed"
        return 1
    fi
    
    return 1
}

# Initial check
echo "Checking PR status..."
check_pr_status "$PR_NUMBER"
INITIAL_STATUS=$?

# If all checks passed, exit with success
if [ "${INITIAL_STATUS:-0}" -eq 0 ]; then
    echo "🎉 All CI checks have passed! Your PR is ready for review."
    exit 0
fi

# If checks failed, offer to open in browser
if [ "${INITIAL_STATUS:-0}" -eq 2 ]; then
    echo "Would you like to open the PR in your browser to view failed checks? (Add --no-browser to disable this prompt)"
    if command_exists open; then
        open "$PR_URL/checks"
    elif command_exists xdg-open; then
        xdg-open "$PR_URL/checks"
    else
        echo "Cannot open browser automatically. Visit: $PR_URL/checks"
    fi
    exit 1
fi

# If not set to auto-poll, exit
if [ "$AUTO_POLL" != "true" ]; then
    echo "Use ./scripts/monitor-pr.sh without --no-poll to wait for checks to complete"
    exit 0
fi

# Set up polling - automatic mode
echo "🔄 Waiting for checks to complete (max $MAX_WAIT_MINUTES minutes)..."
echo "   Press Ctrl+C to exit polling"

START_TIME=$(date +%s)
MAX_WAIT_SECONDS=$((MAX_WAIT_MINUTES * 60))
TIMEOUT_TIME=$((START_TIME + MAX_WAIT_SECONDS))

# Poll until all checks complete or timeout
POLL_COUNT=0
while [ "$(date +%s)" -lt "$TIMEOUT_TIME" ]; do
    POLL_COUNT=$((POLL_COUNT + 1))
    
    # Simple polling message for non-interactive terminals
    echo "Polling for CI status... (iteration $POLL_COUNT)"
    
    sleep $POLL_INTERVAL_SECONDS
    
    # Check status
    echo "Checking current status..."
    CHECK_STATUS=$(gh pr checks "$PR_NUMBER" 2>/dev/null)
    PENDING_CHECKS=$(echo "$CHECK_STATUS" | grep -c "pending\|queued\|in_progress" || true)
    FAILED_CHECKS=$(echo "$CHECK_STATUS" | grep -c "fail\|error\|cancelled\|timed_out\|action_required" || true)
    TOTAL_CHECKS=$(echo "$CHECK_STATUS" | wc -l | xargs)
    
    # Ensure we have numeric values
    [[ "$PENDING_CHECKS" =~ ^[0-9]+$ ]] || PENDING_CHECKS=0
    [[ "$FAILED_CHECKS" =~ ^[0-9]+$ ]] || FAILED_CHECKS=0
    [[ "$TOTAL_CHECKS" =~ ^[0-9]+$ ]] || TOTAL_CHECKS=0
    
    # If no checks yet, wait for them to start
    if [ -z "$CHECK_STATUS" ]; then
        echo "⏳ Waiting for checks to start running..."
        continue
    fi
    
    # Show current progress
    PASSED_CHECKS=$((TOTAL_CHECKS - PENDING_CHECKS - FAILED_CHECKS))
    echo "Status: $PASSED_CHECKS passed, $PENDING_CHECKS pending, $FAILED_CHECKS failed (of $TOTAL_CHECKS total)"
    
    # If no pending checks, break the loop
    if [ "${PENDING_CHECKS:-0}" -eq 0 ]; then
        echo "All checks completed!"
        break
    fi
done

if [ "$(date +%s)" -ge "$TIMEOUT_TIME" ]; then
    echo "⏱️ Timeout reached after $MAX_WAIT_MINUTES minutes."
    echo "   Some checks are still running. Check status manually at: $PR_URL/checks"
fi

echo ""
echo "Final check status:"
check_pr_status "$PR_NUMBER"
FINAL_STATUS=$?

if [ "${FINAL_STATUS:-0}" -eq 2 ]; then
    echo "❌ Some checks failed. Please review and fix the issues."
    exit 1
else
    echo "🎉 All CI checks have passed! Your PR is ready for review."
    exit 0
fi 