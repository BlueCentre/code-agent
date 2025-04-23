This PR updates the project to use 'uv' for development environment setup and dependency installation in local scripts and CI workflows.

**Changes:**
- Updated 'README.md' and 'docs/CONTRIBUTING.md' to recommend 'uv'.
- Modified '.github/workflows/pr-workflow.yml' and '.github/workflows/test-coverage.yml' to use 'uv pip install'.
- Updated local test scripts ('run_coverage_pipeline*.sh', 'run_native_tools_coverage.sh') to use 'uv'.
- Added comments to 'publish.yml' explaining why Poetry is retained for build/publish steps.
- Added a note to 'planning_priorities.md' to revisit 'uv build/publish' later.

**Motivation:**
- Improves dependency installation speed during development and in CI.
- Increases consistency in tooling recommendations.

**Testing:**
- Local tests ('pytest', coverage, E2E) pass successfully after these changes.
- Pipeline changes need verification via this PR's checks.
