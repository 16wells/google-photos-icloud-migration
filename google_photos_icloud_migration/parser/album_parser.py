"""
Extract and preserve album structures from Google Takeout.

This module handles parsing album information from both directory structures
and JSON metadata files, with support for:
- Generator-based file discovery for memory efficiency
- Caching of parsed album information
- Merging album data from multiple sources (directory structure + JSON metadata)
- Comprehensive error handling and validation
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Iterator, Tuple

from google_photos_icloud_migration.exceptions import AlbumError

logger = logging.getLogger(__name__)


class AlbumParser:
    """
    Handles parsing album structures from Google Takeout.
    
    This class extracts album information from both directory structures
    and JSON metadata files, with support for:
    - Memory-efficient generator-based file discovery
    - Caching of parsed album information
    - Merging album data from multiple sources
    - Comprehensive album name cleaning and normalization
    """
    
    def __init__(self, cache_albums: bool = True, cache_ttl_seconds: int = 3600):
        """
        Initialize the album parser with optional caching.
        
        Args:
            cache_albums: Whether to cache parsed album information (default: True)
            cache_ttl_seconds: Time-to-live for cached album data in seconds (default: 1 hour)
        """
        self.albums: Dict[str, List[Path]] = {}
        self.file_to_album: Dict[Path, str] = {}
        self.cache_albums = cache_albums
        self.cache_ttl = cache_ttl_seconds
        # Cache: maps directory path -> (parsed_albums, timestamp)
        self._album_cache: Dict[Path, Tuple[Dict[str, List[Path]], float]] = {}
    
    def parse_from_directory_structure(self, directory: Path) -> Dict[str, List[Path]]:
        """
        Parse album structure from directory hierarchy using efficient file discovery.
        
        Google Takeout often organizes files by album in folders. This method uses
        the Extractor's generator-based file discovery for memory-efficient processing.
        
        Args:
            directory: Root directory to analyze recursively
        
        Returns:
            Dictionary mapping album names to lists of media file paths
        
        Note:
            Uses Extractor.find_media_files() generator for memory-efficient
            processing of large directory structures with many files.
        """
        albums = {}
        
        # Common top-level directories to skip (these are not album names)
        skip_directories = {'takeout', 'takeout-', 'photos from', 'photos'}
        
        # Use Extractor's generator-based file discovery for memory efficiency
        from google_photos_icloud_migration.processor.extractor import Extractor
        
        # Check cache first if enabled
        if self.cache_albums and directory in self._album_cache:
            cached_albums, cached_time = self._album_cache[directory]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug(f"Using cached album structure for {directory}")
                self.albums = cached_albums.copy()
                # Rebuild file_to_album mapping
                self.file_to_album = {}
                for album_name, files in self.albums.items():
                    for file_path in files:
                        self.file_to_album[file_path] = album_name
                return self.albums
        
        # Create extractor for generator-based file discovery
        extractor = Extractor(directory.parent if directory.parent != directory else Path('.'))
        
        # Find all media files using generator (memory-efficient)
        for media_file in extractor.find_media_files(directory):
            rel_path = media_file.relative_to(directory)
            
            # Skip if file is directly in root
            if len(rel_path.parts) <= 1:
                continue
            
            # Find the first directory that's not a common skip directory
            album_name = None
            for i, part in enumerate(rel_path.parts[:-1]):  # Exclude filename
                part_lower = part.lower().strip()
                # Skip common top-level directories
                if any(skip_dir in part_lower for skip_dir in skip_directories):
                    continue
                # Skip date-prefixed directories like "Photos from 2024-01-01"
                if part_lower.startswith('photos from'):
                    continue
                # Use this directory as the album name
                album_name = part
                break
            
            # If we didn't find a valid album directory, try the deepest directory before the file
            if not album_name and len(rel_path.parts) > 1:
                # Use the parent directory of the file (last directory before filename)
                album_name = rel_path.parts[-2]
            
            if album_name:
                # Clean up album name (remove common prefixes)
                album_name = self._clean_album_name(album_name)
                
                # Skip if cleaned name is empty or still a skip directory
                if album_name and album_name.lower() not in skip_directories:
                    if album_name not in albums:
                        albums[album_name] = []
                    albums[album_name].append(media_file)
        
        self.albums = albums
        
        # Build reverse mapping (file_path -> album_name)
        for album_name, files in albums.items():
            for file_path in files:
                self.file_to_album[file_path] = album_name
        
        # Cache the result if caching is enabled
        if self.cache_albums:
            self._album_cache[directory] = (albums.copy(), time.time())
            # Clean expired cache entries periodically
            if len(self._album_cache) % 50 == 0:
                self._clean_expired_album_cache()
        
        logger.info(f"Identified {len(albums)} albums from directory structure")
        return albums
    
    def _clean_expired_album_cache(self) -> None:
        """
        Remove expired entries from the album cache.
        
        This method is called periodically to prevent memory leaks from
        accumulating expired cache entries.
        """
        current_time = time.time()
        expired_paths = [
            path for path, (_, cached_time) in self._album_cache.items()
            if current_time - cached_time >= self.cache_ttl
        ]
        for path in expired_paths:
            del self._album_cache[path]
        
        if expired_paths:
            logger.debug(f"Cleaned up {len(expired_paths)} expired album cache entries")
    
    def clear_album_cache(self) -> None:
        """
        Clear all cached album information.
        
        Useful for freeing memory or forcing re-parsing of all directories.
        """
        cache_size = len(self._album_cache)
        self._album_cache.clear()
        logger.debug(f"Cleared {cache_size} album cache entries")
    
    def parse_from_json_metadata(self, media_json_pairs: Dict[Path, Optional[Path]]) -> Dict[str, List[Path]]:
        """
        Parse album information from JSON metadata files.
        
        Google Takeout JSON files may contain album information.
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON files
        
        Returns:
            Dictionary mapping album names to lists of media file paths
        """
        albums = {}
        
        for media_file, json_file in media_json_pairs.items():
            if json_file is None or not json_file.exists():
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check for album information in various possible fields
                album_name = None
                
                # Check common fields
                if 'albumData' in metadata:
                    album_data = metadata['albumData']
                    if isinstance(album_data, dict):
                        album_name = album_data.get('title') or album_data.get('name')
                    elif isinstance(album_data, str):
                        album_name = album_data
                
                if not album_name and 'googlePhotosOrigin' in metadata:
                    origin = metadata['googlePhotosOrigin']
                    if isinstance(origin, dict):
                        album_name = origin.get('albumTitle')
                
                if not album_name and 'albums' in metadata:
                    # Sometimes albums is a list
                    if isinstance(metadata['albums'], list) and len(metadata['albums']) > 0:
                        album_name = metadata['albums'][0].get('title') or metadata['albums'][0].get('name')
                
                if album_name:
                    album_name = self._clean_album_name(album_name)
                    if album_name not in albums:
                        albums[album_name] = []
                    albums[album_name].append(media_file)
                    self.file_to_album[media_file] = album_name
                    
            except Exception as e:
                logger.debug(f"Failed to parse album from {json_file}: {e}")
                continue
        
        # Merge with existing albums, but JSON metadata takes precedence
        # If a file was assigned to an album from directory structure but now has
        # JSON metadata with a different album, update it
        for album_name, files in albums.items():
            # Update file_to_album mapping for files with JSON metadata (takes precedence)
            for file_path in files:
                self.file_to_album[file_path] = album_name
                # Remove from old album if it was there
                for old_album_name, old_files in list(self.albums.items()):
                    if file_path in old_files and old_album_name != album_name:
                        old_files.remove(file_path)
                        # Clean up empty albums
                        if not old_files:
                            del self.albums[old_album_name]
            
            # Add to new album
            if album_name in self.albums:
                # Merge file lists, avoiding duplicates
                existing_files = set(self.albums[album_name])
                new_files = [f for f in files if f not in existing_files]
                self.albums[album_name].extend(new_files)
            else:
                self.albums[album_name] = files
        
        logger.info(f"Identified {len(albums)} albums from JSON metadata")
        return albums
    
    def _clean_album_name(self, name: str) -> str:
        """
        Clean up album name.
        
        Args:
            name: Raw album name
        
        Returns:
            Cleaned album name
        """
        # Remove common prefixes/suffixes
        name = name.strip()
        
        # Skip common non-album directory names
        skip_names = {'takeout', 'takeout-', 'photos from'}
        if name.lower() in skip_names:
            return ""
        
        # Remove "Google Photos" prefix if present
        if name.startswith("Google Photos"):
            name = name[len("Google Photos"):].strip()
        
        # Remove "Photos from" prefix if present (e.g., "Photos from 2024-01-01")
        if name.lower().startswith("photos from"):
            # Try to extract album name after date
            parts = name.split()
            if len(parts) > 3:  # "Photos from YYYY-MM-DD Album Name"
                name = " ".join(parts[3:])
            else:
                name = ""
        
        # Remove date prefixes if present (e.g., "2024-01-01 Album Name")
        # Keep the actual album name
        
        return name
    
    def get_album_for_file(self, file_path: Path) -> Optional[str]:
        """
        Get album name for a specific file.
        
        Args:
            file_path: Path to media file
        
        Returns:
            Album name or None
        """
        return self.file_to_album.get(file_path)
    
    def get_files_for_album(self, album_name: str) -> List[Path]:
        """
        Get all files in an album.
        
        Args:
            album_name: Name of the album
        
        Returns:
            List of file paths
        """
        return self.albums.get(album_name, [])
    
    def get_all_albums(self) -> Dict[str, List[Path]]:
        """
        Get all albums.
        
        Returns:
            Dictionary mapping album names to file lists
        """
        return self.albums.copy()

