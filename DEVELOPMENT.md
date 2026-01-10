# Development Guide

This guide covers development setup, testing, and running the various tools and checks.

## Quick Setup

```bash
# Install development dependencies
make install-dev

# Or manually
pip install -r requirements-dev.txt
```

## Running Checks

### Security Audit

Check for vulnerable dependencies:

```bash
make security-audit
# or
./scripts/run_security_audit.sh
```

### Health Checks

Verify system readiness:

```bash
make health-check
```

This checks:
- Python version (3.11+)
- Required dependencies
- ExifTool installation
- Disk space
- Write permissions
- Network connectivity

### Generate Lock Files

Create reproducible dependency lock files:

```bash
make requirements-lock-all
# or
./scripts/generate_lock_files.sh
```

This generates:
- `requirements.lock.txt` - Locked production dependencies
- `requirements-dev.lock.txt` - Locked development dependencies

## Testing

### Run All Tests

```bash
make test
# or
pytest
```

### Run Tests with Coverage

```bash
make test-cov
# or
pytest --cov=. --cov-report=html
```

### Run Specific Tests

```bash
# Run only unit tests
pytest tests/test_*.py -v

# Run only integration tests
pytest tests/integration/ -v -m integration

# Run specific test file
pytest tests/test_config_validation.py -v

# Run specific test
pytest tests/test_config_validation.py::TestMigrationConfig::test_migration_config_from_yaml_valid -v
```

## Code Quality

### Format Code

```bash
make format
# or
black .
isort .
```

### Check Formatting (without changes)

```bash
make format-check
```

### Lint Code

```bash
make lint
# or
flake8 .
ruff check .
```

### Auto-fix Linting Issues

```bash
make lint-fix
# or
ruff check --fix .
```

### Type Checking

```bash
make type-check
# or
mypy .
```

### Run All Checks

```bash
make check-all
```

This runs: format-check, lint, and type-check

## Documentation

### Generate Sphinx Documentation

```bash
make docs
# or
cd docs && make html
```

### View Documentation

After generating, open in browser:

```bash
make docs-open
# or manually open
open docs/_build/html/index.html
```

### Clean Documentation Build

```bash
make docs-clean
# or
cd docs && make clean
```

## Pre-commit Hooks

### Install Pre-commit Hooks

```bash
make pre-commit-install
# or
pre-commit install
```

### Run Pre-commit Hooks on All Files

```bash
make pre-commit-run
# or
pre-commit run --all-files
```

## Common Development Tasks

### Clean Up Temporary Files

```bash
make clean
```

This removes:
- `__pycache__` directories
- `.pyc` files
- `.pytest_cache`
- `.mypy_cache`
- `.ruff_cache`
- `htmlcov`
- `build` and `dist` directories

### Full Setup

```bash
make setup
```

This:
1. Installs all development dependencies
2. Creates necessary directories
3. Sets up test infrastructure

## Running the Migration

### Run with Default Config

```bash
make run
# or
python main.py --config config.yaml
```

### Run Health Check First

```bash
make health-check && make run
```

## Continuous Integration

The repository includes GitHub Actions workflows:

- **`.github/workflows/test.yml`** - Runs tests on multiple Python versions
- **`.github/workflows/lint.yml`** - Runs linting checks
- **`.github/workflows/pre-commit.yml`** - Runs pre-commit hooks

All workflows run automatically on push and pull requests.

## Troubleshooting

### pip-audit not found

```bash
pip install pip-audit
# or
make install-dev
```

### Sphinx not found

```bash
pip install sphinx sphinx-rtd-theme myst-parser
# or
make install-dev
```

### Health check fails

Review the output for specific issues:
- Missing dependencies: `pip install -r requirements.txt`
- ExifTool not found: `brew install exiftool`
- Disk space issues: Free up disk space
- Permission issues: Check directory permissions

## Additional Resources

- **`CONTRIBUTING.md`** - Contribution guidelines
- **`RECOMMENDATIONS.md`** - Repository improvement recommendations
- **`IMPLEMENTATION_STATUS.md`** - Status of implemented recommendations
- **`TESTING.md`** - Testing guide
- **`docs/`** - Sphinx documentation
