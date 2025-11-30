# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Modern Web UI** with Flask backend and Tailwind CSS frontend
  - Real-time progress tracking via WebSocket connections
  - Live statistics dashboard with migration metrics
  - Activity log streaming with user-controlled log levels (DEBUG, INFO, WARNING, ERROR)
  - Configuration management through web interface
  - Failed uploads viewer with individual and bulk retry functionality
  - Pause before cleanup when failed uploads are detected (preserves zip files for retry)
  - "Proceed with Cleanup" button to continue after retries
  - Responsive design for desktop and mobile
- Developer tooling infrastructure (Makefile, pre-commit hooks, flake8 config)
- Comprehensive test suite with pytest
- Code formatting and type hints (black, isort, mypy)
- Improved error handling with custom exceptions
- Security improvements (environment variables, configuration validation)
- Enhanced logging and progress reporting with rich library
- Performance optimizations (parallel processing with ThreadPoolExecutor/ProcessPoolExecutor)
- Monitoring and observability features (metrics, health checks)
- Proper package structure (google_photos_icloud_migration package)
- CI/CD pipeline (GitHub Actions for tests, linting, pre-commit)
- Package installation support (pip install -e .)
- Entry point command: photo-migrate
- **.env file support** for secure credential storage
  - `.env.example` template file for environment variables
  - Automatic loading of `.env` files using python-dotenv
  - Support for GitHub token storage for repository management scripts
  - Enhanced documentation for environment variable usage
- **GitHub repository management script** (`scripts/set_github_repo_info.py`)
  - Automated repository description and topics management
  - Support for GitHub personal access tokens via `.env` file
  - Multiple authentication methods (`.env`, environment variable, or command-line argument)

### Changed
- Code style standardized with black and isort
- Type hints added throughout codebase
- Error messages made more actionable
- Configuration management improved
- **PhotoKit sync method is now default in Web UI** (recommended method)
- Activity log now includes full context (timestamp, logger name, level, message)
- Migration automatically pauses before cleanup if failed uploads exist
- Zip files are preserved when uploads fail to allow retries

### Fixed
- Various bug fixes and improvements

## [1.0.0] - 2025-11-26

### Added
- Initial release
- Google Photos to iCloud Photos migration tool
- PhotoKit-based upload method
- Metadata preservation (dates, GPS, descriptions)
- Album structure parsing and preservation
- Interactive authentication setup wizard
- Retry mechanism for failed uploads
- Zip file validation and corruption tracking

### Fixed
- NSDate conversion issues in PhotoKit uploader
- Video file upload support
- PHAssetCollectionTypeAlbum constant import

---

## Version Format

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

