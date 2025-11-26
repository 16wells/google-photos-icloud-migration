"""
Configuration management using dataclasses for type safety and validation.
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
    """Google Drive configuration."""
    credentials_file: str
    folder_id: Optional[str] = None
    zip_file_pattern: str = "takeout-*.zip"
    
    def __post_init__(self):
        """Validate Google Drive configuration."""
        if not self.credentials_file:
            raise ValueError("credentials_file is required for Google Drive")
        
        # Check if credentials file exists
        creds_path = Path(self.credentials_file)
        if not creds_path.exists():
            logger.warning(f"Credentials file not found: {self.credentials_file}")


@dataclass
class ICloudConfig:
    """iCloud configuration."""
    apple_id: Optional[str] = None
    password: Optional[str] = None
    trusted_device_id: Optional[str] = None
    two_fa_code: Optional[str] = None
    photos_library_path: Optional[str] = None
    method: str = "photokit"  # 'api' or 'photokit'
    
    def __post_init__(self):
        """Apply environment variable overrides."""
        # Override with environment variables if present
        if not self.apple_id:
            self.apple_id = os.getenv('ICLOUD_APPLE_ID')
        if not self.password:
            self.password = os.getenv('ICLOUD_PASSWORD')
        if not self.two_fa_code:
            self.two_fa_code = os.getenv('ICLOUD_2FA_CODE')
        if not self.trusted_device_id:
            self.trusted_device_id = os.getenv('ICLOUD_2FA_DEVICE_ID')


@dataclass
class ProcessingConfig:
    """Processing configuration."""
    base_dir: str
    zip_dir: str = "zips"
    extracted_dir: str = "extracted"
    processed_dir: str = "processed"
    batch_size: int = 100
    cleanup_after_upload: bool = True
    max_workers: Optional[int] = None  # None = auto-detect (recommended)
    enable_parallel_processing: bool = True
    
    def __post_init__(self):
        """Validate processing configuration."""
        if not self.base_dir:
            raise ValueError("base_dir is required")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
    
    @property
    def base_path(self) -> Path:
        """Get base directory as Path object."""
        return Path(self.base_dir)
    
    @property
    def zip_path(self) -> Path:
        """Get zip directory as Path object."""
        return self.base_path / self.zip_dir
    
    @property
    def extracted_path(self) -> Path:
        """Get extracted directory as Path object."""
        return self.base_path / self.extracted_dir
    
    @property
    def processed_path(self) -> Path:
        """Get processed directory as Path object."""
        return self.base_path / self.processed_dir


@dataclass
class MetadataConfig:
    """Metadata preservation configuration."""
    preserve_dates: bool = True
    preserve_gps: bool = True
    preserve_descriptions: bool = True
    preserve_albums: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "migration.log"
    
    def __post_init__(self):
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {self.level}. Must be one of {valid_levels}")


@dataclass
class MigrationConfig:
    """Main migration configuration."""
    google_drive: GoogleDriveConfig
    processing: ProcessingConfig
    icloud: ICloudConfig = field(default_factory=ICloudConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, config_path: str, validate: bool = True) -> 'MigrationConfig':
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            validate: Whether to validate against JSON schema
        
        Returns:
            MigrationConfig instance
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
        
        Args:
            config_dict: Configuration dictionary
        
        Returns:
            MigrationConfig instance
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
        """Validate configuration against JSON schema."""
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
        """Apply environment variable overrides to configuration dictionary."""
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

