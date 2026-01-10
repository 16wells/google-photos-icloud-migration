"""
Tests for icloud_uploader.py module (PhotoKit-based uploader only).
"""
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Check if PhotoKit is available (optional dependency)
try:
    from Photos import PHPhotoLibrary
    PHOTOKIT_AVAILABLE = True
except ImportError:
    PHOTOKIT_AVAILABLE = False

from google_photos_icloud_migration.exceptions import AuthenticationError, UploadError

# Import PhotoKit uploader - may not be available if pyobjc-framework-Photos isn't installed
PHOTOS_SYNC_UPLOADER_AVAILABLE = True
try:
    from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
except (ImportError, RuntimeError, AttributeError):
    PHOTOS_SYNC_UPLOADER_AVAILABLE = False
    iCloudPhotosSyncUploader = None  # Will be skipped in tests


class TestICloudPhotosSyncUploader:
    """Test cases for iCloudPhotosSyncUploader class (PhotoKit-based)."""
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system')
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.PHPhotoLibrary')
    def test_initialization_macos(self, mock_library, mock_platform):
        """Test initialization on macOS."""
        mock_platform.return_value = 'Darwin'
        
        mock_lib = Mock()
        mock_lib.authorizationStatus.return_value = 3  # Authorized
        mock_library.return_value = mock_lib
        
        uploader = iCloudPhotosSyncUploader()
        
        assert uploader is not None
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system')
    def test_initialization_non_macos(self, mock_platform):
        """Test that initialization fails on non-macOS."""
        mock_platform.return_value = 'Linux'
        
        with pytest.raises(RuntimeError, match="macOS"):
            iCloudPhotosSyncUploader()
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system')
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.PHPhotoLibrary')
    def test_upload_file_image(self, mock_library, mock_platform, tmp_path):
        """Test uploading an image file."""
        mock_platform.return_value = 'Darwin'
        mock_lib = Mock()
        mock_lib.authorizationStatus.return_value = 3  # Authorized
        
        # Mock PhotoKit components
        with patch('google_photos_icloud_migration.uploader.icloud_uploader.PHAssetChangeRequest') as mock_request, \
             patch('google_photos_icloud_migration.uploader.icloud_uploader.NSURL') as mock_url, \
             patch('google_photos_icloud_migration.uploader.icloud_uploader.NSDate') as mock_date, \
             patch('google_photos_icloud_migration.uploader.icloud_uploader.NSRunLoop') as mock_runloop:
            
            # Setup mocks
            mock_change_request = Mock()
            mock_placeholder = Mock()
            mock_change_request.creationRequestForAssetFromImageAtFileURL_.return_value = mock_change_request
            mock_change_request.placeholderForCreatedAsset.return_value = mock_placeholder
            mock_request.return_value = mock_change_request
            
            mock_library.return_value = mock_lib
            
            uploader = iCloudPhotosSyncUploader()
            
            # Create test image file
            test_image = tmp_path / 'test.jpg'
            test_image.write_bytes(b'fake image data')
            
            # Mock the performChanges callback to succeed
            def perform_changes_callback(callback):
                callback()  # Call immediately for testing
            
            mock_lib.performChanges_completionHandler_ = Mock(side_effect=perform_changes_callback)
            
            # Test upload (this is simplified - actual PhotoKit calls are more complex)
            # result = uploader.upload_file(test_image)
            # assert result is True or False (depending on mock setup)
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    @patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system')
    def test_permission_request(self, mock_platform):
        """Test permission request flow."""
        mock_platform.return_value = 'Darwin'
        
        with patch('google_photos_icloud_migration.uploader.icloud_uploader.PHPhotoLibrary') as mock_library:
            mock_lib = Mock()
            # Test various authorization statuses
            mock_lib.authorizationStatus.return_value = 0  # NotDetermined
            mock_library.return_value = mock_lib
            
            # Permission request would be tested with more complex mocking
            # This is a placeholder test structure
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    def test_get_file_identifier(self, tmp_path):
        """Test file identifier generation."""
        test_file = tmp_path / 'test.jpg'
        test_file.write_bytes(b'test data')
        
        uploader = iCloudPhotosSyncUploader()
        identifier = uploader._get_file_identifier(test_file)
        
        assert isinstance(identifier, str)
        assert len(identifier) > 0
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    def test_upload_tracking_file_path(self, tmp_path):
        """Test upload tracking file handling."""
        tracking_file = tmp_path / 'tracking.json'
        
        with patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system', return_value='Darwin'), \
             patch('google_photos_icloud_migration.uploader.icloud_uploader.PHPhotoLibrary') as mock_library:
            mock_lib = Mock()
            mock_lib.authorizationStatus.return_value = 3  # Authorized
            mock_library.return_value = mock_lib
            
            uploader = iCloudPhotosSyncUploader(upload_tracking_file=tracking_file)
            assert uploader.upload_tracking_file == tracking_file
    
    @pytest.mark.skipif(not PHOTOS_SYNC_UPLOADER_AVAILABLE, reason="iCloudPhotosSyncUploader not available")
    @pytest.mark.skipif(not PHOTOKIT_AVAILABLE, reason="PhotoKit framework not available")
    def test_is_file_already_uploaded_empty_tracking(self, tmp_path):
        """Test checking uploaded status with no tracking file."""
        test_file = tmp_path / 'test.jpg'
        test_file.write_bytes(b'test data')
        
        with patch('google_photos_icloud_migration.uploader.icloud_uploader.platform.system', return_value='Darwin'), \
             patch('google_photos_icloud_migration.uploader.icloud_uploader.PHPhotoLibrary') as mock_library:
            mock_lib = Mock()
            mock_lib.authorizationStatus.return_value = 3  # Authorized
            mock_library.return_value = mock_lib
            
            uploader = iCloudPhotosSyncUploader(upload_tracking_file=None)
            assert uploader._is_file_already_uploaded(test_file) is False
