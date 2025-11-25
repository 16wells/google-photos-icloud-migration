"""
Upload media files to iCloud Photos using pyicloud library.
"""
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloud2SARequiredException
from tqdm import tqdm

logger = logging.getLogger(__name__)


class iCloudUploader:
    """Handles uploading media files to iCloud Photos."""
    
    def __init__(self, apple_id: str, password: str, 
                 trusted_device_id: Optional[str] = None):
        """
        Initialize the iCloud uploader.
        
        Args:
            apple_id: Apple ID email
            password: Apple ID password (empty string will prompt)
            trusted_device_id: Optional trusted device ID for 2FA
        """
        self.apple_id = apple_id
        self.password = password.strip() if password else ''
        self.trusted_device_id = trusted_device_id
        self.api = None
        
        # Prompt for password if empty
        if not self.password:
            import getpass
            logger.info("iCloud password not provided. Please enter your Apple ID password:")
            logger.info("(Note: If you have 2FA enabled, use your regular password)")
            self.password = getpass.getpass("Password: ")
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with iCloud."""
        try:
            self.api = PyiCloudService(self.apple_id, self.password)
            
            # Handle 2FA if required
            if self.api.requires_2fa:
                logger.info("Two-factor authentication required")
                
                if self.trusted_device_id:
                    # Use trusted device
                    device = self.api.trusted_devices[int(self.trusted_device_id)]
                    device_name = device.get('deviceName', 'Unknown')
                    logger.info(f"Using trusted device: {device_name}")
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    logger.info(f"Verification code sent to {device_name}")
                else:
                    # List available devices
                    devices = self.api.trusted_devices
                    logger.info("Available trusted devices:")
                    for i, device in enumerate(devices):
                        device_name = device.get('deviceName', 'Unknown')
                        device_type = device.get('deviceType', 'Unknown')
                        logger.info(f"  {i}: {device_name} ({device_type})")
                    
                    device_index = input("Select device (enter number): ").strip()
                    device = devices[int(device_index)]
                    device_name = device.get('deviceName', 'Unknown')
                    
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    logger.info(f"Verification code sent to {device_name}")
                
                # Allow retries for 2FA code
                max_attempts = 3
                for attempt in range(max_attempts):
                    code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
                    # Remove any spaces or dashes from the code
                    code = code.replace(' ', '').replace('-', '')
                    
                    if self.api.validate_verification_code(device, code):
                        logger.info("✓ Verification code accepted")
                        break
                    else:
                        if attempt < max_attempts - 1:
                            logger.warning("Invalid verification code. Please try again.")
                            logger.info("Note: Codes expire quickly. You may need to request a new code.")
                            retry = input("Request new code? (y/n): ").strip().lower()
                            if retry == 'y':
                                if not self.api.send_verification_code(device):
                                    raise Exception("Failed to send new verification code")
                                logger.info("New verification code sent")
                        else:
                            raise Exception("Invalid verification code after multiple attempts")
            
            logger.info("Successfully authenticated with iCloud")
            
        except PyiCloudFailedLoginException as e:
            raise Exception(f"Failed to login to iCloud: {e}")
        except Exception as e:
            raise Exception(f"Authentication error: {e}")
    
    def create_album(self, album_name: str) -> bool:
        """
        Create an album in iCloud Photos.
        
        Note: pyicloud may not support album creation directly.
        This is a placeholder for future implementation.
        
        Args:
            album_name: Name of the album to create
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # pyicloud doesn't have direct album creation support
            # Albums may need to be created manually or through Photos app
            logger.warning(f"Album creation not supported via API: {album_name}")
            logger.info("Albums will need to be created manually in iCloud Photos")
            return False
        except Exception as e:
            logger.error(f"Failed to create album {album_name}: {e}")
            return False
    
    def upload_photo(self, photo_path: Path) -> bool:
        """
        Upload a single photo to iCloud Photos.
        
        Args:
            photo_path: Path to photo file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # pyicloud's photo upload functionality may be limited
            # The Photos API doesn't have a public upload endpoint
            # This is a placeholder - actual implementation may require
            # using Photos app sync or alternative methods
            
            logger.warning("Direct photo upload via pyicloud may not be supported")
            logger.info(f"Would upload: {photo_path.name}")
            
            # Alternative: Use Photos library sync
            # Files would need to be copied to Photos library directory
            # which then syncs to iCloud
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to upload photo {photo_path.name}: {e}")
            return False
    
    def verify_file_uploaded(self, file_path: Path) -> bool:
        """
        Verify that a file was successfully uploaded to iCloud Photos.
        
        Note: This is a placeholder as direct API upload may not be supported.
        For actual verification, you may need to query the iCloud Photos API.
        
        Args:
            file_path: Path to the original file
        
        Returns:
            True if file is verified to be uploaded, False otherwise
        """
        try:
            # Since direct API upload may not be supported, verification is limited
            # In a real implementation, you would query the iCloud Photos API
            # to check if the file exists
            
            # For now, if upload_photo returned True, we assume it's uploaded
            # This is a placeholder - actual verification would require API query
            logger.debug(f"Verification not fully supported for API uploader: {file_path.name}")
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying file {file_path.name}: {e}")
            return False
    
    def upload_photos_batch(self, photo_paths: List[Path], 
                           album_name: Optional[str] = None,
                           verify_after_upload: bool = True,
                           on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:
        """
        Upload multiple photos in a batch.
        
        Args:
            photo_paths: List of photo file paths
            album_name: Optional album name to add photos to
            verify_after_upload: If True, verify each file after upload
            on_verification_failure: Optional callback function(file_path) called when verification fails
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for photo_path in tqdm(photo_paths, desc=f"Uploading photos"):
            success = self.upload_photo(photo_path)
            
            # Verify upload if requested
            if success and verify_after_upload:
                verified = self.verify_file_uploaded(photo_path)
                if not verified:
                    logger.warning(f"Upload verification failed for {photo_path.name}")
                    if on_verification_failure:
                        on_verification_failure(photo_path)
                    success = False
            
            results[photo_path] = success
            
            # Rate limiting
            time.sleep(0.5)
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Uploaded {successful}/{len(results)} photos")
        
        return results
    
    def upload_video(self, video_path: Path) -> bool:
        """
        Upload a single video to iCloud Photos.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if successful, False otherwise
        """
        # Similar to photo upload - may not be directly supported
        logger.warning(f"Video upload may not be supported: {video_path.name}")
        return False


