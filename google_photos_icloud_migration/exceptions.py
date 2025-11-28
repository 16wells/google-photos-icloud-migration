"""
Custom exceptions for the Google Photos to iCloud Migration tool.
"""


class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class ConfigurationError(MigrationError):
    """Error related to configuration."""
    pass


class AuthenticationError(MigrationError):
    """Error during authentication."""
    pass


class DownloadError(MigrationError):
    """Error during file download."""
    pass


class ExtractionError(MigrationError):
    """Error during file extraction."""
    pass


class ProcessingError(MigrationError):
    """Error during file processing."""
    pass


class UploadError(MigrationError):
    """Error during file upload."""
    pass


class VerificationError(MigrationError):
    """Error during file verification."""
    pass


class MetadataError(MigrationError):
    """Error related to metadata processing."""
    pass


class AlbumError(MigrationError):
    """Error related to album operations."""
    pass


class CorruptedZipException(MigrationError):
    """Exception raised when a corrupted zip file is detected and requires user intervention."""
    def __init__(self, message: str, zip_path: str, file_info: dict = None, file_size_mb: float = None):
        super().__init__(message)
        self.zip_path = zip_path
        self.file_info = file_info or {}
        self.file_size_mb = file_size_mb

