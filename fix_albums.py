"""
Fix album assignments for already-uploaded photos.

This script re-processes a specific zip file to get correct album mappings,
then finds matching photos in iCloud Photos and moves them to the correct albums.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import yaml

from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser
from icloud_uploader import iCloudPhotosSyncUploader

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def find_photos_in_album(album_name: str, uploader: iCloudPhotosSyncUploader) -> List:
    """
    Find all photos in a specific album using PhotoKit.
    
    Args:
        album_name: Name of the album to search
        uploader: iCloudPhotosSyncUploader instance
    
    Returns:
        List of PHAsset objects in the album
    """
    try:
        # Get the album
        album_collection = uploader._get_or_create_album(album_name)
        if not album_collection:
            logger.warning(f"Album '{album_name}' not found")
            return []
        
        # Fetch assets in the album
        fetch_options = uploader.PHFetchOptions.alloc().init()
        assets = uploader.PHAsset.fetchAssetsInAssetCollection_options_(
            album_collection,
            fetch_options
        )
        
        result = []
        for i in range(assets.count()):
            asset = assets.objectAtIndex_(i)
            result.append(asset)
        
        logger.info(f"Found {len(result)} photos in album '{album_name}'")
        return result
        
    except Exception as e:
        logger.error(f"Error finding photos in album '{album_name}': {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []


def match_photo_to_file(asset, file_path: Path, json_file: Optional[Path] = None) -> bool:
    """
    Try to match a PHAsset to a file by filename and date.
    
    Args:
        asset: PHAsset object
        file_path: Path to the file
        json_file: Optional JSON metadata file
    
    Returns:
        True if likely a match, False otherwise
    """
    try:
        # Get asset filename (if available)
        asset_resources = asset.resources()
        if asset_resources and asset_resources.count() > 0:
            resource = asset_resources.objectAtIndex_(0)
            asset_filename = resource.originalFilename()
            if asset_filename:
                # Compare filenames (case-insensitive)
                if asset_filename.lower() == file_path.name.lower():
                    return True
        
        # Try matching by date if JSON metadata is available
        if json_file and json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Get photo taken time from metadata
                photo_taken_time = None
                if 'photoTakenTime' in metadata:
                    timestamp = metadata['photoTakenTime'].get('timestamp')
                    if timestamp:
                        photo_taken_time = datetime.fromtimestamp(int(timestamp))
                
                # Get asset creation date
                asset_date = asset.creationDate()
                if asset_date and photo_taken_time:
                    # Compare dates (within 1 second tolerance)
                    asset_timestamp = asset_date.timeIntervalSince1970()
                    photo_timestamp = photo_taken_time.timestamp()
                    if abs(asset_timestamp - photo_timestamp) < 1.0:
                        return True
            except Exception as e:
                logger.debug(f"Error matching by date: {e}")
        
        return False
        
    except Exception as e:
        logger.debug(f"Error matching photo: {e}")
        return False


def add_photo_to_album(asset, album_collection, uploader: iCloudPhotosSyncUploader) -> bool:
    """
    Add an existing photo to an album.
    
    Args:
        asset: PHAsset object
        album_collection: PHAssetCollection for the album
        uploader: iCloudPhotosSyncUploader instance
    
    Returns:
        True if successful, False otherwise
    """
    try:
        success_ref = [False]
        error_ref = [None]
        completed = [False]
        
        def perform_changes():
            try:
                album_change_request = uploader.PHAssetCollectionChangeRequest.changeRequestForAssetCollection_(album_collection)
                if album_change_request:
                    album_change_request.addAssets_([asset])
                    success_ref[0] = True
                else:
                    error_ref[0] = "Could not create album change request"
            except Exception as e:
                error_ref[0] = e
        
        def completion_handler(success, error):
            if not success or error:
                error_ref[0] = error if error else "Unknown error"
            completed[0] = True
        
        # Perform changes asynchronously
        uploader.PHPhotoLibrary.sharedPhotoLibrary().performChanges_completionHandler_(
            perform_changes, completion_handler
        )
        
        # Wait for completion
        from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSDate
        import time
        timeout = 30
        start_time = time.time()
        while not completed[0] and (time.time() - start_time) < timeout:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
            time.sleep(0.1)
        
        if error_ref[0]:
            logger.debug(f"Error adding photo to album: {error_ref[0]}")
            return False
        
        if not completed[0]:
            logger.debug("Adding photo to album timed out")
            return False
        
        return success_ref[0]
        
    except Exception as e:
        logger.debug(f"Error adding photo to album: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def fix_albums_for_zip(zip_path: Path, config_path: str, wrong_album_name: str = "takeout"):
    """
    Fix album assignments for photos from a specific zip file.
    
    Args:
        zip_path: Path to the zip file to re-process
        config_path: Path to config.yaml
        wrong_album_name: Name of the album where photos were incorrectly placed
    """
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
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
    
    # Setup uploader (for PhotoKit access)
    uploader = iCloudPhotosSyncUploader()
    
    logger.info(f"Re-processing zip file: {zip_path.name}")
    logger.info(f"Looking for photos in album: '{wrong_album_name}'")
    
    # Extract zip
    logger.info("Extracting zip file...")
    extracted_dir = extractor.extract_zip(zip_path)
    
    # Process metadata
    logger.info("Processing metadata...")
    media_json_pairs = extractor.identify_media_json_pairs(extracted_dir)
    
    processed_dir = base_dir / config['processing'].get('processed_dir', 'processed') / zip_path.stem
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    batch_size = config['processing'].get('batch_size', 100)
    all_files = list(media_json_pairs.keys())
    
    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i + batch_size]
        batch_pairs = {f: media_json_pairs[f] for f in batch}
        logger.info(f"Processing metadata batch {i // batch_size + 1}/{(len(all_files) + batch_size - 1) // batch_size}")
        metadata_merger.merge_all_metadata(batch_pairs, output_dir=processed_dir)
    
    # Parse albums (this will use the fixed parser)
    logger.info("Parsing albums...")
    album_parser.parse_from_directory_structure(extracted_dir)
    album_parser.parse_from_json_metadata(media_json_pairs)
    albums = album_parser.get_all_albums()
    
    logger.info(f"Found {len(albums)} albums")
    for album_name, files in albums.items():
        logger.info(f"  - {album_name}: {len(files)} files")
    
    # Find photos in the wrong album
    logger.info(f"Finding photos in album '{wrong_album_name}'...")
    wrong_album_photos = find_photos_in_album(wrong_album_name, uploader)
    
    if not wrong_album_photos:
        logger.warning(f"No photos found in album '{wrong_album_name}'. They may have been moved or the album doesn't exist.")
        return
    
    logger.info(f"Found {len(wrong_album_photos)} photos in '{wrong_album_name}' album")
    
    # Build file-to-album mapping
    file_to_album = {}
    for album_name, files in albums.items():
        for file_path in files:
            file_to_album[file_path] = album_name
    
    # Match photos to files and organize by target album
    logger.info("Matching photos to files...")
    photos_by_album: Dict[str, List[Tuple]] = {}  # album_name -> [(asset, file_path)]
    matched_count = 0
    
    for asset in wrong_album_photos:
        matched = False
        for file_path, album_name in file_to_album.items():
            json_file = media_json_pairs.get(file_path)
            if match_photo_to_file(asset, file_path, json_file):
                if album_name not in photos_by_album:
                    photos_by_album[album_name] = []
                photos_by_album[album_name].append((asset, file_path))
                matched = True
                matched_count += 1
                break
        
        if not matched:
            logger.debug(f"Could not match photo (filename may differ)")
    
    logger.info(f"Matched {matched_count}/{len(wrong_album_photos)} photos to files")
    
    # Move photos to correct albums
    logger.info("Moving photos to correct albums...")
    total_moved = 0
    
    for album_name, photo_list in photos_by_album.items():
        logger.info(f"Moving {len(photo_list)} photos to album '{album_name}'...")
        
        # Get or create target album
        album_collection = uploader._get_or_create_album(album_name)
        if not album_collection:
            logger.warning(f"Could not get/create album '{album_name}', skipping {len(photo_list)} photos")
            continue
        
        # Add each photo to the album
        for asset, file_path in photo_list:
            if add_photo_to_album(asset, album_collection, uploader):
                total_moved += 1
                logger.debug(f"✓ Moved {file_path.name} to '{album_name}'")
            else:
                logger.warning(f"✗ Failed to move {file_path.name} to '{album_name}'")
    
    logger.info(f"✓ Successfully moved {total_moved} photos to correct albums")
    logger.info(f"\nNote: Photos are now in both '{wrong_album_name}' and their correct albums.")
    logger.info(f"You can manually delete the '{wrong_album_name}' album from Photos app if desired.")


def main():
    parser = argparse.ArgumentParser(
        description="Fix album assignments for already-uploaded photos"
    )
    parser.add_argument(
        '--zip',
        type=str,
        required=True,
        help='Path to the zip file to re-process (e.g., takeout-20251122T203910Z-3-049.zip)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config.yaml file'
    )
    parser.add_argument(
        '--wrong-album',
        type=str,
        default='takeout',
        help='Name of the album where photos were incorrectly placed (default: takeout)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    zip_path = Path(args.zip)
    if not zip_path.exists():
        # Try looking in the zip directory from config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        base_dir = Path(config['processing']['base_dir'])
        zip_dir = base_dir / config['processing'].get('zip_dir', 'zips')
        alt_path = zip_dir / zip_path.name
        if alt_path.exists():
            zip_path = alt_path
            logger.info(f"Found zip file in zip directory: {zip_path}")
        else:
            logger.error(f"Zip file not found: {args.zip}")
            logger.error(f"Also checked: {alt_path}")
            sys.exit(1)
    
    try:
        fix_albums_for_zip(zip_path, str(config_path), args.wrong_album)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

