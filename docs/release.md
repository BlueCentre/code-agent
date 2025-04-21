# Release Process

This document outlines the process for creating and publishing new releases of the CLI Code Agent.

## Version Management

The project version is maintained in a single location:
- `pyproject.toml`: The official source of truth for version information

The application code automatically reads this version at runtime using `importlib.metadata`.

## Pre-Release Checklist

Before creating a new release, ensure:

1. All tests are passing: `python -m pytest`
2. Test coverage meets requirements: `python -m pytest --cov=code_agent`
3. Code quality checks pass: `pre-commit run --all-files`
4. Documentation is up-to-date
5. CHANGELOG.md is updated with notable changes (if applicable)

## Release Process

1. **Update Version**

   Modify the version in `pyproject.toml`:
   ```toml
   [tool.poetry]
   name = "cli-code-agent"
   version = "x.y.z"  # Update this line
   ```

2. **Commit Version Change**

   ```bash
   git add pyproject.toml
   git commit -m "Bump version to x.y.z"
   ```

3. **Create Git Tag**

   ```bash
   git tag -a vx.y.z -m "Release version x.y.z"
   ```

4. **Push Changes and Tags**

   ```bash
   git push origin main
   git push origin vx.y.z
   ```

5. **Verify CI Pipeline**

   GitHub Actions will automatically:
   - Run tests
   - Upload coverage to SonarCloud
   - Build and publish to PyPI (for tagged releases)

   Check the GitHub Actions tab to ensure all workflows complete successfully.

6. **Create GitHub Release**

   1. Go to the GitHub repository
   2. Navigate to "Releases"
   3. Click "Draft a new release"
   4. Select the tag you just pushed
   5. Enter a release title (typically "Release x.y.z")
   6. Add release notes describing the changes
   7. Click "Publish release"

7. **Verify PyPI Publication**

   1. Check that the new version appears on PyPI: https://pypi.org/project/cli-code-agent/
   2. Optionally, install the release from PyPI to verify it works:
      ```bash
      pip install --upgrade cli-code-agent
      code-agent --version  # Should show the new version
      ```

## Post-Release

1. Begin development on the next version by updating the version in `pyproject.toml` to the next development version (e.g., "x.y.(z+1)-dev")
2. Update any roadmap documents to reflect completed and upcoming features

## Versioning Strategy

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality additions
- **PATCH** version for backward-compatible bug fixes

For pre-releases, use suffixes like `-alpha.1`, `-beta.1`, or `-rc.1`.

## Hotfix Process

For urgent fixes to a released version:

1. Create a branch from the release tag: `git checkout -b hotfix/x.y.(z+1) vx.y.z`
2. Make the necessary changes
3. Update the version in `pyproject.toml` to `x.y.(z+1)`
4. Follow the standard release process from step 2 onward
