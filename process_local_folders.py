#!/usr/bin/env python3
"""
Process already-extracted Google Takeout folders from the Downloads folder.
This script bypasses the zip download/extraction step and processes folders directly.

NOTE: For most use cases, use process_local_zips.py instead, which:
- Processes zip files directly (extracts automatically)
- Has state tracking (--skip-processed, --retry-failed)
- Is more feature-complete

Use this script only if you have already-extracted folders and want to skip extraction.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional
import yaml

from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
from google_photos_icloud_migration.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def find_takeout_folders(downloads_dir: Path) -> List[Path]:
    """Find all takeout folders in the Downloads directory."""
    takeout_folders = []
    
    # Look for folders starting with "Takeout" (case-insensitive)
    for item in downloads_dir.iterdir():
        if item.is_dir() and item.name.lower().startswith('takeout'):
            takeout_folders.append(item)
    
    return sorted(takeout_folders)


def process_takeout_folder(
    folder_path: Path,
    base_dir: Path,
    extractor: Extractor,
    metadata_merger: MetadataMerger,
    album_parser: AlbumParser,
    uploader: iCloudPhotosSyncUploader,
    folder_number: int,
    total_folders: int
) -> bool:
    """Process a single takeout folder."""
    logger.info("=" * 60)
    logger.info(f"Processing folder {folder_number}/{total_folders}: {folder_path.name}")
    logger.info("=" * 60)
    
    try:
        # Find the Google Photos subfolder
        google_photos_path = folder_path / "Google Photos"
        if not google_photos_path.exists():
            logger.warning(f"No 'Google Photos' folder found in {folder_path.name}")
            # Try to use the folder directly
            source_dir = folder_path
        else:
            source_dir = google_photos_path
        
        logger.info(f"Source directory: {source_dir}")
        
        # Identify media files and their JSON metadata
        logger.info("Identifying media files and metadata...")
        media_json_pairs = extractor.identify_media_json_pairs(source_dir)
        
        if not media_json_pairs:
            logger.warning(f"No media files found in {folder_path.name}")
            return False
        
        logger.info(f"Found {len(media_json_pairs)} media files")
        
        # Process metadata
        logger.info("Processing metadata...")
        processed_dir = base_dir / "processed" / folder_path.name
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        processed_files = []
        for media_file, json_file in media_json_pairs.items():
            try:
                processed_file = metadata_merger.merge_metadata(media_file, json_file, processed_dir)
                if processed_file:
                    processed_files.append(processed_file)
            except Exception as e:
                logger.error(f"Error processing {media_file}: {e}")
                # Continue with next file
                continue
        
        logger.info(f"Processed {len(processed_files)} files with metadata")
        
        # Parse albums
        logger.info("Parsing album structure...")
        albums = album_parser.parse_from_directory_structure(source_dir)
        logger.info(f"Found {len(albums)} albums")
        
        # Upload files
        logger.info("Uploading to iCloud Photos...")
        uploaded_count = 0
        failed_count = 0
        
        for processed_file in processed_files:
            try:
                # Determine album name from original path
                album_name = None
                if albums:
                    # Find which album this file belongs to
                    original_path = None
                    for orig_file, json_file in media_json_pairs.items():
                        # Try to match processed file to original
                        if processed_file.name.startswith(orig_file.stem):
                            original_path = orig_file
                            break
                    
                    if original_path:
                        # Find album from path
                        rel_path = original_path.relative_to(source_dir)
                        if len(rel_path.parts) > 1:
                            album_name = rel_path.parts[0]
                
                # Upload the file
                result = uploader.upload_file(
                    processed_file,
                    album_name=album_name
                )
                
                if result:
                    uploaded_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to upload {processed_file.name}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error uploading {processed_file.name}: {e}")
        
        logger.info(f"Uploaded {uploaded_count} files, {failed_count} failed")
        
        return uploaded_count > 0
        
    except Exception as e:
        logger.error(f"Error processing folder {folder_path.name}: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Process already-extracted Google Takeout folders"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--downloads-dir",
        default=Path.home() / "Downloads",
        type=Path,
        help="Directory containing takeout folders (default: ~/Downloads)"
    )
    # PhotoKit sync method is now the only method (macOS only)
    # No --use-sync flag needed as sync is always used
    
    args = parser.parse_args()
    
    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Setup logging
    logging_config = config.get('logging', {})
    setup_logging(
        level=logging_config.get('level', 'INFO'),
        log_file=logging_config.get('file', 'migration.log')
    )
    
    # Find takeout folders
    downloads_dir = args.downloads_dir
    if not downloads_dir.exists():
        logger.error(f"Downloads directory not found: {downloads_dir}")
        sys.exit(1)
    
    takeout_folders = find_takeout_folders(downloads_dir)
    
    if not takeout_folders:
        logger.error(f"No takeout folders found in {downloads_dir}")
        logger.info("Looking for folders starting with 'Takeout' (case-insensitive)")
        sys.exit(1)
    
    logger.info(f"Found {len(takeout_folders)} takeout folders:")
    for folder in takeout_folders:
        logger.info(f"  - {folder.name}")
    
    # Setup components
    base_dir = Path(config['processing']['base_dir'])
    base_dir.mkdir(parents=True, exist_ok=True)
    
    extractor = Extractor(base_dir)
    metadata_config = config['metadata']
    metadata_merger = MetadataMerger(
        preserve_dates=metadata_config['preserve_dates'],
        preserve_gps=metadata_config['preserve_gps'],
        preserve_descriptions=metadata_config['preserve_descriptions']
    )
    album_parser = AlbumParser()
    
    # Setup uploader - always use PhotoKit sync method (macOS only)
    logger.info("Using PhotoKit sync method (macOS)")
    uploader = iCloudPhotosSyncUploader()
    
    # Process each folder
    successful = 0
    failed = 0
    
    for i, folder in enumerate(takeout_folders, 1):
        if process_takeout_folder(
            folder,
            base_dir,
            extractor,
            metadata_merger,
            album_parser,
            uploader,
            i,
            len(takeout_folders)
        ):
            successful += 1
        else:
            failed += 1
    
    logger.info("=" * 60)
    logger.info(f"Processing complete: {successful} successful, {failed} failed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

