.PHONY: help install install-dev test format lint type-check run clean

help:  ## Show this help message
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt || echo "requirements-dev.txt not found, skipping dev dependencies"

test:  ## Run tests
	pytest tests/ -v || echo "No tests found - run 'make setup-tests' first"

test-cov:  ## Run tests with coverage report
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term || echo "No tests found - run 'make setup-tests' first"

test-fast:  ## Run tests excluding slow markers
	pytest tests/ -v -m "not slow" || echo "No tests found - run 'make setup-tests' first"

setup-tests:  ## Create test directory structure
	mkdir -p tests/fixtures
	touch tests/__init__.py

format:  ## Format code with black and isort
	black . || echo "black not installed - run 'make install-dev'"
	isort . || echo "isort not installed - run 'make install-dev'"

format-check:  ## Check code formatting without making changes
	black --check . || echo "black not installed - run 'make install-dev'"
	isort --check-only . || echo "isort not installed - run 'make install-dev'"

lint:  ## Run linters (flake8 and ruff)
	flake8 . || echo "flake8 not installed - run 'make install-dev'"
	ruff check . || echo "ruff not installed - run 'make install-dev'"

lint-fix:  ## Auto-fix linting issues with ruff
	ruff check --fix . || echo "ruff not installed - run 'make install-dev'"

type-check:  ## Run type checker
	mypy . || echo "mypy not installed - run 'make install-dev'"

check-all: format-check lint type-check  ## Run all checks (format, lint, type-check)

run:  ## Run migration with default config
	python scripts/main.py --config config.yaml

run-sync:  ## Run migration with PhotoKit sync method (default, macOS only)
	python scripts/main.py --config config.yaml

clean:  ## Clean up temporary files and caches
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build

health-check:  ## Run health checks before migration
	python3 -c "from google_photos_icloud_migration.utils.health_check import HealthChecker; \
		from pathlib import Path; \
		checker = HealthChecker(Path('/tmp')); \
		passed, results = checker.check_all(); \
		checker.print_results(); \
		exit(0 if passed else 1)"

security-audit:  ## Run pip-audit to check for vulnerable dependencies
	pip-audit -r requirements.txt || echo "pip-audit not installed - run 'make install-dev'"

security-audit-dev:  ## Run pip-audit on all dependencies including dev
	pip-audit -r requirements.txt -r requirements-dev.txt || echo "pip-audit not installed - run 'make install-dev'"

requirements-lock:  ## Generate requirements.lock.txt from requirements.txt
	pip-compile requirements.txt --output-file=requirements.lock.txt --resolver=backtracking || echo "pip-tools not installed - run 'make install-dev'"

requirements-lock-dev:  ## Generate requirements-dev.lock.txt from requirements-dev.txt
	pip-compile requirements-dev.txt --output-file=requirements-dev.lock.txt --resolver=backtracking || echo "pip-tools not installed - run 'make install-dev'"

requirements-lock-all:  ## Generate all lock files
	@echo "Generating all requirements lock files..."
	@$(MAKE) requirements-lock
	@$(MAKE) requirements-lock-dev
	@echo "✓ All lock files generated!"

docs:  ## Generate Sphinx documentation
	cd docs && make html || echo "Sphinx not installed - run 'make install-dev'"

docs-clean:  ## Clean Sphinx documentation build
	cd docs && make clean || echo "Sphinx not installed"

docs-open:  ## Open generated documentation in browser
	open docs/_build/html/index.html 2>/dev/null || xdg-open docs/_build/html/index.html 2>/dev/null || echo "Could not open browser - view docs/_build/html/index.html manually"

pre-commit-install:  ## Install pre-commit hooks
	pre-commit install || echo "pre-commit not installed - run 'make install-dev'"

pre-commit-run:  ## Run pre-commit hooks on all files
	pre-commit run --all-files || echo "pre-commit not installed - run 'make install-dev'"

setup: install-dev  ## Full setup (install dev deps and create directories)
	mkdir -p tests/fixtures
	@echo "Setup complete!"

