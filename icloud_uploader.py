"""
Upload media files to iCloud Photos using pyicloud library.
"""
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
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
            password: Apple ID password
            trusted_device_id: Optional trusted device ID for 2FA
        """
        self.apple_id = apple_id
        self.password = password
        self.trusted_device_id = trusted_device_id
        self.api = None
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
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    
                    code = input("Enter 2FA code: ")
                    if not self.api.validate_verification_code(device, code):
                        raise Exception("Invalid verification code")
                else:
                    # List available devices
                    devices = self.api.trusted_devices
                    logger.info("Available trusted devices:")
                    for i, device in enumerate(devices):
                        logger.info(f"  {i}: {device.get('deviceName', 'Unknown')}")
                    
                    device_index = input("Select device (enter number): ")
                    device = devices[int(device_index)]
                    
                    if not self.api.send_verification_code(device):
                        raise Exception("Failed to send verification code")
                    
                    code = input("Enter 2FA code: ")
                    if not self.api.validate_verification_code(device, code):
                        raise Exception("Invalid verification code")
            
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
    
    def upload_photos_batch(self, photo_paths: List[Path], 
                           album_name: Optional[str] = None) -> Dict[Path, bool]:
        """
        Upload multiple photos in a batch.
        
        Args:
            photo_paths: List of photo file paths
            album_name: Optional album name to add photos to
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for photo_path in tqdm(photo_paths, desc=f"Uploading photos"):
            success = self.upload_photo(photo_path)
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
    
    def upload_files_batch(self, file_paths: List[Path],
                          albums: Optional[Dict[Path, str]] = None) -> Dict[Path, bool]:
        """
        Upload multiple files in a batch.
        
        Args:
            file_paths: List of file paths
            albums: Optional mapping of files to album names
        
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        
        for file_path in tqdm(file_paths, desc="Copying to Photos library"):
            album_name = albums.get(file_path) if albums else None
            success = self.upload_file(file_path, album_name)
            results[file_path] = success
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Copied {successful}/{len(results)} files to Photos library")
        
        return results

