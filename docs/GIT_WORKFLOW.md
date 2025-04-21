# Git and GitHub Workflow

This document outlines our standardized Git and GitHub workflow for contributing to this project.

## Branch Naming Convention

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

## Helper Script

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

## Commit Message Convention

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

## Development Workflow

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
   - Submit the pull request

5. **Code Review Process**
   - The PR will automatically run tests and add coverage reports as comments
   - At least one reviewer must approve the PR
   - All CI checks must pass
   - Code coverage must not drop below 80%

6. **Merging**
   - Once approved and all checks pass, the PR can be merged
   - Prefer "Squash and merge" to keep a clean history on the main branch

## Working with PRs

When a PR is opened:
1. The CI pipeline will run all tests and generate coverage reports
2. Test results and coverage will be posted as comments on the PR
3. Reviewers can see these reports directly in the PR

## Maintaining Clean History

- Rebase your branch before merging if needed:
  ```bash
  git checkout <type>/<description>
  git rebase main
  git push --force-with-lease
  ```
- Use `git rebase -i` to squash multiple commits if needed
- Avoid merge commits by using squash merges in the GitHub UI
