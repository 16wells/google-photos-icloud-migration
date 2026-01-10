"""
Configuration management using dataclasses for type safety and validation.

This module provides dataclass-based configuration classes for the Google Photos to
iCloud Photos migration tool. Configuration can be loaded from YAML files with
JSON schema validation, environment variable overrides, and comprehensive defaults.

Key Features:
- Type-safe dataclass configuration
- YAML file loading with schema validation
- Environment variable overrides for sensitive values
- Comprehensive validation and error handling
- Automatic path resolution and property helpers

Configuration Classes:
- GoogleDriveConfig: Google Drive API credentials and settings
- ICloudConfig: iCloud Photos upload configuration (PhotoKit method only, macOS only)
- ProcessingConfig: Processing directories, batch sizes, parallel processing settings
- MetadataConfig: Metadata preservation preferences (dates, GPS, descriptions, albums)
- LoggingConfig: Logging level and file output settings
- MigrationConfig: Main configuration container combining all sub-configs
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import json
import os
import jsonschema
import logging

logger = logging.getLogger(__name__)


@dataclass
class GoogleDriveConfig:
    """
    Google Drive API configuration for downloading Google Takeout zip files.
    
    This class holds configuration for authenticating with Google Drive API and
    identifying which zip files to download. Supports downloading from a specific
    folder or searching the entire Drive using a file pattern.
    
    Attributes:
        credentials_file: Path to Google Drive API credentials JSON file.
                        Required for authentication. Should be obtained from
                        Google Cloud Console and configured with Drive API access.
        folder_id: Optional Google Drive folder ID to restrict downloads to a
                  specific folder. If None, searches entire Drive (default).
        zip_file_pattern: Glob pattern for matching zip files (default: "takeout-*.zip").
                         Used to identify Google Takeout archives. Standard pattern
                         matches files like "takeout-20240101T120000Z-001.zip".
    
    Note:
        The credentials file must be a valid OAuth 2.0 client credentials JSON
        file from Google Cloud Console with Drive API enabled.
    """
    credentials_file: str
    folder_id: Optional[str] = None
    zip_file_pattern: str = "takeout-*.zip"
    
    def __post_init__(self):
        """
        Validate Google Drive configuration after initialization.
        
        Raises:
            ValueError: If credentials_file is empty or missing.
            Logs warning if credentials file doesn't exist at the specified path.
        """
        if not self.credentials_file:
            raise ValueError("credentials_file is required for Google Drive")
        
        # Check if credentials file exists
        creds_path = Path(self.credentials_file)
        if not creds_path.exists():
            logger.warning(f"Credentials file not found: {self.credentials_file}")


@dataclass
class ICloudConfig:
    """
    Configuration for iCloud Photos upload using PhotoKit (macOS only).
    
    This class holds configuration for uploading photos to iCloud Photos using PhotoKit.
    PhotoKit is the only supported method and requires no authentication credentials.
    
    Attributes:
        photos_library_path: Optional path to Photos library (rarely needed).
                           If not specified, uses default: ~/Pictures/Photos Library.photoslibrary
                           Only needed if you want to use a non-default Photos library location.
        method: Upload method to use. Must be "photokit" (default, only supported method).
               The "api" method is deprecated and not supported - do not use.
        
    Deprecated Attributes (not used with PhotoKit - kept for backward compatibility only):
        apple_id: Deprecated - not needed with PhotoKit method. Ignored if provided.
        password: Deprecated - not needed with PhotoKit method. Ignored if provided.
        trusted_device_id: Deprecated - not needed with PhotoKit method. Ignored if provided.
        two_fa_code: Deprecated - not needed with PhotoKit method. Ignored if provided.
    
    Note:
        PhotoKit method (default) is the only supported method. It:
        - Requires no Apple ID credentials (uses macOS iCloud account automatically)
        - Uses native macOS Photos integration via PhotoKit framework
        - Properly preserves EXIF metadata
        - Only works on macOS (not Linux, Windows, or cloud servers)
        - Requires you to be signed into iCloud on your Mac
        
        The legacy API-based method is deprecated and not supported. Do not use.
        Legacy credential fields (apple_id, password, etc.) are ignored and kept only
        for backward compatibility with old config files.
    """
    photos_library_path: Optional[str] = None
    method: str = "photokit"  # 'photokit' is the only supported method
    
    # Deprecated fields - kept for backward compatibility only, not used with PhotoKit
    apple_id: Optional[str] = None  # Deprecated - not needed with PhotoKit, ignored
    password: Optional[str] = None  # Deprecated - not needed with PhotoKit, ignored
    trusted_device_id: Optional[str] = None  # Deprecated - not needed with PhotoKit, ignored
    two_fa_code: Optional[str] = None  # Deprecated - not needed with PhotoKit, ignored
    
    def __post_init__(self):
        """
        Apply environment variable overrides after initialization (legacy support only).
        
        Note: Environment variables are checked for backward compatibility only.
        With PhotoKit method, no iCloud credentials are needed - the tool uses your
        macOS iCloud account automatically. These environment variables are ignored.
        
        Legacy environment variables (not used with PhotoKit):
        - ICLOUD_APPLE_ID: Ignored (not needed with PhotoKit)
        - ICLOUD_PASSWORD: Ignored (not needed with PhotoKit)
        - ICLOUD_2FA_CODE: Ignored (not needed with PhotoKit)
        - ICLOUD_2FA_DEVICE_ID: Ignored (not needed with PhotoKit)
        """
        # Legacy support: Check environment variables (ignored with PhotoKit method)
        # These are kept for backward compatibility only
        if not self.apple_id:
            self.apple_id = os.getenv('ICLOUD_APPLE_ID')  # Ignored with PhotoKit
        if not self.password:
            self.password = os.getenv('ICLOUD_PASSWORD')  # Ignored with PhotoKit
        if not self.two_fa_code:
            self.two_fa_code = os.getenv('ICLOUD_2FA_CODE')  # Ignored with PhotoKit
        if not self.trusted_device_id:
            self.trusted_device_id = os.getenv('ICLOUD_2FA_DEVICE_ID')  # Ignored with PhotoKit
        
        # Ensure method is photokit (the only supported method)
        if self.method != "photokit":
            logger.warning(
                f"iCloud method '{self.method}' is deprecated. "
                "Only 'photokit' is supported. Setting to 'photokit'."
            )
            self.method = "photokit"


@dataclass
class ProcessingConfig:
    """
    Processing configuration for migration workflow stages.
    
    This class defines directories, batch processing settings, and parallel processing
    configuration for the migration workflow. Controls where files are stored during
    each stage (download, extraction, processing, upload) and how batches are processed.
    
    Attributes:
        base_dir: Base directory for all migration work (required).
                 All other directories are relative to this path.
        zip_dir: Subdirectory for downloaded zip files (default: "zips").
                Relative to base_dir.
        extracted_dir: Subdirectory for extracted zip contents (default: "extracted").
                      Relative to base_dir.
        processed_dir: Subdirectory for processed files ready for upload (default: "processed").
                      Relative to base_dir. Files here have metadata merged and are ready
                      for iCloud Photos upload.
        batch_size: Number of files to process in each batch (default: 100).
                   Larger batches = more memory usage but fewer iterations.
                   Recommended: 50-200 depending on file sizes and available memory.
        cleanup_after_upload: If True, delete processed files after successful upload (default: True).
                             Set to False to keep files for verification or manual review.
        max_workers: Maximum number of parallel workers for processing (default: None = auto-detect).
                    None (recommended) automatically detects optimal worker count based on
                    CPU cores and task type (I/O-bound vs CPU-bound).
                    Specify a number to manually control parallelism.
        enable_parallel_processing: Enable/disable parallel processing entirely (default: True).
                                   If False, all operations run sequentially.
                                   Set to False for debugging or resource-constrained environments.
    
    Properties:
        base_path: Returns base_dir as Path object for convenient path operations.
        zip_path: Returns full path to zip directory (base_dir/zip_dir).
        extracted_path: Returns full path to extracted directory (base_dir/extracted_dir).
        processed_path: Returns full path to processed directory (base_dir/processed_dir).
    
    Raises:
        ValueError: If base_dir is empty or batch_size is less than 1.
    """
    base_dir: str
    zip_dir: str = "zips"
    extracted_dir: str = "extracted"
    processed_dir: str = "processed"
    batch_size: int = 100
    cleanup_after_upload: bool = True
    max_workers: Optional[int] = None  # None = auto-detect (recommended)
    enable_parallel_processing: bool = True
    
    def __post_init__(self):
        """
        Validate processing configuration after initialization.
        
        Raises:
            ValueError: If base_dir is empty or batch_size is less than 1.
        """
        if not self.base_dir:
            raise ValueError("base_dir is required")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
    
    @property
    def base_path(self) -> Path:
        """
        Get base directory as Path object for convenient path operations.
        
        Returns:
            Path object representing base_dir.
        """
        return Path(self.base_dir)
    
    @property
    def zip_path(self) -> Path:
        """
        Get full path to zip directory.
        
        Returns:
            Path object representing base_dir/zip_dir.
        """
        return self.base_path / self.zip_dir
    
    @property
    def extracted_path(self) -> Path:
        """
        Get full path to extracted directory.
        
        Returns:
            Path object representing base_dir/extracted_dir.
        """
        return self.base_path / self.extracted_dir
    
    @property
    def processed_path(self) -> Path:
        """
        Get full path to processed directory.
        
        Returns:
            Path object representing base_dir/processed_dir.
        """
        return self.base_path / self.processed_dir


@dataclass
class MetadataConfig:
    """
    Metadata preservation configuration for EXIF and album information.
    
    This class controls which metadata is preserved when merging JSON metadata from
    Google Takeout into media files and organizing files into albums.
    
    Attributes:
        preserve_dates: If True, preserve creation/modification dates from JSON metadata
                       (default: True). Uses ExifTool to set EXIF DateTimeOriginal and
                       file system timestamps.
        preserve_gps: If True, preserve GPS location data from JSON metadata (default: True).
                     Uses ExifTool to set EXIF GPS tags (GPSLatitude, GPSLongitude, etc.).
        preserve_descriptions: If True, preserve image descriptions from JSON metadata
                              (default: True). Uses ExifTool to set EXIF ImageDescription
                              or XMP:Description tags.
        preserve_albums: If True, preserve album structure and organize files into albums
                        during upload (default: True). Creates albums in iCloud Photos
                        matching Google Photos album structure.
    """
    preserve_dates: bool = True
    preserve_gps: bool = True
    preserve_descriptions: bool = True
    preserve_albums: bool = True


@dataclass
class LoggingConfig:
    """
    Logging configuration for migration process logging.
    
    This class controls logging output level and file location for the migration process.
    
    Attributes:
        level: Logging level: "DEBUG", "INFO", "WARNING", "ERROR", or "CRITICAL"
              (default: "INFO"). Case-insensitive.
        file: Path to log file (default: "migration.log"). Logs are appended to this file.
             Relative paths are resolved relative to the current working directory.
    
    Raises:
        ValueError: If logging level is not one of the valid levels.
    """
    level: str = "INFO"
    file: str = "migration.log"
    
    def __post_init__(self):
        """
        Validate logging level after initialization.
        
        Raises:
            ValueError: If logging level is not one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {self.level}. Must be one of {valid_levels}")


