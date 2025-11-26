#!/usr/bin/env python3
"""
Update script to run ON the VM
This will update main.py and drive_downloader.py with the fixes
"""

import sys
import os
from pathlib import Path

# Get the updated file contents
DRIVE_DOWNLOADER_UPDATES = {
    'import_shutil': "import shutil\n",
    'check_disk_space_method': '''    def _check_disk_space(self, path: Path, required_bytes: int, 
                         buffer_percent: float = 0.1) -> bool:
        """
        Check if there's enough disk space available.
        
        Args:
            path: Path to check disk space for
            required_bytes: Required bytes
            buffer_percent: Additional buffer percentage (default 10%)
        
        Returns:
            True if enough space, False otherwise
        """
        stat = shutil.disk_usage(path)
        available_bytes = stat.free
        required_with_buffer = int(required_bytes * (1 + buffer_percent))
        
        if available_bytes < required_with_buffer:
            available_gb = available_bytes / (1024 ** 3)
            required_gb = required_with_buffer / (1024 ** 3)
            logger.error(
                f"Insufficient disk space: {available_gb:.2f} GB available, "
                f"{required_gb:.2f} GB required (with {buffer_percent*100:.0f}% buffer)"
            )
            return False
        
        return True
    ''',
}

def update_drive_downloader():
    """Update drive_downloader.py"""
    file_path = Path('drive_downloader.py')
    
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return False
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if '_check_disk_space' in content and 'download_single_zip' in content:
        print("drive_downloader.py already has updates")
        return True
    
    # Add shutil import if missing
    if 'import shutil' not in content:
        content = content.replace('import os\n', 'import os\nimport shutil\n')
    
    # Add _check_disk_space method before download_file
    if '_check_disk_space' not in content:
        # Find the download_file method
        insert_pos = content.find('    def download_file(self')
        if insert_pos > 0:
            # Insert before download_file
            content = content[:insert_pos] + '''    def _check_disk_space(self, path: Path, required_bytes: int, 
                         buffer_percent: float = 0.1) -> bool:
        """
        Check if there's enough disk space available.
        
        Args:
            path: Path to check disk space for
            required_bytes: Required bytes
            buffer_percent: Additional buffer percentage (default 10%)
        
        Returns:
            True if enough space, False otherwise
        """
        stat = shutil.disk_usage(path)
        available_bytes = stat.free
        required_with_buffer = int(required_bytes * (1 + buffer_percent))
        
        if available_bytes < required_with_buffer:
            available_gb = available_bytes / (1024 ** 3)
            required_gb = required_with_buffer / (1024 ** 3)
            logger.error(
                f"Insufficient disk space: {available_gb:.2f} GB available, "
                f"{required_gb:.2f} GB required (with {buffer_percent*100:.0f}% buffer)"
            )
            return False
        
        return True
    
''' + content[insert_pos:]
    
    # Update download_file signature to include file_size parameter
    if 'def download_file(self, file_id: str, file_name: str,' in content:
        content = content.replace(
            'def download_file(self, file_id: str, file_name: str, \n                     destination_dir: Path) -> Path:',
            'def download_file(self, file_id: str, file_name: str, \n                     destination_dir: Path, file_size: Optional[int] = None) -> Path:'
        )
    
    # Add disk space check in download_file
    if '# Check disk space before downloading' not in content:
        # Find the line after "Skip if file already exists"
        check_pos = content.find('if destination_path.exists():')
        if check_pos > 0:
            # Find the end of that block
            next_line = content.find('\n        logger.info(f"Downloading', check_pos)
            if next_line > 0:
                # Insert disk space check
                disk_check = '''        
        # Check disk space before downloading
        if file_size:
            if not self._check_disk_space(destination_dir, file_size):
                raise OSError(
                    f"Insufficient disk space to download {file_name} "
                    f"({file_size / (1024**3):.2f} GB)"
                )
        
'''
                content = content[:next_line] + disk_check + content[next_line:]
    
    # Update download_all_zips to pass file_size
    if 'file_size = None' not in content or 'if \'size\' in file_info:' not in content:
        # This is complex, let's check if it needs updating
        if 'file_size=file_size' not in content:
            # Find download_all_zips and update it
            pass  # Skip for now, manual update needed
    
    # Add download_single_zip method
    if 'def download_single_zip(self' not in content:
        # Add after download_all_zips
        insert_pos = content.find('        logger.info(f"Downloaded {len(downloaded_files)} zip files")')
        if insert_pos > 0:
            # Find end of download_all_zips
            end_pos = content.find('\n\n', insert_pos)
            if end_pos > 0:
                single_zip_method = '''
    def download_single_zip(self, file_info: dict, destination_dir: Path) -> Path:
        """
        Download a single zip file.
        
        Args:
            file_info: File metadata dictionary with 'id', 'name', and optionally 'size'
            destination_dir: Directory to save zip file
        
        Returns:
            Path to downloaded file
        """
        file_size = None
        if 'size' in file_info:
            try:
                file_size = int(file_info['size'])
            except (ValueError, TypeError):
                pass
        
        return self.download_file(
            file_info['id'],
            file_info['name'],
            destination_dir,
            file_size=file_size
        )
'''
                content = content[:end_pos] + single_zip_method + content[end_pos:]
    
    # Write updated file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated {file_path}")
    return True

def update_main_py():
    """Update main.py"""
    file_path = Path('main.py')
    
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return False
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if '_find_existing_zips' in content and 'Phase 1: Listing zip files' in content:
        print("main.py already has updates")
        return True
    
    # This is too complex to do with simple string replacement
    # Instead, we'll provide instructions
    print("main.py needs manual update - the changes are too complex for automatic update")
    print("Please use the provided updated main.py file")
    return False

if __name__ == '__main__':
    print("Updating files on VM...")
    print("=" * 60)
    
    success1 = update_drive_downloader()
    success2 = update_main_py()
    
    if success1:
        print("\n✓ drive_downloader.py updated successfully")
    if not success2:
        print("\n⚠ main.py needs to be updated manually")
        print("Please copy the updated main.py from your local machine")
    
    print("\nDone!")

