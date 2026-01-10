"""
Security utilities for credential storage and management.
"""
import os
import sys
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try to import keyring for secure credential storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.debug("keyring library not available - using environment variables only")


class SecureCredentialStore:
    """
    Secure credential storage using macOS Keychain (via keyring) or environment variables.
    
    Prefers keyring for macOS Keychain integration, falls back to environment variables.
    """
    
    SERVICE_NAME = "google-photos-icloud-migration"
    
    @classmethod
    def get_credential(cls, key: str, username: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential from secure storage.
        
        Args:
            key: The credential key (e.g., 'google_drive_client_secret')
            username: Optional username for keyring (defaults to current user)
            
        Returns:
            The credential value or None if not found
        """
        # First check environment variables (highest priority)
        env_key = key.upper().replace('-', '_')
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
        
        # Then try keyring (macOS Keychain)
        if KEYRING_AVAILABLE:
            try:
                username = username or os.getenv('USER', 'default')
                credential = keyring.get_password(cls.SERVICE_NAME, f"{username}:{key}")
                if credential:
                    logger.debug(f"Retrieved credential '{key}' from keyring")
                    return credential
            except Exception as e:
                logger.debug(f"Could not retrieve credential from keyring: {e}")
        
        return None
    
    @classmethod
    def set_credential(cls, key: str, value: str, username: Optional[str] = None) -> bool:
        """
        Store a credential in secure storage.
        
        Args:
            key: The credential key (e.g., 'google_drive_client_secret')
            value: The credential value
            username: Optional username for keyring (defaults to current user)
            
        Returns:
            True if successfully stored, False otherwise
        """
        if not value:
            logger.warning(f"Attempted to store empty credential for '{key}'")
            return False
        
        if KEYRING_AVAILABLE:
            try:
                username = username or os.getenv('USER', 'default')
                keyring.set_password(cls.SERVICE_NAME, f"{username}:{key}", value)
                logger.debug(f"Stored credential '{key}' in keyring")
                return True
            except Exception as e:
                logger.warning(f"Could not store credential in keyring: {e}")
                return False
        else:
            logger.warning(
                f"keyring not available - credential '{key}' not stored. "
                f"Install with: pip install keyring"
            )
            return False
    
    @classmethod
    def delete_credential(cls, key: str, username: Optional[str] = None) -> bool:
        """
        Delete a credential from secure storage.
        
        Args:
            key: The credential key
            username: Optional username for keyring (defaults to current user)
            
        Returns:
            True if successfully deleted, False otherwise
        """
        if KEYRING_AVAILABLE:
            try:
                username = username or os.getenv('USER', 'default')
                keyring.delete_password(cls.SERVICE_NAME, f"{username}:{key}")
                logger.debug(f"Deleted credential '{key}' from keyring")
                return True
            except keyring.errors.PasswordDeleteError:
                logger.debug(f"Credential '{key}' not found in keyring")
                return False
            except Exception as e:
                logger.warning(f"Could not delete credential from keyring: {e}")
                return False
        
        return False
    
    @classmethod
    def is_available(cls) -> bool:
        """
        Check if secure credential storage is available.
        
        Returns:
            True if keyring is available, False otherwise
        """
        return KEYRING_AVAILABLE


def sanitize_path(path: str) -> str:
    """
    Sanitize file paths to prevent directory traversal attacks.
    
    Args:
        path: The path to sanitize
        
    Returns:
        Sanitized path
    """
    # Resolve to absolute path to prevent traversal
    resolved = Path(path).resolve()
    
    # Check for dangerous patterns
    path_str = str(resolved)
    if '..' in path_str:
        raise ValueError(f"Path contains directory traversal: {path}")
    
    return path_str


def validate_file_path(path: str, must_exist: bool = False, must_be_file: bool = False) -> Path:
    """
    Validate a file path and return Path object.
    
    Args:
        path: The path to validate
        must_exist: If True, path must exist
        must_be_file: If True, path must be a file (not directory)
        
    Returns:
        Path object
        
    Raises:
        ValueError: If validation fails
    """
    try:
        sanitized = sanitize_path(path)
        path_obj = Path(sanitized)
        
        if must_exist and not path_obj.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        if must_be_file and path_obj.exists() and not path_obj.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        return path_obj
    except Exception as e:
        raise ValueError(f"Invalid file path '{path}': {e}")


def validate_file_size(file_path: Path, max_size_mb: Optional[float] = None) -> bool:
    """
    Validate file size is within acceptable limits.
    
    Args:
        file_path: Path to file
        max_size_mb: Maximum size in MB (None = no limit)
        
    Returns:
        True if valid, False otherwise
    """
    if not file_path.exists():
        return False
    
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    if max_size_mb and size_mb > max_size_mb:
        logger.warning(f"File {file_path} is {size_mb:.1f} MB, exceeds limit of {max_size_mb:.1f} MB")
        return False
    
    return True