@dataclass
class MigrationConfig:
    """
    Main migration configuration container combining all sub-configurations.
    
    This is the top-level configuration class that combines all sub-configurations
    (Google Drive, iCloud, Processing, Metadata, Logging) into a single unified
    configuration object. Provides methods for loading from YAML files with schema
    validation and environment variable overrides.
    
    Attributes:
        google_drive: Google Drive API configuration for downloading Takeout zips.
        processing: Processing configuration (directories, batch sizes, parallelism).
        icloud: iCloud Photos upload configuration (method, credentials).
        metadata: Metadata preservation preferences.
        logging: Logging level and file output settings.
    
    Class Methods:
        from_yaml: Load configuration from YAML file with optional schema validation.
        from_dict: Create configuration from dictionary (used internally).
    
    Example:
        >>> config = MigrationConfig.from_yaml("config.yaml")
        >>> print(config.processing.base_dir)
        /path/to/migration
    """
    google_drive: GoogleDriveConfig
    processing: ProcessingConfig
    icloud: ICloudConfig = field(default_factory=ICloudConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, config_path: str, validate: bool = True) -> 'MigrationConfig':
        """
        Load configuration from YAML file with optional schema validation.
        
        This method loads configuration from a YAML file, optionally validates it against
        a JSON schema (config_schema.json), applies environment variable overrides, and
        returns a fully configured MigrationConfig instance.
        
        Args:
            config_path: Path to YAML configuration file. Can be absolute or relative.
                       File must exist and contain valid YAML.
            validate: Whether to validate configuration against JSON schema (default: True).
                     Schema file should be located at google_photos_icloud_migration/config_schema.json.
                     If schema file is missing, validation is skipped with a warning.
        
        Returns:
            MigrationConfig instance with all sub-configurations loaded and validated.
        
        Raises:
            ValueError: If config file cannot be loaded, is empty, or fails validation.
            FileNotFoundError: If config file doesn't exist (raised by open()).
            yaml.YAMLError: If YAML file is malformed.
            jsonschema.ValidationError: If validation is enabled and config doesn't match schema.
        
        Note:
            Environment variables take precedence over config file values for security.
            See _apply_env_overrides() for which environment variables are supported.
        
        Example:
            >>> config = MigrationConfig.from_yaml("config.yaml", validate=True)
            >>> print(f"Base directory: {config.processing.base_dir}")
        """
        # Load YAML
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        except (yaml.YAMLError, IOError, OSError) as e:
            raise ValueError(f"Failed to load configuration file '{config_path}': {e}") from e
        
        if config_dict is None:
            raise ValueError(f"Configuration file '{config_path}' is empty or invalid")
        
        # Validate schema if requested
        if validate:
            cls._validate_schema(config_dict)
        
        # Apply environment variable overrides
        config_dict = cls._apply_env_overrides(config_dict)
        
        # Build configuration objects
        return cls.from_dict(config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MigrationConfig':
        """
        Create configuration from dictionary.
        
        This method constructs a MigrationConfig instance from a dictionary structure,
        extracting sub-configurations (google_drive, icloud, processing, metadata, logging)
        and creating appropriate dataclass instances with defaults for missing sections.
        
        Args:
            config_dict: Configuration dictionary with optional sections:
                        - google_drive: Dictionary for GoogleDriveConfig (required if using Drive)
                        - icloud: Dictionary for ICloudConfig (optional, defaults used)
                        - processing: Dictionary for ProcessingConfig (required)
                        - metadata: Dictionary for MetadataConfig (optional, defaults used)
                        - logging: Dictionary for LoggingConfig (optional, defaults used)
        
        Returns:
            MigrationConfig instance with all sub-configurations initialized.
        
        Raises:
            ValueError: If required configuration sections are missing or invalid.
            TypeError: If dataclass initialization fails due to type mismatches.
        
        Note:
            Missing sections use default values. This method is called internally by
            from_yaml() after YAML loading and environment variable overrides.
        
        Example:
            >>> config_dict = {
            ...     "google_drive": {"credentials_file": "creds.json"},
            ...     "processing": {"base_dir": "/migration"}
            ... }
            >>> config = MigrationConfig.from_dict(config_dict)
        """
        # Extract sections with defaults
        google_drive_dict = config_dict.get('google_drive', {})
        icloud_dict = config_dict.get('icloud', {})
        processing_dict = config_dict.get('processing', {})
        metadata_dict = config_dict.get('metadata', {})
        logging_dict = config_dict.get('logging', {})
        
        # Create config objects
        google_drive = GoogleDriveConfig(**google_drive_dict)
        icloud = ICloudConfig(**icloud_dict)
        processing = ProcessingConfig(**processing_dict)
        metadata = MetadataConfig(**metadata_dict)
        logging_config = LoggingConfig(**logging_dict)
        
        return cls(
            google_drive=google_drive,
            icloud=icloud,
            processing=processing,
            metadata=metadata,
            logging=logging_config
        )
    
    @staticmethod
    def _validate_schema(config_dict: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary against JSON schema.
        
        This method validates the configuration dictionary against a JSON schema file
        (config_schema.json) located in the same directory as this module. If the schema
        file doesn't exist, validation is skipped with a warning.
        
        Args:
            config_dict: Configuration dictionary to validate.
        
        Raises:
            ValueError: If validation fails. Includes detailed error message with
                       the path to the invalid field.
            jsonschema.ValidationError: If configuration doesn't match schema structure
                                       or field constraints.
        
        Note:
            Schema file path: google_photos_icloud_migration/config_schema.json
            If schema file is missing, validation is skipped (warning logged).
        """
        try:
            schema_path = Path(__file__).parent / 'config_schema.json'
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                
                jsonschema.validate(instance=config_dict, schema=schema)
                logger.debug("Configuration validated against schema")
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Configuration validation failed: {e.message}\n"
                f"Path: {'.'.join(str(p) for p in e.path)}"
            ) from e
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load configuration schema for validation: {e}")
            # Continue without validation if schema file is missing
    
    @staticmethod
    def _apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration dictionary.
        
        This method creates a deep copy of the configuration dictionary and applies
        environment variable overrides for sensitive values (credentials, passwords).
        Environment variables take precedence over config file values for security.
        
        Supported Environment Variables:
        - ICLOUD_APPLE_ID: Overrides icloud.apple_id
        - ICLOUD_PASSWORD: Overrides icloud.password
        - ICLOUD_2FA_CODE: Overrides icloud.two_fa_code
        - ICLOUD_2FA_DEVICE_ID: Overrides icloud.trusted_device_id
        - GOOGLE_DRIVE_CREDENTIALS_FILE: Overrides google_drive.credentials_file
        
        Args:
            config_dict: Original configuration dictionary to apply overrides to.
        
        Returns:
            New dictionary with environment variable overrides applied. Original
            dictionary is not modified (deep copy is created).
        
        Note:
            Environment variables are checked for existence. If a variable is not set,
            the config file value is used. This allows sensitive values to be stored
            in environment variables instead of config files.
        
        Example:
            >>> import os
            >>> os.environ['ICLOUD_APPLE_ID'] = 'user@example.com'
            >>> config = {'icloud': {'method': 'photokit'}}
            >>> overridden = MigrationConfig._apply_env_overrides(config)
            >>> overridden['icloud']['apple_id']
            'user@example.com'
        """
        # Create a deep copy
        config = json.loads(json.dumps(config_dict))
        
        # iCloud credentials from environment
        if 'icloud' not in config:
            config['icloud'] = {}
        
        env_apple_id = os.getenv('ICLOUD_APPLE_ID')
        if env_apple_id:
            config['icloud']['apple_id'] = env_apple_id
        
        env_password = os.getenv('ICLOUD_PASSWORD')
        if env_password:
            config['icloud']['password'] = env_password
        
        env_2fa_code = os.getenv('ICLOUD_2FA_CODE')
        if env_2fa_code:
            config['icloud']['two_fa_code'] = env_2fa_code
        
        env_device_id = os.getenv('ICLOUD_2FA_DEVICE_ID')
        if env_device_id:
            config['icloud']['trusted_device_id'] = env_device_id
        
        # Google Drive credentials
        if 'google_drive' not in config:
            config['google_drive'] = {}
        
        env_credentials = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE')
        if env_credentials:
            config['google_drive']['credentials_file'] = env_credentials
        
        return config

