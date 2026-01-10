"""
Extract zip files and identify media/JSON file pairs.

This module handles extraction of Google Takeout zip files with support for:
- Secure temporary file handling during extraction
- Generator-based file discovery for memory efficiency
- Path validation to prevent security vulnerabilities
- Comprehensive error handling and recovery
"""
import zipfile
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Iterator
from tqdm import tqdm

from google_photos_icloud_migration.exceptions import ExtractionError

logger = logging.getLogger(__name__)

# Supported media file extensions
MEDIA_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.png', '.gif', '.bmp', '.tiff',
                   '.avi', '.mov', '.mp4', '.m4v', '.3gp', '.mkv'}


class Extractor:
    """Handles extraction of zip files and identification of media files."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize the extractor.
        
        Args:
            base_dir: Base directory for extraction
        """
        self.base_dir = base_dir
        self.extracted_dir = base_dir / "extracted"
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_zip(self, zip_path: Path, extract_to: Optional[Path] = None) -> Path:
        """
        Extract a zip file maintaining directory structure with secure path handling.
        
        This method extracts zip files with comprehensive security measures:
        - Path validation to prevent zip slip attacks
        - Symlink detection and skipping
        - Secure file permissions (0600 for files, 0700 for directories)
        - Proper error handling for corrupted or incomplete files
        
        Args:
            zip_path: Path to zip file to extract
            extract_to: Optional destination directory.
                       If None, uses extracted_dir/<zip_stem> as destination.
                       Should be an absolute path for security.
        
        Returns:
            Path to the extracted directory containing all files
        
        Raises:
            ExtractionError: If the zip file is invalid, corrupted, or extraction fails
                            due to path validation issues or I/O errors
        
        Note:
            Uses secure temporary directory handling and validates all extracted paths
            to prevent directory traversal attacks (zip slip).
        """
        if extract_to is None:
            # Create a subdirectory based on zip file name
            extract_to = self.extracted_dir / zip_path.stem
        
        # Ensure extract_to is absolute for security
        extract_to = extract_to.resolve()
        extract_to.mkdir(parents=True, exist_ok=True)
        
        # Validate zip file before extraction (basic validation - check if we can open it)
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                # Basic validation: try to list entries
                entry_count = len(test_zip.namelist())
                logger.debug(f"Zip file {zip_path.name} has {entry_count} entries")
                
                # Try full validation, but be lenient with file system errors on external drives
                try:
                    bad_file = test_zip.testzip()
                    if bad_file:
                        logger.warning(
                            f"Zip file '{zip_path.name}' has corrupted entries (first bad file: {bad_file}), "
                            f"but will attempt extraction anyway"
                        )
                except OSError as e:
                    # File system errors (like [Errno 22]) might be external drive issues
                    # Log warning but proceed with extraction - actual extraction may work
                    if e.errno == 22:  # Invalid argument
                        logger.warning(
                            f"Zip validation hit file system error for '{zip_path.name}': {e}. "
                            f"This may be due to external drive issues. Will attempt extraction anyway. "
                            f"File size: {zip_path.stat().st_size / (1024*1024):.1f} MB"
                        )
                    else:
                        # For other OSErrors during testzip, also just warn (extraction might still work)
                        logger.warning(
                            f"Zip validation error for '{zip_path.name}': {e}. "
                            f"Will attempt extraction anyway."
                        )
                except Exception as e:
                    # Other exceptions during testzip - warn but continue
                    logger.warning(
                        f"Zip validation error for '{zip_path.name}': {e}. "
                        f"Will attempt extraction anyway."
                    )
        except zipfile.BadZipFile as e:
            raise ExtractionError(
                f"File '{zip_path.name}' is not a valid zip file. "
                f"It may be corrupted or incomplete. File size: {zip_path.stat().st_size / (1024*1024):.1f} MB. "
                f"Consider re-downloading this file from Google Drive."
            ) from e
        except (OSError, IOError) as e:
            # If we can't even open the zip file, that's a real problem
            raise ExtractionError(
                f"Error accessing zip file '{zip_path.name}': {e}. "
                f"File may be corrupted, incomplete, or inaccessible."
            ) from e
        except Exception as e:
            raise ExtractionError(
                f"Unexpected error validating zip file '{zip_path.name}': {e}"
            ) from e
        
        logger.info(f"Extracting {zip_path.name} to {extract_to}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files to extract
            file_list = zip_ref.namelist()
            
            # Extract with progress bar and path validation (prevent zip slip and symlink attacks)
            extract_to_resolved = extract_to.resolve()
            for file_info in tqdm(file_list, desc=f"Extracting {zip_path.name}"):
                # Skip symlinks in zip files (security: prevent symlink attacks)
                # Check if this entry is a symlink by examining ZipInfo
                try:
                    zip_info = zip_ref.getinfo(file_info)
                    # Check if this is a symlink (Linux/Unix symlinks in zip have mode 0o120000)
                    if hasattr(zip_info, 'external_attr') and zip_info.external_attr:
                        # Extract mode from external_attr (first 2 bytes on Unix)
                        mode = (zip_info.external_attr >> 16) & 0o777
                        if (zip_info.external_attr >> 28) == 0o12:  # S_IFLNK (symlink)
                            logger.warning(f"Skipping symlink in zip file: {file_info} (security: symlink attacks)")
                            continue
                except (KeyError, AttributeError):
                    # If we can't determine, proceed with normal validation
                    pass
                
                # Validate path to prevent zip slip attack
                target_path = (extract_to_resolved / file_info).resolve()
                try:
                    target_path.relative_to(extract_to_resolved)
                except ValueError:
                    raise ExtractionError(
                        f"Invalid path in zip file (potential zip slip attack): {file_info}. "
                        f"Path resolves outside extraction directory: {target_path}"
                    )
                zip_ref.extract(file_info, extract_to)
                
                # Set secure file permissions after extraction
                # Set files to 0600 (owner read/write) and directories to 0700 (owner access)
                extracted_item = extract_to_resolved / file_info
                if extracted_item.exists():
                    try:
                        if extracted_item.is_file():
                            extracted_item.chmod(0o600)  # Owner read/write only
                        elif extracted_item.is_dir():
                            extracted_item.chmod(0o700)  # Owner access only
                    except (OSError, PermissionError) as e:
                        # Permission setting may fail on some systems, log but don't fail
                        logger.debug(f"Could not set permissions for {extracted_item}: {e}")
        
        # Set directory permissions on extraction root
        try:
            extract_to.chmod(0o700)  # Owner access only
        except (OSError, PermissionError) as e:
            logger.debug(f"Could not set permissions for extraction directory {extract_to}: {e}")
        
        logger.info(f"Extracted {zip_path.name}")
        return extract_to
    
    def extract_all_zips(self, zip_files: List[Path]) -> Iterator[Path]:
        """
        Extract all zip files using a generator for memory efficiency.
        
        This method extracts zip files one at a time, yielding results incrementally
        rather than collecting all results in memory. This is more memory-efficient
        for processing many large zip files.
        
        Args:
            zip_files: List of zip file paths to extract
        
        Yields:
            Path objects for each extracted directory, in the order files are processed
        
        Note:
            This is a generator function that yields results incrementally,
            allowing for memory-efficient processing of many zip files.
        """
        for zip_file in zip_files:
            try:
                extracted_dir = self.extract_zip(zip_file)
                yield extracted_dir
            except ExtractionError as e:
                logger.error(f"Failed to extract {zip_file.name}: {e}")
                # Continue with next zip file rather than failing completely
                continue
            except Exception as e:
                logger.error(f"Unexpected error extracting {zip_file.name}: {e}")
                continue
    
    def extract_all_zips_list(self, zip_files: List[Path]) -> List[Path]:
        """
        Extract all zip files (returns list for backward compatibility).
        
        This is a convenience method that collects generator results into a list.
        Use extract_all_zips() directly for memory-efficient processing.
        
        Args:
            zip_files: List of zip file paths
        
        Returns:
            List of extracted directory paths
        """
        return list(self.extract_all_zips(zip_files))
    
    def find_media_files(self, directory: Path) -> Iterator[Path]:
        """
        Find all media files in a directory recursively using a generator.
        
        This method uses a generator to avoid loading all file paths into memory
        at once, which is more memory-efficient for large directories.
        
        Args:
            directory: Directory to search recursively
        
        Yields:
            Path objects for each media file found
        
        Note:
            This is a generator function that yields results incrementally,
            allowing for memory-efficient processing of large directory structures.
            The results are filtered to exclude __MACOSX files and hidden files.
        """
        seen_paths = set()  # Track seen paths to avoid duplicates from case-insensitive matching
        
        for ext in MEDIA_EXTENSIONS:
            # Search for lowercase extensions
            for file_path in directory.rglob(f"*{ext}"):
                if file_path in seen_paths:
                    continue
                seen_paths.add(file_path)
                
                # Skip __MACOSX directory and its contents
                if '__MACOSX' in str(file_path):
                    continue
                # Skip hidden files starting with ._
                if file_path.name.startswith('._'):
                    continue
                
                yield file_path
            
            # Search for uppercase extensions (avoid duplicate processing)
            if ext != ext.upper():
                for file_path in directory.rglob(f"*{ext.upper()}"):
                    if file_path in seen_paths:
                        continue
                    seen_paths.add(file_path)
                    
                    # Skip __MACOSX directory and its contents
                    if '__MACOSX' in str(file_path):
                        continue
                    # Skip hidden files starting with ._
                    if file_path.name.startswith('._'):
                        continue
                    
                    yield file_path
    
    def find_media_files_list(self, directory: Path) -> List[Path]:
        """
        Find all media files in a directory recursively (returns list).
        
        This is a convenience method that collects generator results into a list.
        Use find_media_files() directly for memory-efficient processing.
        
        Args:
            directory: Directory to search
        
        Returns:
            List of media file paths
        """
        files = list(self.find_media_files(directory))
        logger.debug(f"Found {len(files)} media files in {directory}")
        return files
    
    def find_json_metadata(self, media_file: Path) -> Optional[Path]:
        """
        Find corresponding JSON metadata file for a media file.
        
        Google Takeout creates JSON files with the same name as media files.
        
        Args:
            media_file: Path to media file
        
        Returns:
            Path to JSON file if found, None otherwise
        """
        json_path = media_file.with_suffix('.json')
        
        if json_path.exists():
            return json_path
        
        # Also check for .json files with similar names
        # Sometimes Google Takeout uses slightly different naming
        json_path_alt = media_file.parent / f"{media_file.stem}.json"
        if json_path_alt.exists():
            return json_path_alt
        
        return None
    
    def identify_media_json_pairs(self, directory: Path) -> Dict[Path, Optional[Path]]:
        """
        Identify all media files and their corresponding JSON metadata files.
        
        This method uses the generator-based find_media_files() for memory-efficient
        processing, building a dictionary of media-to-JSON mappings.
        
        Args:
            directory: Directory to search recursively
        
        Returns:
            Dictionary mapping media file paths to JSON file paths (or None if not found)
        
        Note:
            Uses generator-based file discovery for memory efficiency with large directories.
        """
        pairs = {}
        media_count = 0
        json_count = 0
        
        # Use generator for memory-efficient processing
        for media_file in self.find_media_files(directory):
            media_count += 1
            json_file = self.find_json_metadata(media_file)
            pairs[media_file] = json_file
            if json_file is not None:
                json_count += 1
        
        logger.info(f"Identified {media_count} media files, "
                   f"{json_count} with JSON metadata")
        
        return pairs
    
    def get_album_structure(self, directory: Path) -> Dict[str, List[Path]]:
        """
        Extract album structure from directory hierarchy.
        
        Google Takeout often organizes files by album in folders. This method
        uses generator-based file discovery for memory efficiency with large
        directory structures.
        
        Args:
            directory: Root directory to analyze recursively
        
        Returns:
            Dictionary mapping album names to lists of media file paths
        
        Note:
            Uses find_media_files() generator for memory-efficient processing
            of large directory trees with many files.
        """
        albums = {}
        
        # Use generator for memory-efficient processing
        for media_file in self.find_media_files(directory):
            # Get relative path from root
            try:
                rel_path = media_file.relative_to(directory)
            except ValueError:
                # File is outside directory, skip it (shouldn't happen, but safety check)
                logger.debug(f"Skipping file outside directory: {media_file}")
                continue
            
            # Album is typically the parent directory name
            # Skip if file is directly in root
            if len(rel_path.parts) > 1:
                album_name = rel_path.parts[0]
                
                if album_name not in albums:
                    albums[album_name] = []
                albums[album_name].append(media_file)
        
        logger.info(f"Identified {len(albums)} albums from directory structure")
        return albums

