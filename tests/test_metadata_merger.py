"""
Tests for metadata_merger.py module.
"""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger


class TestMetadataMerger:
    """Test cases for MetadataMerger class."""
    
    def test_initialization(self):
        """Test that MetadataMerger can be initialized with default values."""
        merger = MetadataMerger()
        
        assert merger.preserve_dates is True
        assert merger.preserve_gps is True
        assert merger.preserve_descriptions is True
    
    def test_initialization_with_options(self):
        """Test that MetadataMerger can be initialized with custom options."""
        merger = MetadataMerger(
            preserve_dates=False,
            preserve_gps=False,
            preserve_descriptions=False
        )
        
        assert merger.preserve_dates is False
        assert merger.preserve_gps is False
        assert merger.preserve_descriptions is False
    
    def test_convert_timestamp(self):
        """Test timestamp conversion."""
        merger = MetadataMerger()
        
        # Test Unix timestamp conversion
        timestamp = "1609459200"  # 2021-01-01 00:00:00 UTC
        result = merger.convert_timestamp(timestamp)
        
        assert result is not None
        assert "2021:01:01" in result or "2021-01-01" in result
    
    def test_convert_invalid_timestamp(self):
        """Test that invalid timestamps return None."""
        merger = MetadataMerger()
        
        result = merger.convert_timestamp("invalid")
        assert result is None
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_success(self, mock_subprocess, tmp_path, sample_metadata_json):
        """Test successful metadata merging."""
        merger = MetadataMerger()
        
        # Create a test image file
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        # Mock subprocess.run to simulate ExifTool success
        mock_subprocess.return_value = Mock(returncode=0)
        
        result = merger.merge_metadata(media_file, sample_metadata_json)
        
        assert result is True
        mock_subprocess.assert_called_once()
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_no_json(self, mock_subprocess, tmp_path):
        """Test metadata merging when no JSON file is provided."""
        merger = MetadataMerger()
        
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        result = merger.merge_metadata(media_file, None)
        
        # Should return True even without JSON (no-op)
        assert result is True
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_exiftool_not_found(self, mock_subprocess, tmp_path, sample_metadata_json):
        """Test handling when ExifTool is not found."""
        merger = MetadataMerger()
        
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        # Mock FileNotFoundError for exiftool
        mock_subprocess.side_effect = FileNotFoundError("exiftool not found")
        
        result = merger.merge_metadata(media_file, sample_metadata_json)
        
        assert result is False
    
    def test_build_exiftool_args_with_dates(self, tmp_path, sample_metadata_json):
        """Test building ExifTool arguments with date preservation."""
        merger = MetadataMerger(preserve_dates=True)
        
        media_file = tmp_path / 'test.jpg'
        json_file = sample_metadata_json
        
        # Load metadata
        with open(json_file) as f:
            metadata = json.load(f)
        
        args = merger.build_exiftool_args(media_file, json_file, metadata)
        
        assert '-AllDates' in args
        assert any('2021' in str(arg) or '1609459200' in str(arg) for arg in args)
    
    def test_build_exiftool_args_with_gps(self, tmp_path):
        """Test building ExifTool arguments with GPS preservation."""
        merger = MetadataMerger(preserve_gps=True)
        
        media_file = tmp_path / 'test.jpg'
        json_file = tmp_path / 'test.json'
        
        metadata = {
            'geoData': {
                'latitude': 37.7749,
                'longitude': -122.4194
            }
        }
        
        args = merger.build_exiftool_args(media_file, json_file, metadata)
        
        assert '-GPSLatitude' in args
        assert '-GPSLongitude' in args
        assert any('37.7749' in str(arg) for arg in args)
    
    def test_build_exiftool_args_with_descriptions(self, tmp_path):
        """Test building ExifTool arguments with description preservation."""
        merger = MetadataMerger(preserve_descriptions=True)
        
        media_file = tmp_path / 'test.jpg'
        json_file = tmp_path / 'test.json'
        
        metadata = {
            'description': 'Test description'
        }
        
        args = merger.build_exiftool_args(media_file, json_file, metadata)
        
        assert '-ImageDescription' in args or '-Description' in args

