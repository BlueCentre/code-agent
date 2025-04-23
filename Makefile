.PHONY: test test-coverage clean lint format

test:
	pytest

test-coverage:
	pytest tests/ --cov=code_agent --cov-report=term --cov-report=html --cov-fail-under=80

test-report:
	pytest tests/ --cov=code_agent --cov-report=term --cov-report=html --cov-fail-under=80
	open htmlcov/index.html

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

clean:
	rm -rf .coverage htmlcov/ .pytest_cache/ *.egg-info/ dist/ build/
	find . -type d -name __pycache__ -exec rm -rf {} +

install:
	poetry install
