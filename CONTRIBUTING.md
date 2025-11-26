# Contributing to Google Photos to iCloud Migration

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/16wells/google-photos-icloud-migration.git
   cd google-photos-icloud-migration
   ```

2. **Install dependencies**:
   ```bash
   # Install production dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   
   # Or install in development mode (recommended)
   pip install -e .
   pip install -r requirements-dev.txt
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

4. **Verify setup**:
   ```bash
   make help  # See all available commands
   make test  # Run tests
   ```

## Code Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (Black default)
- **Formatting**: Use [Black](https://black.readthedocs.io/) for automatic formatting
- **Import sorting**: Use [isort](https://pycqa.github.io/isort/) with Black profile
- **Type hints**: Use type hints for all function signatures

### Formatting Code

Before committing, format your code:
```bash
make format
# or
black .
isort .
```

### Linting

Run linters to check code quality:
```bash
make lint
# or
flake8 .
```

### Type Checking

Check type annotations:
```bash
make type-check
# or
mypy .
```

## Testing

### Running Tests

```bash
# Run all tests
make test
# or
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test function names starting with `test_`
- Follow the patterns in `tests/example_test.py`

### Test Coverage

Aim for high test coverage, especially for:
- Error handling paths
- Core functionality
- Edge cases

## Pull Request Process

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit your changes**:
   ```bash
   git commit -m "Description of your changes"
   ```
   
   Use clear, descriptive commit messages:
   - Start with a verb (Add, Fix, Update, Remove, etc.)
   - Keep first line under 72 characters
   - Add details in the body if needed

4. **Run checks before pushing**:
   ```bash
   make format lint type-check test
   ```

5. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Guidelines**:
   - Provide a clear description of changes
   - Reference related issues
   - Ensure all CI checks pass
   - Request review from maintainers

## Development Workflow

### Using Makefile

We provide a Makefile with common commands:

```bash
make help          # Show all available commands
make install       # Install production dependencies
make install-dev   # Install development dependencies
make test          # Run tests
make format        # Format code
make lint          # Run linters
make type-check    # Run type checker
make clean         # Clean temporary files
```

### Project Structure

```
.
├── main.py                 # Main entry point
├── drive_downloader.py     # Google Drive integration
├── extractor.py            # Zip extraction
├── metadata_merger.py      # Metadata processing
├── album_parser.py         # Album parsing
├── icloud_uploader.py      # iCloud upload
├── exceptions.py           # Custom exceptions
├── tests/                  # Test files
├── docs/                   # Documentation
└── requirements.txt        # Production dependencies
```

## Code Review Guidelines

- Be respectful and constructive
- Focus on code, not the person
- Explain why, not just what
- Ask questions if something is unclear

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the problem
2. **Steps to reproduce**: Detailed steps to reproduce the issue
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: 
   - OS and version
   - Python version
   - Relevant package versions
6. **Logs**: Relevant log output (sanitize any sensitive data)

## Feature Requests

For feature requests:

1. Check if it's already been requested
2. Provide a clear use case
3. Explain why it would be valuable
4. Consider if you can implement it yourself

## Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email the maintainers directly
3. Provide details about the vulnerability
4. Allow time for a fix before public disclosure

## Documentation

- Update README.md for user-facing changes
- Update docstrings for API changes
- Add examples for new features
- Keep documentation clear and concise

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search existing issues
3. Open a discussion/question issue

Thank you for contributing! 🎉

