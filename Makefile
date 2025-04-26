.PHONY: test test-coverage clean lint format install setup-dev setup-venv test-unit test-integration uv-test uv-test-unit uv-test-integration uv-lint uv-format

# Environment setup targets
setup-venv:
	python -m venv .venv

setup-dev: setup-venv
	@echo "Setting up development environment..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Using UV for faster installation"; \
		. .venv/bin/activate && uv pip install -e ".[dev]"; \
	else \
		echo "Using pip for installation"; \
		. .venv/bin/activate && pip install -e ".[dev]"; \
	fi
	@echo "Installing pre-commit hooks..."
	. .venv/bin/activate && pre-commit install

install:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Using UV for faster installation"; \
		uv pip install -e .; \
	else \
		echo "Using pip for installation"; \
		pip install -e .; \
	fi

# Test targets
test:
	@echo "Running all tests..."
	pytest

test-unit:
	@echo "Running unit tests only..."
	pytest -m unit tests/

test-integration:
	@echo "Running integration tests only..."
	pytest -m integration tests/

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=code_agent --cov-report=term --cov-report=html --cov-fail-under=80

test-report:
	pytest tests/ --cov=code_agent --cov-report=term --cov-report=html --cov-fail-under=80
	open htmlcov/index.html

# Linting and formatting
lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

# Clean up
clean:
	rm -rf .coverage htmlcov/ .pytest_cache/ *.egg-info/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

# Run with UV for faster performance
uv-test:
	@echo "Running tests with UV..."
	. .venv/bin/activate && uv pip install pytest && uv run pytest

uv-test-unit:
	@echo "Running unit tests with UV..."
	. .venv/bin/activate && uv pip install pytest && uv run pytest -m unit tests/

uv-test-integration:
	@echo "Running integration tests with UV..."
	. .venv/bin/activate && uv pip install pytest && uv run pytest -m integration tests/

uv-lint:
	@echo "Running linting with UV..."
	. .venv/bin/activate && uv pip install ruff && uv run ruff check .
	. .venv/bin/activate && uv run ruff format --check .

uv-format:
	@echo "Running formatting with UV..."
	. .venv/bin/activate && uv pip install ruff && uv run ruff check --fix .
	. .venv/bin/activate && uv run ruff format .
