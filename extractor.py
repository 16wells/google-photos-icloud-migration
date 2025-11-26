"""
Extract zip files and identify media/JSON file pairs.
"""
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from tqdm import tqdm

from exceptions import ExtractionError

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
        Extract a zip file maintaining directory structure.
        
        Args:
            zip_path: Path to zip file
            extract_to: Optional destination directory (defaults to extracted_dir)
        
        Returns:
            Path to extracted directory
        """
        if extract_to is None:
            # Create a subdirectory based on zip file name
            extract_to = self.extracted_dir / zip_path.stem
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        # Validate zip file before extraction
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                test_zip.testzip()
        except zipfile.BadZipFile as e:
            raise ExtractionError(
                f"File '{zip_path.name}' is not a valid zip file. "
                f"It may be corrupted or incomplete. File size: {zip_path.stat().st_size / (1024*1024):.1f} MB. "
                f"Consider re-downloading this file from Google Drive."
            ) from e
        except (OSError, IOError) as e:
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
            
            # Extract with progress bar
            for file_info in tqdm(file_list, desc=f"Extracting {zip_path.name}"):
                zip_ref.extract(file_info, extract_to)
        
        logger.info(f"Extracted {zip_path.name}")
        return extract_to
    
    def extract_all_zips(self, zip_files: List[Path]) -> List[Path]:
        """
        Extract all zip files.
        
        Args:
            zip_files: List of zip file paths
        
        Returns:
            List of extracted directory paths
        """
        extracted_dirs = []
        
        for zip_file in zip_files:
            extracted_dir = self.extract_zip(zip_file)
            extracted_dirs.append(extracted_dir)
        
        return extracted_dirs
    
    def find_media_files(self, directory: Path) -> List[Path]:
        """
        Find all media files in a directory recursively.
        
        Args:
            directory: Directory to search
        
        Returns:
            List of media file paths
        """
        media_files = []
        
        for ext in MEDIA_EXTENSIONS:
            media_files.extend(directory.rglob(f"*{ext}"))
            media_files.extend(directory.rglob(f"*{ext.upper()}"))
        
        logger.debug(f"Found {len(media_files)} media files in {directory}")
        return media_files
    
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
        
        Args:
            directory: Directory to search
        
        Returns:
            Dictionary mapping media file paths to JSON file paths (or None)
        """
        media_files = self.find_media_files(directory)
        pairs = {}
        
        for media_file in media_files:
            json_file = self.find_json_metadata(media_file)
            pairs[media_file] = json_file
        
        logger.info(f"Identified {len(pairs)} media files, "
                   f"{sum(1 for v in pairs.values() if v is not None)} with JSON metadata")
        
        return pairs
    
    def get_album_structure(self, directory: Path) -> Dict[str, List[Path]]:
        """
        Extract album structure from directory hierarchy.
        
        Google Takeout often organizes files by album in folders.
        
        Args:
            directory: Root directory to analyze
        
        Returns:
            Dictionary mapping album names to lists of media file paths
        """
        albums = {}
        media_files = self.find_media_files(directory)
        
        for media_file in media_files:
            # Get relative path from root
            rel_path = media_file.relative_to(directory)
            
            # Album is typically the parent directory name
            # Skip if file is directly in root
            if len(rel_path.parts) > 1:
                album_name = rel_path.parts[0]
                
                if album_name not in albums:
                    albums[album_name] = []
                albums[album_name].append(media_file)
        
        logger.info(f"Identified {len(albums)} albums from directory structure")
        return albums

