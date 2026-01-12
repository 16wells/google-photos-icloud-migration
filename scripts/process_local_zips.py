#!/usr/bin/env python3
"""
Process Google Takeout zip files from a local directory.
This script processes local zip files: extracts, processes metadata, and uploads to iCloud using PhotoKit sync method (macOS only).
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict
import yaml
import zipfile

# Add parent directory to path to allow imports from package
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
from google_photos_icloud_migration.utils.logging_config import setup_logging
from google_photos_icloud_migration.utils.state_manager import StateManager, ZipProcessingState

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
    cleanup: bool = True,
    state_manager: Optional[StateManager] = None
) -> bool:
    """Process a single zip file: extract, process metadata, upload."""
    logger.info("=" * 60)
    logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_path.name}")
    logger.info("=" * 60)
    
    # Check if zip was already processed
    if state_manager:
        if state_manager.is_zip_complete(zip_path.name):
            logger.info(f"⏭️  Skipping {zip_path.name} - already processed successfully")
            return True
    
    try:
        # Validate zip file (basic validation - check if we can open and list it)
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                # Basic validation: try to list entries
                entry_count = len(test_zip.namelist())
                logger.debug(f"Zip file {zip_path.name} has {entry_count} entries")
                
                # Try full validation, but don't fail hard if it hits file system issues
                try:
                    bad_file = test_zip.testzip()
                    if bad_file:
                        logger.warning(f"Zip file {zip_path.name} has corrupted entries, but will attempt extraction")
                except OSError as e:
                    # File system errors (like [Errno 22]) might be external drive issues
                    # Log warning but proceed with extraction
                    if e.errno == 22:  # Invalid argument
                        logger.warning(
                            f"Zip validation hit file system error for {zip_path.name}: {e}. "
                            f"This may be due to external drive issues. Will attempt extraction anyway."
                        )
                    else:
                        raise
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
            if state_manager:
                state_manager.mark_zip_extracted(zip_path.name, str(extracted_dir))
        except Exception as e:
            logger.error(f"Error extracting {zip_path.name}: {e}")
            if state_manager:
                state_manager.mark_zip_failed(
                    zip_path.name,
                    ZipProcessingState.FAILED_EXTRACTION,
                    str(e)
                )
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
        try:
            processed_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if e.errno == 28:  # No space left on device
                logger.error(f"❌ No space left on device. Cannot create processed directory: {processed_dir}")
                logger.error("Please free up disk space and try again.")
                return False
            else:
                raise
        
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
        
        # Update state
        if state_manager:
            if uploaded_count > 0:
                state_manager.mark_zip_uploaded(zip_path.name)
            elif failed_count > 0:
                state_manager.mark_zip_failed(
                    zip_path.name,
                    ZipProcessingState.FAILED_UPLOAD,
                    f"{failed_count} files failed to upload"
                )
        
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
        description="Process Google Takeout zip files from a local directory"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--takeout-dir",
        type=Path,
        required=True,
        help="Directory containing takeout zip files (e.g., /Volumes/[your external drive]/Takeout or ~/Downloads/Takeout)"
    )
    # PhotoKit sync method is now the only method (macOS only)
    # No --use-sync flag needed as sync is always used
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up extracted files after processing"
    )
    parser.add_argument(
        "--skip-processed",
        action="store_true",
        help="Skip zip files that have already been processed successfully"
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry processing zip files that previously failed"
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
    
    # Setup base directory (needed for state manager)
    base_dir = Path(config['processing']['base_dir'])
    try:
        base_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        if e.errno == 28:  # No space left on device
            logger.error(f"❌ No space left on device. Cannot create base directory: {base_dir}")
            logger.error("Please free up disk space and try again.")
            sys.exit(1)
        else:
            raise
    
    # Setup state manager for tracking processed zips (must be before filtering zip files)
    state_manager = StateManager(base_dir) if (args.skip_processed or args.retry_failed) else None
    
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
    
    # Filter zip files based on flags
    if state_manager:
        if args.skip_processed:
            original_count = len(zip_files)
            zip_files = [z for z in zip_files if not state_manager.is_zip_complete(z.name)]
            skipped_count = original_count - len(zip_files)
            if skipped_count > 0:
                logger.info(f"⏭️  Skipping {skipped_count} already-processed zip file(s)")
        
        if args.retry_failed:
            # Include failed zips in the list
            failed_zips = state_manager.get_zips_by_state(ZipProcessingState.FAILED_UPLOAD)
            failed_zips.extend(state_manager.get_zips_by_state(ZipProcessingState.FAILED_EXTRACTION))
            if failed_zips:
                logger.info(f"🔄 Retrying {len(failed_zips)} previously failed zip file(s)")
                # Add failed zips to the list if not already there
                zip_file_names = {z.name for z in zip_files}
                for failed_zip_name in failed_zips:
                    # Find the actual zip file path
                    for zip_file in find_zip_files(takeout_dir):
                        if zip_file.name == failed_zip_name and zip_file.name not in zip_file_names:
                            zip_files.append(zip_file)
                            zip_file_names.add(zip_file.name)
                            break
    
    logger.info(f"Found {len(zip_files)} zip file(s) to process:")
    for zip_file in zip_files:
        size_mb = zip_file.stat().st_size / (1024 * 1024)
        status = ""
        if state_manager:
            zip_state = state_manager.get_zip_state(zip_file.name)
            if zip_state == ZipProcessingState.UPLOADED.value:
                status = " [already processed]"
            elif zip_state in [ZipProcessingState.FAILED_UPLOAD.value, ZipProcessingState.FAILED_EXTRACTION.value]:
                status = " [retrying]"
        logger.info(f"  - {zip_file.name} ({size_mb:.1f} MB){status}")
    
    # Setup components (base_dir already initialized above)
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
            cleanup=not args.no_cleanup,
            state_manager=state_manager
        ):
            successful += 1
        else:
            failed += 1
            # Mark as failed in state manager
            if state_manager:
                state_manager.mark_zip_failed(
                    zip_file.name,
                    ZipProcessingState.FAILED_UPLOAD,
                    "Processing failed"
                )
        
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

