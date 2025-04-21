#!/bin/bash

# Script to create a new feature branch following our naming convention

# Usage information
function show_usage {
    echo "Usage: ./create-branch.sh <type> <description>"
    echo ""
    echo "Creates a new Git branch following the '<type>/<description>' convention"
    echo ""
    echo "Types:"
    echo "  feat     - A new feature"
    echo "  fix      - A bug fix"
    echo "  docs     - Documentation only changes"
    echo "  style    - Changes that do not affect code functionality"
    echo "  refactor - Code change that neither fixes a bug nor adds a feature"
    echo "  perf     - A code change that improves performance"
    echo "  test     - Adding or modifying tests"
    echo "  chore    - Changes to build process or auxiliary tools"
    echo ""
    echo "Example:"
    echo "  ./create-branch.sh feat user-authentication"
    echo "  (creates branch: feat/user-authentication)"
    exit 1
}

# Check if we have enough arguments
if [ $# -lt 2 ]; then
    show_usage
fi

# Get the branch type and description
TYPE=$1
DESC=$2

# Convert any spaces in description to hyphens
DESC=${DESC// /-}

# Check if the type is valid
VALID_TYPES=("feat" "fix" "docs" "style" "refactor" "perf" "test" "chore")
VALID=0

for VALID_TYPE in "${VALID_TYPES[@]}"; do
    if [ "$TYPE" = "$VALID_TYPE" ]; then
        VALID=1
        break
    fi
done

if [ $VALID -eq 0 ]; then
    echo "Error: Invalid branch type '$TYPE'"
    echo ""
    show_usage
fi

# Create the branch name
BRANCH_NAME="$TYPE/$DESC"

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if the branch already exists
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
    echo "Error: Branch '$BRANCH_NAME' already exists"
    exit 1
fi

# Make sure we're on main branch and up to date
echo "Checking out main branch..."
git checkout main

echo "Pulling latest changes..."
git pull

# Create and checkout the new branch
echo "Creating branch '$BRANCH_NAME'..."
git checkout -b $BRANCH_NAME

echo ""
echo "Branch '$BRANCH_NAME' created successfully!"
echo "You are now ready to make your changes."
echo ""
echo "When committing, remember to use the conventional commit format:"
echo "  git commit -m \"$TYPE: description of changes\""
