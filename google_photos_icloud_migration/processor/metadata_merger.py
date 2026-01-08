"""
Merge JSON metadata from Google Takeout into media files using ExifTool.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from tqdm import tqdm

from google_photos_icloud_migration.exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataMerger:
    """Handles merging JSON metadata into media files using ExifTool."""
    
    def __init__(self, preserve_dates: bool = True, preserve_gps: bool = True,
                 preserve_descriptions: bool = True):
        """
        Initialize the metadata merger.
        
        Args:
            preserve_dates: Whether to preserve date/time metadata
            preserve_gps: Whether to preserve GPS coordinates
            preserve_descriptions: Whether to preserve descriptions
        """
        self.preserve_dates = preserve_dates
        self.preserve_gps = preserve_gps
        self.preserve_descriptions = preserve_descriptions
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
    
    def parse_json_metadata(self, json_path: Path) -> Dict:
        """
        Parse JSON metadata file from Google Takeout.
        
        Args:
            json_path: Path to JSON file
        
        Returns:
            Dictionary of metadata
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to parse JSON {json_path}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Unexpected error parsing JSON {json_path}: {e}")
            return {}
    
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
    
    def merge_metadata(self, media_file: Path, json_file: Optional[Path]) -> None:
        """
        Merge metadata from JSON file into media file.
        
        Args:
            media_file: Path to media file
            json_file: Path to JSON metadata file (or None)
        
        Returns:
            True if successful, False otherwise
        """
        if json_file is None or not json_file.exists():
            logger.debug(f"No JSON metadata for {media_file.name}")
            return
        
        metadata = self.parse_json_metadata(json_file)
        if not metadata:
            logger.debug(f"No valid metadata found in {json_file}")
            return
        
        args = self.build_exiftool_args(media_file, json_file, metadata)
        
        # Validate file path before subprocess call (prevent command injection)
        from google_photos_icloud_migration.utils.security import validate_subprocess_path
        validate_subprocess_path(media_file)
        
        # Run ExifTool
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.debug(f"Merged metadata for {media_file.name}")
            
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
                          output_dir: Optional[Path] = None) -> Dict[Path, bool]:
        """
        Merge metadata for all media files.
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON files
            output_dir: Optional output directory (if None, modifies files in place)
            
        Returns:
            Dictionary mapping media files to success status
        """
        results = {}
        
        # Initialize video converter if needed (lazy import to avoid requiring ffmpeg if not needed)
        video_converter = None
        
        for media_file, json_file in tqdm(media_json_pairs.items(), 
                                          desc="Merging metadata"):
            # Check if video conversion is needed
            needs_conversion = False
            try:
                from google_photos_icloud_migration.processor.video_converter import VideoConverter, UNSUPPORTED_VIDEO_FORMATS
                if media_file.suffix.lower() in UNSUPPORTED_VIDEO_FORMATS:
                    needs_conversion = True
                    if video_converter is None:
                        video_converter = VideoConverter(output_format='mov', preserve_metadata=True)
            except ImportError:
                # Video converter not available, skip conversion
                pass
            except Exception as e:
                logger.debug(f"Error checking video conversion: {e}")
            
            if output_dir:
                if needs_conversion and video_converter:
                    # Convert video to supported format in output directory
                    converted_file, success = video_converter.convert_video(media_file, output_dir=output_dir)
                    if success and converted_file != media_file:
                        # Use the converted file for metadata merging
                        media_file = converted_file
                        logger.debug(f"Using converted video: {converted_file.name}")
                    elif not success:
                        logger.warning(f"Video conversion failed for {media_file.name}, copying original (will fail upload)")
                        # Copy original - upload will fail with clear error
                    
                    # Copy file to output directory
                    import shutil
                    output_file = output_dir / media_file.name
                    try:
                        shutil.copy2(media_file, output_file)
                        # Set secure file permissions (owner read/write only)
                        try:
                            output_file.chmod(0o600)
                        except (OSError, PermissionError):
                            pass  # Permission setting may fail on some systems
                        media_file = output_file
                    except OSError as e:
                        if e.errno == 28:  # No space left on device
                            logger.error(f"❌ No space left on device. Cannot copy {media_file.name}")
                            results[media_file] = False
                            continue
                        else:
                            raise
                else:
                    # Copy file to output directory first (regular files or conversion disabled)
                    output_file = output_dir / media_file.name
                    import shutil
                    try:
                        shutil.copy2(media_file, output_file)
                        # Set secure file permissions (owner read/write only)
                        try:
                            output_file.chmod(0o600)
                        except (OSError, PermissionError):
                            pass  # Permission setting may fail on some systems
                        media_file = output_file
                    except OSError as e:
                        if e.errno == 28:  # No space left on device
                            logger.error(f"❌ No space left on device. Cannot copy {media_file.name}")
                            logger.error("Please free up disk space and try again.")
                            results[media_file] = False
                            continue
                        else:
                            raise
            
            try:
                self.merge_metadata(media_file, json_file)
                results[media_file] = True
            except (MetadataError, ValueError) as e:
                # ValueError can come from validate_subprocess_path for problematic characters
                logger.warning(f"Skipping file with problematic path: {media_file.name} - {e}")
                results[media_file] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Merged metadata for {successful}/{len(results)} files")
        
        return results

