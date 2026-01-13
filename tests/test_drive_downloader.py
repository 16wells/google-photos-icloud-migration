"""
Tests for drive_downloader.py module.
"""
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from google_photos_icloud_migration.downloader.drive_downloader import DriveDownloader, SCOPES


class TestDriveDownloader:
    """Test cases for DriveDownloader class."""
    
    def _setup_oauth_mocks(self, mock_flow, mock_creds, mock_exists, mock_build, mock_drive_service=None):
        """Helper to set up OAuth flow mocks for all tests."""
        # Mock no token file exists - will trigger OAuth flow
        mock_exists.return_value = False
        
        # Mock credentials object
        mock_creds_obj = Mock()
        mock_creds_obj.valid = True
        mock_creds_obj.to_json.return_value = '{"token": "test"}'
        
        # Mock Credentials.from_authorized_user_file to return None (no cached token)
        mock_creds.from_authorized_user_file.return_value = None
        
        # Mock OAuth flow
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = mock_creds_obj
        mock_flow_instance.credentials = mock_creds_obj
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        # Mock service
        if mock_drive_service:
            mock_build.return_value = mock_drive_service
        else:
            mock_service = Mock()
            mock_build.return_value = mock_service
        
        return mock_creds_obj
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.InstalledAppFlow')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    def test_initialization(self, mock_exists, mock_creds, mock_flow, mock_build, credentials_file, tmp_path):
        """Test that DriveDownloader can be initialized."""
        self._setup_oauth_mocks(mock_flow, mock_creds, mock_exists, mock_build)
        
        downloader = DriveDownloader(str(credentials_file))
        
        assert downloader.credentials_file == str(credentials_file)
        assert downloader.service is not None
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
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
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.InstalledAppFlow')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    def test_list_zip_files(self, mock_exists, mock_creds, mock_flow, mock_build, credentials_file, mock_drive_service):
        """Test listing zip files from Google Drive."""
        self._setup_oauth_mocks(mock_flow, mock_creds, mock_exists, mock_build, mock_drive_service)
        
        downloader = DriveDownloader(str(credentials_file))
        zip_files = downloader.list_zip_files(folder_id='test_folder', pattern='takeout-*.zip')
        
        assert len(zip_files) == 2
        assert zip_files[0]['name'] == 'takeout-001.zip'
        assert zip_files[1]['name'] == 'takeout-002.zip'
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.MediaIoBaseDownload')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.InstalledAppFlow')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    def test_download_file(self, mock_exists, mock_creds, mock_flow, mock_download, mock_build, 
                          credentials_file, mock_drive_service, tmp_path):
        """Test downloading a file from Google Drive."""
        self._setup_oauth_mocks(mock_flow, mock_creds, mock_exists, mock_build, mock_drive_service)
        
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
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.InstalledAppFlow')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    def test_list_zip_files_with_pattern(self, mock_exists, mock_creds, mock_flow, mock_build,
                                        credentials_file, mock_drive_service):
        """Test listing zip files with pattern matching."""
        self._setup_oauth_mocks(mock_flow, mock_creds, mock_exists, mock_build, mock_drive_service)
        
        downloader = DriveDownloader(str(credentials_file))
        zip_files = downloader.list_zip_files(pattern='takeout-*.zip')
        
        # Should filter by pattern
        assert all('takeout-' in f['name'] for f in zip_files)
    
    @patch('google_photos_icloud_migration.downloader.drive_downloader.build')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.InstalledAppFlow')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.Credentials')
    @patch('google_photos_icloud_migration.downloader.drive_downloader.os.path.exists')
    @patch('builtins.input')  # Mock input() for headless mode
    def test_is_headless_environment(self, mock_input, mock_exists, mock_creds, mock_flow, mock_build, credentials_file):
        """Test headless environment detection."""
        mock_exists.return_value = False
        mock_creds.from_authorized_user_file.return_value = None
        
        # Mock credentials object
        mock_creds_obj = Mock()
        mock_creds_obj.valid = True
        mock_creds_obj.to_json.return_value = '{"token": "test"}'
        
        # Mock OAuth flow for headless mode
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = ('http://example.com/auth', 'state')
        mock_flow_instance.fetch_token.return_value = None
        mock_flow_instance.credentials = mock_creds_obj
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        mock_input.return_value = 'http://localhost:8080/?code=test123'
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        with patch('google_photos_icloud_migration.downloader.drive_downloader.os.environ', {'SSH_CLIENT': '1'}):
            downloader = DriveDownloader(str(credentials_file))
            assert downloader._is_headless_environment() is True
        
        # Mock OAuth flow for non-headless mode
        mock_flow_instance2 = Mock()
        mock_flow_instance2.run_local_server.return_value = mock_creds_obj
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance2
        
        with patch('google_photos_icloud_migration.downloader.drive_downloader.os.environ', {'DISPLAY': ':0'}):
            downloader = DriveDownloader(str(credentials_file))
            assert downloader._is_headless_environment() is False