class iCloudPhotosSyncUploader:
    """
    Alternative uploader using Photos library sync method.
    
    This approach copies files to the Photos library directory,
    which then syncs to iCloud Photos automatically.
    """
    
    def __init__(self, photos_library_path: Optional[Path] = None):
        """
        Initialize the sync-based uploader.
        
        Args:
            photos_library_path: Path to Photos library (defaults to macOS default)
        """
        if photos_library_path is None:
            # Default macOS Photos library location
            home = Path.home()
            self.photos_library_path = home / "Pictures" / "Photos Library.photoslibrary"
        else:
            self.photos_library_path = photos_library_path
        
        # Photos library structure
        self.masters_path = self.photos_library_path / "Masters"
        
        logger.info(f"Using Photos library: {self.photos_library_path}")
    
    def upload_file(self, file_path: Path, album_name: Optional[str] = None) -> bool:
        """
        Copy file to Photos library for sync.
        
        Args:
            file_path: Path to media file
            album_name: Optional album name (not directly supported)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create Masters directory if it doesn't exist
            self.masters_path.mkdir(parents=True, exist_ok=True)
            
            # Organize by date (year/month)
            # This helps Photos app organize files
            import shutil
            from datetime import datetime
            
            # Try to get date from file metadata
            try:
                from PIL import Image
                from PIL.ExifTags import DATETIME
                
                img = Image.open(file_path)
                exif = img._getexif()
                if exif:
                    date_str = exif.get(DATETIME)
                    if date_str:
                        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        year = dt.year
                        month = dt.month
                    else:
                        year = datetime.now().year
                        month = datetime.now().month
                else:
                    year = datetime.now().year
                    month = datetime.now().month
            except:
                year = datetime.now().year
                month = datetime.now().month
            
            # Create year/month directory
            target_dir = self.masters_path / str(year) / f"{month:02d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            target_path = target_dir / file_path.name
            shutil.copy2(file_path, target_path)
            
            logger.debug(f"Copied {file_path.name} to Photos library")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy {file_path.name}: {e}")
            return False
    
    def verify_file_uploaded(self, file_path: Path) -> bool:
        """
        Verify that a file was successfully uploaded to iCloud Photos.
        
        For sync method, this checks if the file exists in the Photos library.
        
        Args:
            file_path: Path to the original file
        
        Returns:
            True if file is verified to be uploaded, False otherwise
        """
        try:
            from datetime import datetime
            
            # Try to get date from file metadata to find target location
            try:
                from PIL import Image
                from PIL.ExifTags import DATETIME
                
                img = Image.open(file_path)
                exif = img._getexif()
                if exif:
                    date_str = exif.get(DATETIME)
                    if date_str:
                        dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        year = dt.year
                        month = dt.month
                    else:
                        year = datetime.now().year
                        month = datetime.now().month
                else:
                    year = datetime.now().year
                    month = datetime.now().month
            except:
                year = datetime.now().year
                month = datetime.now().month
            
            # Check if file exists in Photos library
            target_dir = self.masters_path / str(year) / f"{month:02d}"
            target_path = target_dir / file_path.name
            
            if target_path.exists():
                # Also verify file size matches (basic integrity check)
                if target_path.stat().st_size == file_path.stat().st_size:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying file {file_path.name}: {e}")
            return False
    
    def upload_files_batch(self, file_paths: List[Path],
                          albums: Optional[Dict[Path, str]] = None,
                          verify_after_upload: bool = True,
                          on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:
        """
        Upload multiple files in a batch.
        
        Args:
            file_paths: List of file paths
            albums: Optional mapping of files to album names
            verify_after_upload: If True, verify each file after upload
            on_verification_failure: Optional callback function(file_path) called when verification fails
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for file_path in tqdm(file_paths, desc="Copying to Photos library"):
            album_name = albums.get(file_path) if albums else None
            success = self.upload_file(file_path, album_name)
            
            # Verify upload if requested
            if success and verify_after_upload:
                verified = self.verify_file_uploaded(file_path)
                if not verified:
                    logger.warning(f"Upload verification failed for {file_path.name}")
                    if on_verification_failure:
                        on_verification_failure(file_path)
                    success = False
            
            results[file_path] = success
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Copied {successful}/{len(results)} files to Photos library")
        
        return results

