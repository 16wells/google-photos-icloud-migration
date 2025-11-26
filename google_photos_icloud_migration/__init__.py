"""
Google Photos to iCloud Photos Migration Tool

A comprehensive tool for migrating photos and videos from Google Photos
(exported via Google Takeout) to iCloud Photos, preserving metadata and
album structures.
"""
__version__ = "1.0.0"

# Import main classes for easy access
from google_photos_icloud_migration.config import MigrationConfig
from google_photos_icloud_migration.exceptions import (
    MigrationError,
    ConfigurationError,
    AuthenticationError,
    DownloadError,
    ExtractionError,
    ProcessingError,
    UploadError,
    VerificationError,
    MetadataError,
    AlbumError,
)

__all__ = [
    '__version__',
    'MigrationConfig',
    'MigrationError',
    'ConfigurationError',
    'AuthenticationError',
    'DownloadError',
    'ExtractionError',
    'ProcessingError',
    'UploadError',
    'VerificationError',
    'MetadataError',
    'AlbumError',
]

