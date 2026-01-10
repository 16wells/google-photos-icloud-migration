"""
Tests for security utilities.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from google_photos_icloud_migration.utils.security import (
    SecureCredentialStore,
    sanitize_path,
    validate_file_path,
    validate_file_size,
)


class TestSecureCredentialStore:
    """Tests for SecureCredentialStore class."""
    
    def test_get_credential_from_env(self):
        """Test retrieving credential from environment variable."""
        key = "test_credential"
        env_key = "TEST_CREDENTIAL"
        test_value = "test_value_from_env"
        
        with patch.dict(os.environ, {env_key: test_value}):
            result = SecureCredentialStore.get_credential(key)
            assert result == test_value
    
    def test_get_credential_not_found(self):
        """Test retrieving credential that doesn't exist."""
        key = "nonexistent_credential"
        env_key = "NONEXISTENT_CREDENTIAL"
        
        with patch.dict(os.environ, {}, clear=False):
            if env_key in os.environ:
                del os.environ[env_key]
        
        # Try with keyring unavailable
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', False):
            result = SecureCredentialStore.get_credential(key)
            assert result is None
    
    def test_set_credential_with_keyring(self):
        """Test storing credential with keyring available."""
        key = "test_key"
        value = "test_value"
        
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', True), \
             patch('keyring.set_password') as mock_set:
            result = SecureCredentialStore.set_credential(key, value)
            assert result is True
            mock_set.assert_called_once()
    
    def test_set_credential_without_keyring(self):
        """Test storing credential without keyring."""
        key = "test_key"
        value = "test_value"
        
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', False):
            result = SecureCredentialStore.set_credential(key, value)
            # Should return False when keyring unavailable
            assert result is False
    
    def test_set_credential_empty_value(self):
        """Test storing empty credential value."""
        key = "test_key"
        value = ""
        
        result = SecureCredentialStore.set_credential(key, value)
        assert result is False
    
    def test_delete_credential(self):
        """Test deleting credential."""
        key = "test_key"
        
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', True), \
             patch('keyring.delete_password') as mock_delete:
            mock_delete.return_value = None
            result = SecureCredentialStore.delete_credential(key)
            assert result is True
            mock_delete.assert_called_once()
    
    def test_is_available(self):
        """Test checking if secure storage is available."""
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', True):
            assert SecureCredentialStore.is_available() is True
        
        with patch('google_photos_icloud_migration.utils.security.KEYRING_AVAILABLE', False):
            assert SecureCredentialStore.is_available() is False


class TestPathSanitization:
    """Tests for path sanitization functions."""
    
    def test_sanitize_path_normal(self):
        """Test sanitizing a normal path."""
        path = "/tmp/test/file.txt"
        result = sanitize_path(path)
        assert isinstance(result, str)
        assert ".." not in result
    
    def test_sanitize_path_with_traversal(self):
        """Test sanitizing a path with directory traversal."""
        path = "/tmp/../../etc/passwd"
        
        with pytest.raises(ValueError, match="directory traversal"):
            sanitize_path(path)
    
    def test_validate_file_path_exists(self, tmp_path):
        """Test validating a file path that exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        result = validate_file_path(str(test_file), must_exist=True, must_be_file=True)
        assert isinstance(result, Path)
        assert result.exists()
        assert result.is_file()
    
    def test_validate_file_path_not_exists(self, tmp_path):
        """Test validating a file path that doesn't exist."""
        test_file = tmp_path / "nonexistent.txt"
        
        with pytest.raises(ValueError, match="does not exist"):
            validate_file_path(str(test_file), must_exist=True)
    
    def test_validate_file_path_is_directory(self, tmp_path):
        """Test validating a path that is a directory, not a file."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        with pytest.raises(ValueError, match="not a file"):
            validate_file_path(str(test_dir), must_exist=True, must_be_file=True)
    
    def test_validate_file_size_within_limit(self, tmp_path):
        """Test file size validation within limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_size(test_file, max_size_mb=1.0)
        assert result is True
    
    def test_validate_file_size_exceeds_limit(self, tmp_path):
        """Test file size validation exceeding limit."""
        test_file = tmp_path / "large.txt"
        # Write 2MB of data
        test_file.write_bytes(b"x" * (2 * 1024 * 1024))
        
        result = validate_file_size(test_file, max_size_mb=1.0)
        assert result is False
    
    def test_validate_file_size_nonexistent(self, tmp_path):
        """Test file size validation for nonexistent file."""
        test_file = tmp_path / "nonexistent.txt"
        
        result = validate_file_size(test_file, max_size_mb=1.0)
        assert result is False
    
    def test_validate_file_size_no_limit(self, tmp_path):
        """Test file size validation without limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = validate_file_size(test_file, max_size_mb=None)
        assert result is True
