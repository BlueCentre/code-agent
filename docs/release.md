# Release Process

This document outlines the process for creating and publishing new releases of the CLI Code Agent.

## Version Management

The project version is maintained in three locations:
- `pyproject.toml`: The primary source of truth for version information
- `code_agent/version.py`: Contains the fallback version
- `CHANGELOG.md`: Documents changes in each version

The application code automatically reads the version at runtime using `importlib.metadata`.

## Pre-Release Checklist

Before creating a new release, ensure:

1. All tests are passing and coverage meets requirements: `make test` or `make test-coverage`
2. Code quality checks pass: `make lint` (or `uv run ruff check .`)
3. Documentation is up-to-date
4. The installation and functionality have been manually verified

## Release Process

1. **Update CHANGELOG.md First**

   Add a new section for the upcoming version to `CHANGELOG.md` with categories:
   ```markdown
   ## [x.y.z] - YYYY-MM-DD

   ### Added
   - New features

   ### Changed
   - Changes in existing functionality

   ### Fixed
   - Bug fixes

   ### Security
   - Security fixes
   ```

2. **Check PyPI for Version Availability**

   Verify the version you're planning to release isn't already on PyPI:
   ```bash
   uv pip install cli-code-agent==x.y.z
   ```
   If the command succeeds, increment your version number.

3. **Update Version in Files**

   Update the version in all relevant files:
   
   a. `pyproject.toml`:
   ```toml
   [project]
   name = "cli-code-agent"
   version = "x.y.z"  # Update this line
   ```
   
   b. `code_agent/version.py`:
   ```python
   try:
       from importlib.metadata import version
   
       __version__ = version("cli-code-agent")
   except ImportError:
       __version__ = "x.y.z"  # Update this fallback version
   ```
   
   c. If present in sonar-scanner section of `pyproject.toml`:
   ```toml
   # projectVersion = "x.y.z"  # Update this line
   ```

4. **Commit All Changes**

   ```bash
   git add pyproject.toml code_agent/version.py CHANGELOG.md uv.lock
   git commit -m "chore: Bump version to x.y.z with updated changelog"
   ```

5. **Create Git Tag with Changelog Content**

   Extract changelog entry for the new version and use it as the tag message:
   ```bash
   awk '/## \[x.y.z\]/,/## \[.*\]/' CHANGELOG.md | grep -v "## \[.*\]" > /tmp/tag_message.txt
   git tag -a vx.y.z -F /tmp/tag_message.txt
   ```

6. **Push Changes and Tags**

   ```bash
   git push origin main
   git push origin vx.y.z
   ```

7. **Verify CI Pipeline**

   GitHub Actions will automatically:
   - Run tests
   - Build and publish to PyPI (for tagged releases)

   Check the GitHub Actions tab to ensure all workflows complete successfully.

8. **Verify PyPI Publication**

   1. Check that the new version appears on PyPI: https://pypi.org/project/cli-code-agent/
   2. Verify installation from PyPI:
      ```bash
      uv pip install --upgrade cli-code-agent
      code-agent --version  # Should show the new version
      ```

## Troubleshooting

### Publish Workflow Failures

If the publish workflow fails:

1. Check workflow logs for specific errors
2. Common issues include:
   - Version already exists on PyPI
   - Caching problems with GitHub Actions
   - Missing dependencies in the workflow

3. If needed, update the workflow file at `.github/workflows/publish.yml`

### Version Display Issues

If `code-agent --version` doesn't show the correct version:

1. Ensure `code_agent/__init__.py` correctly imports `__version__` from `version.py`
2. Reinstall the package with `uv pip install -e .` for local testing

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
3. Update the version in all files to `x.y.(z+1)`
4. Follow the standard release process from step 1 onward
