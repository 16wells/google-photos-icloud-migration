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
        # Note: 1609459200 is 2021-01-01 00:00:00 UTC, but converts to local time
        timestamp = "1609459200"
        result = merger.convert_timestamp(timestamp)
        
        assert result is not None
        # Check that it's a valid date format (YYYY:MM:DD HH:MM:SS)
        assert ":" in result
        assert len(result) >= 19  # "YYYY:MM:DD HH:MM:SS" format
    
    def test_convert_invalid_timestamp(self):
        """Test that invalid timestamps return None."""
        merger = MetadataMerger()
        
        result = merger.convert_timestamp("invalid")
        assert result is None
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_success(self, mock_subprocess, tmp_path, sample_metadata_json):
        """Test successful metadata merging."""
        # Mock subprocess.run to simulate ExifTool success
        # First call is for _check_exiftool(), second is for merge_metadata()
        mock_result = Mock(returncode=0)
        mock_subprocess.return_value = mock_result
        
        merger = MetadataMerger()
        
        # Create a test image file
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        result = merger.merge_metadata(media_file, sample_metadata_json)
        
        assert result is True
        # Should be called at least once for merge_metadata (and once for _check_exiftool during init)
        assert mock_subprocess.call_count >= 1
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_no_json(self, mock_subprocess, tmp_path):
        """Test metadata merging when no JSON file is provided."""
        # Mock subprocess.run for _check_exiftool() during initialization
        mock_result = Mock(returncode=0)
        mock_subprocess.return_value = mock_result
        
        merger = MetadataMerger()
        
        # Reset call count to ignore the _check_exiftool() call
        initial_call_count = mock_subprocess.call_count
        
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        result = merger.merge_metadata(media_file, None)
        
        # Should return False when no JSON file is provided (per implementation)
        assert result is False
        # Should not call subprocess.run for merge_metadata (only for _check_exiftool)
        assert mock_subprocess.call_count == initial_call_count
    
    @patch('google_photos_icloud_migration.processor.metadata_merger.subprocess.run')
    def test_merge_metadata_exiftool_not_found(self, mock_subprocess, tmp_path, sample_metadata_json):
        """Test handling when ExifTool is not found."""
        # Skip this test if exiftool check fails during initialization
        try:
            merger = MetadataMerger()
        except Exception:
            pytest.skip("ExifTool not available - cannot test")
        
        media_file = tmp_path / 'test.jpg'
        media_file.write_bytes(b'fake image data')
        
        # Mock FileNotFoundError for exiftool
        mock_subprocess.side_effect = FileNotFoundError("exiftool not found")
        
        # The implementation raises MetadataError, not returns False
        with pytest.raises(Exception):  # MetadataError or subprocess.CalledProcessError
            merger.merge_metadata(media_file, sample_metadata_json)
    
    def test_build_exiftool_args_with_dates(self, tmp_path, sample_metadata_json):
        """Test building ExifTool arguments with date preservation."""
        merger = MetadataMerger(preserve_dates=True)
        
        media_file = tmp_path / 'test.jpg'
        json_file = sample_metadata_json
        
        # Load metadata
        with open(json_file) as f:
            metadata = json.load(f)
        
        args = merger.build_exiftool_args(media_file, json_file, metadata)
        
        # Check for date-related arguments (implementation uses DateTimeOriginal, CreateDate, ModifyDate)
        assert any('-DateTimeOriginal' in str(arg) or '-CreateDate' in str(arg) or '-ModifyDate' in str(arg) for arg in args)
        # Check that timestamp was converted to date format
        assert any(':' in str(arg) and ('2020' in str(arg) or '2021' in str(arg)) for arg in args)
    
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
        
        # Check for GPS-related arguments (implementation uses = syntax)
        assert any('-GPSLatitude=' in str(arg) for arg in args)
        assert any('-GPSLongitude=' in str(arg) for arg in args)
        assert any('37.7749' in str(arg) for arg in args)
        assert any('-122.4194' in str(arg) for arg in args)
    
    def test_build_exiftool_args_with_descriptions(self, tmp_path):
        """Test building ExifTool arguments with description preservation."""
        merger = MetadataMerger(preserve_descriptions=True)
        
        media_file = tmp_path / 'test.jpg'
        json_file = tmp_path / 'test.json'
        
        metadata = {
            'description': 'Test description'
        }
        
        args = merger.build_exiftool_args(media_file, json_file, metadata)
        
        # Check for description-related arguments (implementation uses = syntax)
        assert any('-Description=' in str(arg) or '-Caption-Abstract=' in str(arg) or '-UserComment=' in str(arg) for arg in args)
        assert any('Test description' in str(arg) for arg in args)

