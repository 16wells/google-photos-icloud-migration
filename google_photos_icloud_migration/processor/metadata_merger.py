"""
Merge JSON metadata from Google Takeout into media files using ExifTool.

This module handles merging metadata from JSON files into media files, with support
for parallel processing and metadata caching for improved performance.
"""
import json
import logging
import subprocess
import os
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Iterator
from datetime import datetime
from tqdm import tqdm
import tempfile

from google_photos_icloud_migration.exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataMerger:
    """
    Handles merging JSON metadata into media files using ExifTool.
    
    This class processes metadata merging with support for:
    - Parallel processing for improved performance
    - Metadata caching to avoid re-parsing JSON files
    - Secure temporary file handling
    - Comprehensive error handling and validation
    """
    
    def __init__(self, preserve_dates: bool = True, preserve_gps: bool = True,
                 preserve_descriptions: bool = True, enable_parallel: bool = True,
                 max_workers: Optional[int] = None, cache_metadata: bool = True,
                 cache_ttl_seconds: int = 3600):
        """
        Initialize the metadata merger.
        
        Args:
            preserve_dates: Whether to preserve date/time metadata from PhotoTakenTimeTimestamp
            preserve_gps: Whether to preserve GPS coordinates from geoData
            preserve_descriptions: Whether to preserve descriptions/titles
            enable_parallel: Whether to enable parallel processing for batch operations
            max_workers: Maximum number of parallel workers (None = auto-detect CPU count)
            cache_metadata: Whether to cache parsed metadata to avoid re-reading JSON files
            cache_ttl_seconds: Time-to-live for metadata cache entries in seconds (default: 1 hour)
        """
        self.preserve_dates = preserve_dates
        self.preserve_gps = preserve_gps
        self.preserve_descriptions = preserve_descriptions
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.cache_metadata = cache_metadata
        
        # Metadata cache: maps JSON file path -> (parsed_data, timestamp)
        self._metadata_cache: Dict[Path, Tuple[Dict, float]] = {}
        self._cache_ttl = cache_ttl_seconds
        
        self._check_exiftool()
    
    def _check_exiftool(self):
        """Check if ExifTool is installed."""
        try:
            result = subprocess.run(
                ['exiftool', '-ver'],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"ExifTool version {result.stdout.strip()} found")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise MetadataError(
                "ExifTool is not installed. Please install it:\n"
                "  macOS: brew install exiftool\n"
                "  Linux: apt-get install libimage-exiftool-perl\n"
                "  Or download from: https://exiftool.org/"
            ) from e
    
    def parse_json_metadata(self, json_path: Path, use_cache: bool = True) -> Dict:
        """
        Parse JSON metadata file from Google Takeout with optional caching.
        
        This method caches parsed metadata to avoid re-reading JSON files on subsequent
        calls, improving performance when processing the same files multiple times.
        
        Args:
            json_path: Path to JSON file
            use_cache: Whether to use cached metadata if available (default: True)
        
        Returns:
            Dictionary of metadata, or empty dict if parsing fails
        
        Note:
            Cache entries expire after cache_ttl_seconds. The cache is automatically
            cleaned up when expired entries are accessed.
        """
        # Check cache first if enabled
        if use_cache and self.cache_metadata:
            if json_path in self._metadata_cache:
                cached_data, cached_time = self._metadata_cache[json_path]
                # Check if cache entry is still valid
                if time.time() - cached_time < self._cache_ttl:
                    logger.debug(f"Using cached metadata for {json_path.name}")
                    return cached_data
                else:
                    # Cache expired, remove it
                    del self._metadata_cache[json_path]
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Cache the parsed metadata if caching is enabled
            if use_cache and self.cache_metadata:
                self._metadata_cache[json_path] = (metadata, time.time())
                # Clean up expired cache entries periodically (every 100 entries)
                if len(self._metadata_cache) % 100 == 0:
                    self._clean_expired_cache()
            
            return metadata
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to parse JSON {json_path}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Unexpected error parsing JSON {json_path}: {e}")
            return {}
    
    def _clean_expired_cache(self) -> None:
        """
        Remove expired entries from the metadata cache.
        
        This method is called periodically to prevent memory leaks from
        accumulating expired cache entries.
        """
        current_time = time.time()
        expired_paths = [
            path for path, (_, cached_time) in self._metadata_cache.items()
            if current_time - cached_time >= self._cache_ttl
        ]
        for path in expired_paths:
            del self._metadata_cache[path]
        
        if expired_paths:
            logger.debug(f"Cleaned up {len(expired_paths)} expired cache entries")
    
    def clear_cache(self) -> None:
        """
        Clear all cached metadata entries.
        
        Useful for freeing memory or forcing re-parsing of all JSON files.
        """
        cache_size = len(self._metadata_cache)
        self._metadata_cache.clear()
        logger.debug(f"Cleared {cache_size} metadata cache entries")
    
    def convert_timestamp(self, timestamp: str) -> Optional[str]:
        """
        Convert Google Photos timestamp to EXIF date format.
        
        Args:
            timestamp: Timestamp string (e.g., "1234567890" or ISO format)
        
        Returns:
            EXIF-formatted date string or None
        """
        try:
            # Try parsing as Unix timestamp (seconds)
            if timestamp.isdigit():
                dt = datetime.fromtimestamp(int(timestamp))
            else:
                # Try parsing as ISO format
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            return dt.strftime("%Y:%m:%d %H:%M:%S")
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to convert timestamp {timestamp}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error converting timestamp {timestamp}: {e}")
            return None
    
    def build_exiftool_args(self, media_file: Path, json_file: Path,
                            metadata: Dict) -> List[str]:
        """
        Build ExifTool command arguments for merging metadata.
        
        Args:
            media_file: Path to media file
            json_file: Path to JSON metadata file
            metadata: Parsed metadata dictionary
        
        Returns:
            List of ExifTool arguments
        """
        args = ['exiftool', '-overwrite_original', '-preserve']
        
        # Date/time metadata
        if self.preserve_dates:
            # PhotoTakenTimeTimestamp is in Unix timestamp format
            if 'photoTakenTime' in metadata:
                timestamp = metadata['photoTakenTime'].get('timestamp', '')
                if timestamp:
                    exif_date = self.convert_timestamp(timestamp)
                    if exif_date:
                        # Use separate date/time tags instead of -AllDates to avoid parsing issues
                        # Format: "YYYY:MM:DD HH:MM:SS" - Use = syntax to ensure date is treated as single value
                        args.extend([f'-DateTimeOriginal={exif_date}'])
                        args.extend([f'-CreateDate={exif_date}'])
                        args.extend([f'-ModifyDate={exif_date}'])
            
            # Also check for creationTime
            if 'creationTime' in metadata:
                timestamp = metadata['creationTime'].get('timestamp', '')
                if timestamp:
                    exif_date = self.convert_timestamp(timestamp)
                    if exif_date:
                        # Use separate date/time tags instead of -AllDates to avoid parsing issues
                        # Format: "YYYY:MM:DD HH:MM:SS" - Use = syntax to ensure date is treated as single value
                        args.extend([f'-DateTimeOriginal={exif_date}'])
                        args.extend([f'-CreateDate={exif_date}'])
                        args.extend([f'-ModifyDate={exif_date}'])
        
        # GPS coordinates
        if self.preserve_gps and 'geoData' in metadata:
            geo = metadata['geoData']
            lat = geo.get('latitude')
            lon = geo.get('longitude')
            
            if lat is not None and lon is not None:
                # ExifTool expects decimal degrees format
                # Use = syntax to ensure values are treated as single arguments
                args.extend([f'-GPSLatitude={lat:.6f}'])
                args.extend([f'-GPSLongitude={lon:.6f}'])
                
                # Set GPS reference (N/S for latitude, E/W for longitude)
                args.extend([f'-GPSLatitudeRef={"N" if lat >= 0 else "S"}'])
                args.extend([f'-GPSLongitudeRef={"E" if lon >= 0 else "W"}'])
        
        # Description/Caption
        if self.preserve_descriptions:
            description = metadata.get('description', '')
            if description:
                # Escape special characters that might cause issues
                description = description.replace('\n', ' ').replace('\r', ' ')
                # Use = syntax to ensure description is treated as single value
                args.extend([f'-Description={description}'])
                args.extend([f'-Caption-Abstract={description}'])
                args.extend([f'-UserComment={description}'])
        
        # Title
        if 'title' in metadata:
            title = metadata['title']
            # Escape special characters
            title = title.replace('\n', ' ').replace('\r', ' ')
            args.extend([f'-Title={title}'])
        
        # Add the media file path
        args.append(str(media_file))
        
        return args
    
    def merge_metadata(self, media_file: Path, json_file: Optional[Path]) -> bool:
        """
        Merge metadata from JSON file into media file using ExifTool.
        
        This method validates paths, parses JSON metadata (with caching), builds
        ExifTool arguments, and executes the merge operation with comprehensive
        error handling.
        
        Args:
            media_file: Path to media file to update
            json_file: Path to JSON metadata file (or None if no metadata available)
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            MetadataError: If metadata merging fails due to ExifTool errors,
                          file I/O issues, or other processing errors
        
        Note:
            Uses secure temporary files if needed and validates all file paths
            to prevent security issues.
        """
        if json_file is None or not json_file.exists():
            logger.debug(f"No JSON metadata for {media_file.name}")
            return False
        
        # Parse metadata (with caching if enabled)
        metadata = self.parse_json_metadata(json_file, use_cache=self.cache_metadata)
        if not metadata:
            logger.debug(f"No valid metadata found in {json_file}")
            return False
        
        args = self.build_exiftool_args(media_file, json_file, metadata)
        
        # Validate file path before subprocess call (prevent command injection)
        from google_photos_icloud_migration.utils.security import validate_subprocess_path
        validate_subprocess_path(media_file)
        
        # Run ExifTool with proper error handling
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # Timeout to prevent hanging on corrupted files
            )
            
            logger.debug(f"Merged metadata for {media_file.name}")
            return True
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"ExifTool timed out for {media_file.name} after 30 seconds")
            raise MetadataError(
                f"Metadata merge timed out for {media_file.name}. "
                f"File may be corrupted or too large."
            ) from e
        except subprocess.CalledProcessError as e:
            logger.error(f"ExifTool failed for {media_file.name}: {e.stderr}")
            raise MetadataError(
                f"Failed to merge metadata for {media_file.name}: ExifTool error - {e.stderr}"
            ) from e
        except (OSError, IOError) as e:
            logger.error(f"File I/O error while merging metadata for {media_file.name}: {e}")
            raise MetadataError(
                f"Failed to access file {media_file.name} during metadata merge: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error merging metadata for {media_file.name}: {e}")
            raise MetadataError(
                f"Unexpected error merging metadata for {media_file.name}: {e}"
            ) from e
    
    def merge_all_metadata(self, media_json_pairs: Dict[Path, Optional[Path]],
                          output_dir: Optional[Path] = None,
                          max_workers: Optional[int] = None) -> Dict[Path, bool]:
        """
        Merge metadata for all media files with optional parallel processing.
        
        This method processes metadata merging for multiple files, with support for:
        - Parallel processing for improved performance (if enabled)
        - Secure temporary file handling for intermediate processing
        - Video conversion for unsupported formats
        - Comprehensive error handling and progress tracking
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON metadata files
            output_dir: Optional output directory for processed files.
                       If None, modifies files in place. If specified, files are
                       copied to this directory before processing.
            max_workers: Maximum number of parallel workers for processing.
                        If None, uses self.max_workers or auto-detects CPU count.
                        Ignored if parallel processing is disabled.
            
        Returns:
            Dictionary mapping media file paths to success status (True/False)
        
        Note:
            When using parallel processing, file order may not be preserved in
            the results dictionary. Use the input dictionary keys for ordering.
        """
        if not media_json_pairs:
            return {}
        
        # Use provided max_workers or fall back to instance setting
        effective_max_workers = max_workers if max_workers is not None else self.max_workers
        
        # Initialize video converter if needed (lazy import to avoid requiring ffmpeg if not needed)
        video_converter = None
        
        # Process with parallel processing if enabled
        if self.enable_parallel and len(media_json_pairs) > 1:
            return self._merge_all_metadata_parallel(
                media_json_pairs, output_dir, effective_max_workers, video_converter
            )
        
        # Sequential processing (fallback when parallel disabled or single file)
        results = {}
        for media_file, json_file in tqdm(media_json_pairs.items(), 
                                          desc="Merging metadata"):
            # Check if video conversion is needed for sequential processing
            if video_converter is None:
                try:
                    from google_photos_icloud_migration.processor.video_converter import VideoConverter, UNSUPPORTED_VIDEO_FORMATS
                    if media_file.suffix.lower() in UNSUPPORTED_VIDEO_FORMATS:
                        video_converter = VideoConverter(output_format='mov', preserve_metadata=True)
                except ImportError:
                    pass
            
            processed_file = self._prepare_file_for_processing(
                media_file, json_file, output_dir, video_converter
            )
            if processed_file is None:
                results[media_file] = False
                continue
            
            try:
                success = self.merge_metadata(processed_file, json_file)
                results[media_file] = success
            except (MetadataError, ValueError) as e:
                # ValueError can come from validate_subprocess_path for problematic characters
                logger.warning(f"Skipping file with problematic path: {media_file.name} - {e}")
                results[media_file] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Merged metadata for {successful}/{len(results)} files")
        
        return results
    
    def _merge_all_metadata_parallel(self, media_json_pairs: Dict[Path, Optional[Path]],
                                     output_dir: Optional[Path],
                                     max_workers: Optional[int],
                                     video_converter) -> Dict[Path, bool]:
        """
        Merge metadata for all files using parallel processing.
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON files
            output_dir: Optional output directory
            max_workers: Maximum number of parallel workers
            video_converter: Optional video converter instance
        
        Returns:
            Dictionary mapping media files to success status
        """
        from google_photos_icloud_migration.utils.parallel import parallel_map_with_results
        
        # Prepare items for parallel processing
        items_to_process = list(media_json_pairs.items())
        
        # Define processing function for parallel execution
        def process_pair(pair: Tuple[Path, Optional[Path]]) -> Tuple[Path, bool]:
            """Process a single media/JSON pair."""
            media_file, json_file = pair
            try:
                processed_file = self._prepare_file_for_processing(
                    media_file, json_file, output_dir, video_converter
                )
                if processed_file is None:
                    return (media_file, False)
                
                success = self.merge_metadata(processed_file, json_file)
                return (media_file, success)
            except (MetadataError, ValueError) as e:
                logger.debug(f"Failed to process {media_file.name}: {e}")
                return (media_file, False)
            except Exception as e:
                logger.warning(f"Unexpected error processing {media_file.name}: {e}")
                return (media_file, False)
        
        # Process in parallel
        logger.info(f"Processing {len(items_to_process)} files in parallel (max_workers={max_workers})")
        parallel_results = parallel_map_with_results(
            process_pair,
            items_to_process,
            max_workers=max_workers,
            use_processes=False  # Use threads for I/O-bound operations
        )
        
        # Convert results back to dictionary
        results = {media_file: success for media_file, success in parallel_results.values()}
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Merged metadata for {successful}/{len(results)} files (parallel processing)")
        
        return results
    
    def _prepare_file_for_processing(self, media_file: Path, json_file: Optional[Path],
                                     output_dir: Optional[Path],
                                     video_converter) -> Optional[Path]:
        """
        Prepare a file for metadata processing with secure temporary file handling.
        
        This method handles:
        - Video conversion for unsupported formats (using secure temp directories)
        - Copying files to output directory with atomic writes
        - Secure file permissions (0600)
        - Proper cleanup of temporary files on errors
        
        Args:
            media_file: Path to source media file to process
            json_file: Path to JSON metadata file (used for logging/debugging)
            output_dir: Optional output directory. If None, returns original file path.
                       If specified, copies/converts file to this directory.
            video_converter: Optional VideoConverter instance for video format conversion.
                           If None and conversion needed, creates a new instance.
        
        Returns:
            Path to prepared file ready for metadata merging, or None if preparation failed
            (e.g., due to disk space issues or conversion failures)
        
        Note:
            Uses tempfile.mkdtemp() for secure temporary directory creation and
            NamedTemporaryFile for atomic file writes to prevent corruption.
        """
        if not output_dir:
            return media_file
        
        # Check if video conversion is needed
        needs_conversion = False
        if video_converter is None:
            try:
                from google_photos_icloud_migration.processor.video_converter import VideoConverter, UNSUPPORTED_VIDEO_FORMATS
                if media_file.suffix.lower() in UNSUPPORTED_VIDEO_FORMATS:
                    needs_conversion = True
                    video_converter = VideoConverter(output_format='mov', preserve_metadata=True)
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Error checking video conversion: {e}")
        
        # Use secure temporary directory for intermediate processing
        temp_dir = None
        try:
            if needs_conversion and video_converter:
                # Use tempfile for secure temporary directory
                temp_dir = tempfile.mkdtemp(prefix='photo_migration_', suffix='_tmp')
                temp_dir_path = Path(temp_dir)
                
                # Convert video to supported format
                converted_file, success = video_converter.convert_video(
                    media_file, output_dir=temp_dir_path
                )
                if success and converted_file != media_file:
                    media_file = converted_file
                    logger.debug(f"Using converted video: {converted_file.name}")
                elif not success:
                    logger.warning(f"Video conversion failed for {media_file.name}")
            
            # Copy file to output directory using secure tempfile for atomic writes
            output_file = output_dir / media_file.name
            import shutil
            
            # Use NamedTemporaryFile for atomic write
            with tempfile.NamedTemporaryFile(
                dir=output_dir,
                prefix=f'.tmp_{media_file.stem}_',
                suffix=media_file.suffix,
                delete=False
            ) as temp_output:
                temp_path = Path(temp_output.name)
                try:
                    shutil.copy2(media_file, temp_path)
                    # Set secure file permissions (owner read/write only)
                    try:
                        temp_path.chmod(0o600)
                    except (OSError, PermissionError):
                        pass
                    # Atomic rename
                    temp_path.replace(output_file)
                    return output_file
                except OSError as e:
                    # Clean up temp file on error
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
                    if e.errno == 28:  # No space left on device
                        logger.error(f"❌ No space left on device. Cannot copy {media_file.name}")
                        return None
                    raise
        except OSError as e:
            if e.errno == 28:  # No space left on device
                logger.error(f"❌ No space left on device. Cannot process {media_file.name}")
                return None
            raise
        finally:
            # Clean up temporary directory if created
            if temp_dir and Path(temp_dir).exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except OSError:
                    pass  # Best effort cleanup

