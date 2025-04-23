#!/bin/bash

# Script to install Git hooks
# Run this after cloning the repository

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SOURCES="$REPO_ROOT/.githooks"
HOOK_DEST="$REPO_ROOT/.git/hooks"

echo "Installing Git hooks..."

# Check if .githooks directory exists
if [ ! -d "$HOOK_SOURCES" ]; then
    echo "Error: .githooks directory not found!"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DEST"

# Copy all hooks and make them executable
for hook in "$HOOK_SOURCES"/*; do
    if [ -f "$hook" ]; then
        hook_name=$(basename "$hook")
        echo "Installing $hook_name hook..."
        cp "$hook" "$HOOK_DEST/$hook_name"
        chmod +x "$HOOK_DEST/$hook_name"
    fi
done

# Set up Git to use this hooks directory (alternative approach)
# git config core.hooksPath "$HOOK_SOURCES"

echo "Git hooks installed successfully!"
echo "You can also set up hooks using Git config: git config core.hooksPath .githooks" 