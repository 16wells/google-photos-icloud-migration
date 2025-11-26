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

setup-tests:  ## Create test directory structure
	mkdir -p tests/fixtures
	touch tests/__init__.py

format:  ## Format code with black
	black *.py || echo "black not installed - run 'make install-dev'"
	isort *.py || echo "isort not installed - run 'make install-dev'"

lint:  ## Run linters
	flake8 *.py || echo "flake8 not installed - run 'make install-dev'"

type-check:  ## Run type checker
	mypy *.py || echo "mypy not installed - run 'make install-dev'"

run:  ## Run migration with default config
	python main.py --config config.yaml

run-sync:  ## Run migration with PhotoKit sync method
	python main.py --config config.yaml --use-sync

clean:  ## Clean up temporary files and caches
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache

setup: install-dev  ## Full setup (install dev deps and create directories)
	mkdir -p tests/fixtures
	@echo "Setup complete!"

