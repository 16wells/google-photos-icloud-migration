"""
Tests for drive_downloader.py module.
"""
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from drive_downloader import DriveDownloader, SCOPES


class TestDriveDownloader:
    """Test cases for DriveDownloader class."""
    
    def test_initialization(self, credentials_file, tmp_path):
        """Test that DriveDownloader can be initialized."""
        with patch('drive_downloader.build') as mock_build, \
             patch('drive_downloader.Credentials') as mock_creds:
            # Mock credentials
            mock_creds.from_authorized_user_file.return_value = None
            mock_creds_obj = Mock()
            mock_creds_obj.valid = True
            mock_creds.return_value = mock_creds_obj
            
            # Mock service
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            downloader = DriveDownloader(str(credentials_file))
            
            assert downloader.credentials_file == str(credentials_file)
            assert downloader.service is not None
    
    @patch('drive_downloader.os.path.exists')
    @patch('drive_downloader.Credentials')
    @patch('drive_downloader.build')
    def test_authenticate_with_existing_token(self, mock_build, mock_creds, mock_exists, credentials_file):
        """Test authentication with existing valid token."""
        mock_exists.return_value = True
        mock_cred_obj = Mock()
        mock_cred_obj.valid = True
        mock_creds.from_authorized_user_file.return_value = mock_cred_obj
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        downloader = DriveDownloader(str(credentials_file))
        
        assert downloader.service == mock_service
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_cred_obj)
    
    @patch('drive_downloader.build')
    @patch('drive_downloader.InstalledAppFlow')
    @patch('drive_downloader.Credentials')
    @patch('drive_downloader.os.path.exists')
    def test_list_zip_files(self, mock_exists, mock_creds, mock_flow, mock_build, credentials_file, mock_drive_service):
        """Test listing zip files from Google Drive."""
        mock_exists.return_value = False
        mock_build.return_value = mock_drive_service
        
        downloader = DriveDownloader(str(credentials_file))
        zip_files = downloader.list_zip_files(folder_id='test_folder', pattern='takeout-*.zip')
        
        assert len(zip_files) == 2
        assert zip_files[0]['name'] == 'takeout-001.zip'
        assert zip_files[1]['name'] == 'takeout-002.zip'
    
    @patch('drive_downloader.build')
    @patch('drive_downloader.MediaIoBaseDownload')
    @patch('drive_downloader.InstalledAppFlow')
    @patch('drive_downloader.Credentials')
    @patch('drive_downloader.os.path.exists')
    def test_download_file(self, mock_exists, mock_creds, mock_flow, mock_download, mock_build, 
                          credentials_file, mock_drive_service, tmp_path):
        """Test downloading a file from Google Drive."""
        mock_exists.return_value = False
        mock_build.return_value = mock_drive_service
        
        # Mock file download
        mock_request = Mock()
        mock_download_obj = Mock()
        mock_download_obj.next_chunk.return_value = (None, True)
        mock_download.return_value = mock_download_obj
        
        mock_drive_service.files.return_value.get_media.return_value = mock_request
        
        downloader = DriveDownloader(str(credentials_file))
        output_path = tmp_path / 'downloaded.zip'
        
        result = downloader.download_file('file1', output_path)
        
        assert result is True
        mock_download.assert_called_once()
    
    @patch('drive_downloader.build')
    @patch('drive_downloader.InstalledAppFlow')
    @patch('drive_downloader.Credentials')
    @patch('drive_downloader.os.path.exists')
    def test_list_zip_files_with_pattern(self, mock_exists, mock_creds, mock_flow, mock_build,
                                        credentials_file, mock_drive_service):
        """Test listing zip files with pattern matching."""
        mock_exists.return_value = False
        mock_build.return_value = mock_drive_service
        
        downloader = DriveDownloader(str(credentials_file))
        zip_files = downloader.list_zip_files(pattern='takeout-*.zip')
        
        # Should filter by pattern
        assert all('takeout-' in f['name'] for f in zip_files)
    
    @patch('drive_downloader.build')
    @patch('drive_downloader.InstalledAppFlow')
    @patch('drive_downloader.Credentials')
    @patch('drive_downloader.os.path.exists')
    def test_is_headless_environment(self, mock_exists, mock_creds, mock_flow, mock_build, credentials_file):
        """Test headless environment detection."""
        mock_exists.return_value = False
        
        with patch('drive_downloader.os.environ', {'DISPLAY': ''}):
            downloader = DriveDownloader(str(credentials_file))
            assert downloader._is_headless_environment() is True
        
        with patch('drive_downloader.os.environ', {'DISPLAY': ':0'}):
            downloader = DriveDownloader(str(credentials_file))
            assert downloader._is_headless_environment() is False

