#!/usr/bin/env python3
"""Patch script to add verification features to icloud_uploader.py"""
import re

# Read the existing file
with open('icloud_uploader.py', 'r') as f:
    content = f.read()

# Check if already patched
if 'verify_file_uploaded' in content and 'on_verification_failure' in content:
    print("File already has verification features!")
    exit(0)

# Add Callable to imports if not present
if 'from typing import' in content and 'Callable' not in content:
    content = content.replace(
        'from typing import List, Dict, Optional',
        'from typing import List, Dict, Optional, Callable'
    )

# Add verify_file_uploaded method to iCloudUploader class (after upload_photo)
verify_method_api = '''
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
            logger.debug(f"Verification not fully supported for API uploader: {file_path.name}")
            return False
        except Exception as e:
            logger.debug(f"Error verifying file {file_path.name}: {e}")
            return False
    '''

if 'def verify_file_uploaded(self, file_path: Path)' not in content:
    # Insert after upload_photo method
    pattern = r'(def upload_photo\(self, photo_path: Path\) -> bool:.*?return False\n\s+except Exception as e:.*?return False)'
    replacement = r'\1' + verify_method_api
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Update upload_photos_batch signature and add verification
if 'verify_after_upload: bool = True' not in content:
    # Update method signature
    content = content.replace(
        'def upload_photos_batch(self, photo_paths: List[Path], \n                           album_name: Optional[str] = None) -> Dict[Path, bool]:',
        'def upload_photos_batch(self, photo_paths: List[Path], \n                           album_name: Optional[str] = None,\n                           verify_after_upload: bool = True,\n                           on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:'
    )
    
    # Update docstring
    content = content.replace(
        '        Args:\n            photo_paths: List of photo file paths\n            album_name: Optional album name to add photos to',
        '        Args:\n            photo_paths: List of photo file paths\n            album_name: Optional album name to add photos to\n            verify_after_upload: If True, verify each file after upload\n            on_verification_failure: Optional callback function(file_path) called when verification fails'
    )
    
    # Add verification logic in the loop
    content = content.replace(
        '        for photo_path in tqdm(photo_paths, desc=f"Uploading photos"):\n            success = self.upload_photo(photo_path)\n            results[photo_path] = success',
        '        for photo_path in tqdm(photo_paths, desc=f"Uploading photos"):\n            success = self.upload_photo(photo_path)\n            \n            # Verify upload if requested\n            if success and verify_after_upload:\n                verified = self.verify_file_uploaded(photo_path)\n                if not verified:\n                    logger.warning(f"Upload verification failed for {photo_path.name}")\n                    if on_verification_failure:\n                        on_verification_failure(photo_path)\n                    success = False\n            \n            results[photo_path] = success'
    )

# Add verify_file_uploaded method to iCloudPhotosSyncUploader class
verify_method_sync = '''
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
    '''

if 'class iCloudPhotosSyncUploader' in content and 'def verify_file_uploaded(self, file_path: Path)' not in content.split('class iCloudPhotosSyncUploader')[1]:
    # Insert after upload_file method in iCloudPhotosSyncUploader
    pattern = r'(class iCloudPhotosSyncUploader:.*?def upload_file\(self, file_path: Path.*?return False\n\s+except Exception as e:.*?return False)'
    replacement = r'\1' + verify_method_sync
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Update upload_files_batch signature and add verification for sync uploader
if 'class iCloudPhotosSyncUploader' in content:
    sync_class_content = content.split('class iCloudPhotosSyncUploader')[1]
    if 'verify_after_upload: bool = True' not in sync_class_content:
        # Update method signature
        content = content.replace(
            '    def upload_files_batch(self, file_paths: List[Path],\n                          albums: Optional[Dict[Path, str]] = None) -> Dict[Path, bool]:',
            '    def upload_files_batch(self, file_paths: List[Path],\n                          albums: Optional[Dict[Path, str]] = None,\n                          verify_after_upload: bool = True,\n                          on_verification_failure: Optional[Callable[[Path], None]] = None) -> Dict[Path, bool]:'
        )
        
        # Update docstring
        content = content.replace(
            '        Args:\n            file_paths: List of file paths\n            albums: Optional mapping of files to album names',
            '        Args:\n            file_paths: List of file paths\n            albums: Optional mapping of files to album names\n            verify_after_upload: If True, verify each file after upload\n            on_verification_failure: Optional callback function(file_path) called when verification fails'
        )
        
        # Add verification logic
        content = content.replace(
            '        for file_path in tqdm(file_paths, desc="Copying to Photos library"):\n            album_name = albums.get(file_path) if albums else None\n            success = self.upload_file(file_path, album_name)\n            results[file_path] = success',
            '        for file_path in tqdm(file_paths, desc="Copying to Photos library"):\n            album_name = albums.get(file_path) if albums else None\n            success = self.upload_file(file_path, album_name)\n            \n            # Verify upload if requested\n            if success and verify_after_upload:\n                verified = self.verify_file_uploaded(file_path)\n                if not verified:\n                    logger.warning(f"Upload verification failed for {file_path.name}")\n                    if on_verification_failure:\n                        on_verification_failure(file_path)\n                    success = False\n            \n            results[file_path] = success'
        )

# Write the patched file
with open('icloud_uploader.py', 'w') as f:
    f.write(content)

print("✓ Successfully patched icloud_uploader.py with verification features!")

