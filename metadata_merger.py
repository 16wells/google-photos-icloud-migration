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

from exceptions import MetadataError

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
                        args.extend(['-AllDates', exif_date])
            
            # Also check for creationTime
            if 'creationTime' in metadata:
                timestamp = metadata['creationTime'].get('timestamp', '')
                if timestamp:
                    exif_date = self.convert_timestamp(timestamp)
                    if exif_date:
                        args.extend(['-AllDates', exif_date])
        
        # GPS coordinates
        if self.preserve_gps and 'geoData' in metadata:
            geo = metadata['geoData']
            lat = geo.get('latitude')
            lon = geo.get('longitude')
            
            if lat is not None and lon is not None:
                # ExifTool expects format: "lat, lon" or separate tags
                args.extend(['-GPSLatitude', str(lat)])
                args.extend(['-GPSLongitude', str(lon)])
                
                # Set GPS reference
                args.extend(['-GPSLatitudeRef', 'N' if lat >= 0 else 'S'])
                args.extend(['-GPSLongitudeRef', 'E' if lon >= 0 else 'W'])
        
        # Description/Caption
        if self.preserve_descriptions:
            description = metadata.get('description', '')
            if description:
                args.extend(['-Description', description])
                args.extend(['-Caption-Abstract', description])
                args.extend(['-UserComment', description])
        
        # Title
        if 'title' in metadata:
            args.extend(['-Title', metadata['title']])
        
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
        
        # Run ExifTool
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
        
        for media_file, json_file in tqdm(media_json_pairs.items(), 
                                          desc="Merging metadata"):
            if output_dir:
                # Copy file to output directory first
                output_file = output_dir / media_file.name
                import shutil
                shutil.copy2(media_file, output_file)
                media_file = output_file
            
            try:
                self.merge_metadata(media_file, json_file)
                results[media_file] = True
            except MetadataError as e:
                logger.error(f"Metadata merge failed: {e}")
                results[media_file] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Merged metadata for {successful}/{len(results)} files")
        
        return results

