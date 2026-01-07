#!/usr/bin/env python3
"""
Process Google Takeout zip files from the X10 Pro drive's Takeout folder.
This script processes local zip files: extracts, processes metadata, and uploads to iCloud.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional
import yaml
import zipfile

from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
from google_photos_icloud_migration.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def find_zip_files(takeout_dir: Path) -> List[Path]:
    """Find all takeout zip files in the Takeout directory."""
    zip_files = []
    
    # Look for zip files matching takeout pattern
    for item in takeout_dir.iterdir():
        if item.is_file() and item.suffix.lower() == '.zip':
            # Check if it matches takeout pattern
            name_lower = item.name.lower()
            if 'takeout' in name_lower:
                zip_files.append(item)
    
    return sorted(zip_files)


def process_zip_file(
    zip_path: Path,
    base_dir: Path,
    extractor: Extractor,
    metadata_merger: MetadataMerger,
    album_parser: AlbumParser,
    uploader: iCloudPhotosSyncUploader,
    zip_number: int,
    total_zips: int,
    cleanup: bool = True
) -> bool:
    """Process a single zip file: extract, process metadata, upload."""
    logger.info("=" * 60)
    logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_path.name}")
    logger.info("=" * 60)
    
    try:
        # Validate zip file
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                test_zip.testzip()
        except zipfile.BadZipFile:
            logger.error(f"Invalid or corrupted zip file: {zip_path.name}")
            return False
        except Exception as e:
            logger.error(f"Error validating zip file {zip_path.name}: {e}")
            return False
        
        # Extract the zip file
        logger.info(f"Extracting {zip_path.name}...")
        try:
            extracted_dir = extractor.extract_zip(zip_path)
            logger.info(f"Extracted to: {extracted_dir}")
        except Exception as e:
            logger.error(f"Error extracting {zip_path.name}: {e}")
            return False
        
        # Find the Google Photos subfolder
        google_photos_path = extracted_dir / "Google Photos"
        if not google_photos_path.exists():
            logger.warning(f"No 'Google Photos' folder found in {zip_path.name}")
            # Try to use the extracted directory directly
            source_dir = extracted_dir
        else:
            source_dir = google_photos_path
        
        logger.info(f"Source directory: {source_dir}")
        
        # Identify media files and their JSON metadata
        logger.info("Identifying media files and metadata...")
        media_json_pairs = extractor.identify_media_json_pairs(source_dir)
        
        if not media_json_pairs:
            logger.warning(f"No media files found in {zip_path.name}")
            if cleanup:
                logger.info(f"Cleaning up extracted directory: {extracted_dir}")
                import shutil
                shutil.rmtree(extracted_dir, ignore_errors=True)
            return False
        
        logger.info(f"Found {len(media_json_pairs)} media files")
        
        # Process metadata
        logger.info("Processing metadata...")
        processed_dir = base_dir / "processed" / zip_path.stem
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Use merge_all_metadata which handles copying to output_dir and merging
        results = metadata_merger.merge_all_metadata(media_json_pairs, output_dir=processed_dir)
        processed_files = [file_path for file_path, success in results.items() if success]
        
        logger.info(f"Processed {len(processed_files)} files with metadata")
        
        # Parse albums
        logger.info("Parsing album structure...")
        albums = album_parser.parse_from_directory_structure(source_dir)
        logger.info(f"Found {len(albums)} albums")
        
        # Upload files
        logger.info("Uploading to iCloud Photos...")
        
        # Build file-to-album mapping
        file_to_album = {}
        for processed_file in processed_files:
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
            
            file_to_album[processed_file] = album_name
        
        # Use batch upload for better performance
        if hasattr(uploader, 'upload_files_batch'):
            logger.info(f"Uploading {len(processed_files)} files using batch upload...")
            results = uploader.upload_files_batch(
                processed_files,
                albums=file_to_album,
                verify_after_upload=True
            )
            uploaded_count = sum(1 for success in results.values() if success)
            failed_count = len(results) - uploaded_count
        else:
            # Fallback to individual uploads
            uploaded_count = 0
            failed_count = 0
            for processed_file in processed_files:
                try:
                    album_name = file_to_album.get(processed_file)
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
        
        logger.info(f"✓ Uploaded {uploaded_count} files, {failed_count} failed")
        if failed_count > 0:
            logger.warning(f"⚠️  {failed_count} files failed to upload. Check logs for details.")
        
        # Cleanup extracted files if requested
        if cleanup:
            logger.info(f"Cleaning up extracted directory: {extracted_dir}")
            import shutil
            try:
                shutil.rmtree(extracted_dir, ignore_errors=True)
                logger.info("✓ Cleanup complete")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
        
        return uploaded_count > 0
        
    except Exception as e:
        logger.error(f"Error processing zip {zip_path.name}: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Process Google Takeout zip files from X10 Pro drive"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--takeout-dir",
        default="/Volumes/X10 Pro/Takeout",
        type=Path,
        help="Directory containing takeout zip files (default: /Volumes/X10 Pro/Takeout)"
    )
    parser.add_argument(
        "--use-sync",
        action="store_true",
        help="Use PhotoKit sync method (macOS only, recommended)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up extracted files after processing"
    )
    
    args = parser.parse_args()
    
    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info(f"Looking for config at: {config_path.absolute()}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Setup logging
    logging_config = config.get('logging', {})
    setup_logging(
        level=logging_config.get('level', 'INFO'),
        log_file=logging_config.get('file', 'migration.log')
    )
    
    # Find zip files
    takeout_dir = args.takeout_dir
    if not takeout_dir.exists():
        logger.error(f"Takeout directory not found: {takeout_dir}")
        sys.exit(1)
    
    zip_files = find_zip_files(takeout_dir)
    
    if not zip_files:
        logger.error(f"No takeout zip files found in {takeout_dir}")
        logger.info("Looking for zip files matching 'takeout*.zip' pattern")
        sys.exit(1)
    
    logger.info(f"Found {len(zip_files)} zip files:")
    for zip_file in zip_files:
        size_mb = zip_file.stat().st_size / (1024 * 1024)
        logger.info(f"  - {zip_file.name} ({size_mb:.1f} MB)")
    
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
    
    # Setup uploader
    if args.use_sync:
        logger.info("Using PhotoKit sync method (macOS)")
        uploader = iCloudPhotosSyncUploader()
    else:
        logger.error("API method not fully supported. Please use --use-sync flag (macOS only)")
        sys.exit(1)
    
    # Process each zip file
    successful = 0
    failed = 0
    
    for i, zip_file in enumerate(zip_files, 1):
        if process_zip_file(
            zip_file,
            base_dir,
            extractor,
            metadata_merger,
            album_parser,
            uploader,
            i,
            len(zip_files),
            cleanup=not args.no_cleanup
        ):
            successful += 1
        else:
            failed += 1
        
        # Ask if user wants to continue (optional - can be removed for fully automated)
        if i < len(zip_files):
            logger.info("")
            logger.info(f"Processed {i}/{len(zip_files)} zip files. Continuing...")
            logger.info("")
    
    logger.info("=" * 60)
    logger.info(f"Processing complete: {successful} successful, {failed} failed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

