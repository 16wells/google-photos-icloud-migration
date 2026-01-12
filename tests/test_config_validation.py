"""
Tests for configuration validation.
"""
import pytest
import yaml
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from google_photos_icloud_migration.config import (
    MigrationConfig,
    GoogleDriveConfig,
    ICloudConfig,
    ProcessingConfig,
    MetadataConfig,
    LoggingConfig,
)
from google_photos_icloud_migration.exceptions import ConfigurationError


class TestGoogleDriveConfig:
    """Tests for GoogleDriveConfig."""
    
    def test_google_drive_config_creation(self):
        """Test creating Google Drive config."""
        config = GoogleDriveConfig(credentials_file="credentials.json")
        assert config.credentials_file == "credentials.json"
        assert config.zip_file_pattern == "takeout-*.zip"
    
    def test_google_drive_config_with_folder_id(self):
        """Test config with folder ID."""
        config = GoogleDriveConfig(
            credentials_file="credentials.json",
            folder_id="folder123",
            zip_file_pattern="custom-*.zip"
        )
        assert config.folder_id == "folder123"
        assert config.zip_file_pattern == "custom-*.zip"
    
    def test_google_drive_config_empty_credentials(self):
        """Test config validation with empty credentials file."""
        with pytest.raises(ValueError, match="credentials_file is required"):
            GoogleDriveConfig(credentials_file="")


class TestICloudConfig:
    """Tests for ICloudConfig."""
    
    def test_icloud_config_creation(self):
        """Test creating iCloud config."""
        config = ICloudConfig()
        assert config.apple_id is None
        assert config.password is None
        assert config.method == "photokit"
    
    def test_icloud_config_with_credentials(self):
        """Test config with credentials."""
        config = ICloudConfig(
            apple_id="test@example.com",
            password="testpass",
            photos_library_path="~/Pictures/Photos Library.photoslibrary"
        )
        assert config.apple_id == "test@example.com"
        assert config.password == "testpass"
        assert config.photos_library_path == "~/Pictures/Photos Library.photoslibrary"


class TestProcessingConfig:
    """Tests for ProcessingConfig."""
    
    def test_processing_config_creation(self):
        """Test creating processing config."""
        config = ProcessingConfig(base_dir="/tmp/test")
        assert config.base_dir == "/tmp/test"
        assert config.zip_dir == "zips"
        assert config.batch_size == 100
    
    def test_processing_config_path_properties(self):
        """Test path properties."""
        config = ProcessingConfig(base_dir="/tmp/test")
        assert isinstance(config.base_path, Path)
        assert config.zip_path == Path("/tmp/test/zips")
        assert config.extracted_path == Path("/tmp/test/extracted")
        assert config.processed_path == Path("/tmp/test/processed")
    
    def test_processing_config_empty_base_dir(self):
        """Test validation with empty base directory."""
        with pytest.raises(ValueError, match="base_dir is required"):
            ProcessingConfig(base_dir="")
    
    def test_processing_config_invalid_batch_size(self):
        """Test validation with invalid batch size."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            ProcessingConfig(base_dir="/tmp/test", batch_size=0)


class TestMetadataConfig:
    """Tests for MetadataConfig."""
    
    def test_metadata_config_defaults(self):
        """Test metadata config with defaults."""
        config = MetadataConfig()
        assert config.preserve_dates is True
        assert config.preserve_gps is True
        assert config.preserve_descriptions is True
        assert config.preserve_albums is True
    
    def test_metadata_config_custom(self):
        """Test metadata config with custom values."""
        config = MetadataConfig(
            preserve_dates=False,
            preserve_gps=False,
            preserve_descriptions=False,
            preserve_albums=False
        )
        assert config.preserve_dates is False
        assert config.preserve_gps is False
        assert config.preserve_descriptions is False
        assert config.preserve_albums is False


class TestLoggingConfig:
    """Tests for LoggingConfig."""
    
    def test_logging_config_defaults(self):
        """Test logging config with defaults."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file == "migration.log"
    
    def test_logging_config_invalid_level(self):
        """Test validation with invalid log level."""
        with pytest.raises(ValueError, match="Invalid logging level"):
            LoggingConfig(level="INVALID")


class TestMigrationConfig:
    """Tests for MigrationConfig."""
    
    def test_migration_config_from_yaml_valid(self, tmp_path):
        """Test loading valid config from YAML."""
        config_dict = {
            "google_drive": {
                "credentials_file": "credentials.json",
                "zip_file_pattern": "takeout-*.zip"
            },
            "processing": {
                "base_dir": str(tmp_path)
            }
        }
        
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f)
        
        config = MigrationConfig.from_yaml(str(config_file), validate=False)
        assert isinstance(config, MigrationConfig)
        assert config.google_drive.credentials_file == "credentials.json"
        assert config.processing.base_dir == str(tmp_path)
    
    def test_migration_config_from_yaml_with_validation(self, tmp_path):
        """Test loading config with schema validation."""
        config_dict = {
            "google_drive": {
                "credentials_file": "credentials.json",
                "zip_file_pattern": "takeout-*.zip"
            },
            "processing": {
                "base_dir": str(tmp_path),
                "batch_size": 50
            }
        }
        
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f)
        
        # Should work with valid config
        config = MigrationConfig.from_yaml(str(config_file), validate=True)
        assert isinstance(config, MigrationConfig)
    
    def test_migration_config_from_yaml_invalid_schema(self, tmp_path):
        """Test loading config with invalid schema."""
        config_dict = {
            "google_drive": {
                # Missing required credentials_file
                "zip_file_pattern": "takeout-*.zip"
            },
            "processing": {
                "base_dir": str(tmp_path)
            }
        }
        
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f)
        
        # Should raise error with validation enabled
        with pytest.raises((ConfigurationError, ValueError, Exception)):
            MigrationConfig.from_yaml(str(config_file), validate=True)
    
    def test_migration_config_missing_required_fields(self, tmp_path):
        """Test config with missing required fields."""
        config_dict = {
            "google_drive": {
                "credentials_file": "credentials.json"
            }
            # Missing required "processing" section with base_dir
        }
        
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f)
        
        # ProcessingConfig requires base_dir, so this should raise an error
        with pytest.raises((ConfigurationError, ValueError, KeyError, TypeError)):
            MigrationConfig.from_yaml(str(config_file), validate=False)
