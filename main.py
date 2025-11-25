"""
Main orchestration script for Google Photos to iCloud Photos migration.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from tqdm import tqdm

from drive_downloader import DriveDownloader
from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser
from icloud_uploader import iCloudUploader, iCloudPhotosSyncUploader

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrates the entire migration process."""
    
    def __init__(self, config_path: str):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Path to configuration YAML file
        """
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.base_dir = Path(self.config['processing']['base_dir'])
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize downloader
        drive_config = self.config['google_drive']
        self.downloader = DriveDownloader(drive_config['credentials_file'])
        
        # Initialize extractor
        self.extractor = Extractor(self.base_dir)
        
        # Initialize metadata merger
        metadata_config = self.config['metadata']
        self.metadata_merger = MetadataMerger(
            preserve_dates=metadata_config['preserve_dates'],
            preserve_gps=metadata_config['preserve_gps'],
            preserve_descriptions=metadata_config['preserve_descriptions']
        )
        
        # Initialize album parser
        self.album_parser = AlbumParser()
        
        # Initialize iCloud uploader (will be set up later)
        self.icloud_uploader = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Set up logging configuration."""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'migration.log')
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def download_zip_files(self) -> List[Path]:
        """
        Download all zip files from Google Drive.
        
        Returns:
            List of downloaded zip file paths
        """
        logger.info("=" * 60)
        logger.info("Phase 1: Downloading zip files from Google Drive")
        logger.info("=" * 60)
        
        drive_config = self.config['google_drive']
        zip_dir = self.base_dir / self.config['processing']['zip_dir']
        
        zip_files = self.downloader.download_all_zips(
            destination_dir=zip_dir,
            folder_id=drive_config.get('folder_id') or None,
            pattern=drive_config.get('zip_file_pattern') or None
        )
        
        logger.info(f"Downloaded {len(zip_files)} zip files")
        return zip_files
    
    def extract_files(self, zip_files: List[Path]) -> List[Path]:
        """
        Extract all zip files.
        
        Args:
            zip_files: List of zip file paths
        
        Returns:
            List of extracted directory paths
        """
        logger.info("=" * 60)
        logger.info("Phase 2: Extracting zip files")
        logger.info("=" * 60)
        
        extracted_dirs = self.extractor.extract_all_zips(zip_files)
        
        logger.info(f"Extracted {len(extracted_dirs)} zip files")
        return extracted_dirs
    
    def process_metadata(self, extracted_dirs: List[Path]) -> Dict[Path, Optional[Path]]:
        """
        Process metadata for all extracted files.
        
        Args:
            extracted_dirs: List of extracted directory paths
        
        Returns:
            Dictionary mapping media files to JSON metadata files
        """
        logger.info("=" * 60)
        logger.info("Phase 3: Processing metadata")
        logger.info("=" * 60)
        
        # Collect all media/JSON pairs
        all_pairs = {}
        
        for extracted_dir in extracted_dirs:
            pairs = self.extractor.identify_media_json_pairs(extracted_dir)
            all_pairs.update(pairs)
        
        logger.info(f"Found {len(all_pairs)} media files to process")
        
        # Merge metadata
        processed_dir = self.base_dir / self.config['processing']['processed_dir']
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Process in batches
        batch_size = self.config['processing']['batch_size']
        all_files = list(all_pairs.keys())
        
        for i in range(0, len(all_files), batch_size):
            batch = all_files[i:i + batch_size]
            batch_pairs = {f: all_pairs[f] for f in batch}
            
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(all_files) + batch_size - 1) // batch_size}")
            self.metadata_merger.merge_all_metadata(batch_pairs, output_dir=processed_dir)
        
        # Update pairs to point to processed files
        processed_pairs = {}
        for media_file, json_file in all_pairs.items():
            processed_file = processed_dir / media_file.name
            if processed_file.exists():
                processed_pairs[processed_file] = json_file
            else:
                # Fallback to original if processing failed
                processed_pairs[media_file] = json_file
        
        return processed_pairs
    
    def parse_albums(self, media_json_pairs: Dict[Path, Optional[Path]],
                    extracted_dirs: List[Path]) -> Dict[str, List[Path]]:
        """
        Parse album structures from extracted files.
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON files
            extracted_dirs: List of extracted directory paths
        
        Returns:
            Dictionary mapping album names to file lists
        """
        logger.info("=" * 60)
        logger.info("Phase 4: Parsing album structures")
        logger.info("=" * 60)
        
        # Parse from directory structure
        for extracted_dir in extracted_dirs:
            self.album_parser.parse_from_directory_structure(extracted_dir)
        
        # Parse from JSON metadata
        self.album_parser.parse_from_json_metadata(media_json_pairs)
        
        albums = self.album_parser.get_all_albums()
        logger.info(f"Identified {len(albums)} albums")
        
        return albums
    
    def setup_icloud_uploader(self, use_sync_method: bool = False):
        """
        Set up iCloud uploader.
        
        Args:
            use_sync_method: If True, use Photos library sync method
        """
        icloud_config = self.config['icloud']
        
        if use_sync_method:
            self.icloud_uploader = iCloudPhotosSyncUploader()
        else:
            self.icloud_uploader = iCloudUploader(
                apple_id=icloud_config['apple_id'],
                password=icloud_config.get('password', ''),
                trusted_device_id=icloud_config.get('trusted_device_id')
            )
    
    def upload_to_icloud(self, media_json_pairs: Dict[Path, Optional[Path]],
                        albums: Dict[str, List[Path]]) -> Dict[Path, bool]:
        """
        Upload processed files to iCloud Photos.
        
        Args:
            media_json_pairs: Dictionary mapping media files to JSON files
            albums: Dictionary mapping album names to file lists
        
        Returns:
            Dictionary mapping file paths to upload success status
        """
        logger.info("=" * 60)
        logger.info("Phase 5: Uploading to iCloud Photos")
        logger.info("=" * 60)
        
        if self.icloud_uploader is None:
            raise RuntimeError("iCloud uploader not initialized. Call setup_icloud_uploader() first.")
        
        # Build file-to-album mapping
        file_to_album = {}
        for album_name, files in albums.items():
            for file_path in files:
                file_to_album[file_path] = album_name
        
        # Upload files
        all_files = list(media_json_pairs.keys())
        
        if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
            results = self.icloud_uploader.upload_files_batch(
                all_files,
                albums=file_to_album
            )
        else:
            # Group by album for regular uploader
            results = {}
            for album_name, files in albums.items():
                logger.info(f"Uploading album: {album_name} ({len(files)} files)")
                album_results = self.icloud_uploader.upload_photos_batch(
                    files,
                    album_name=album_name
                )
                results.update(album_results)
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Uploaded {successful}/{len(results)} files to iCloud Photos")
        
        return results
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.config['processing'].get('cleanup_after_upload', False):
            logger.info("=" * 60)
            logger.info("Phase 6: Cleanup")
            logger.info("=" * 60)
            
            extracted_dir = self.base_dir / self.config['processing']['extracted_dir']
            if extracted_dir.exists():
                import shutil
                logger.info(f"Removing extracted files: {extracted_dir}")
                shutil.rmtree(extracted_dir)
    
    def process_single_zip(self, zip_path: Path, zip_number: int, total_zips: int, 
                           use_sync_method: bool = False) -> bool:
        """
        Process a single zip file: extract, process metadata, upload, cleanup.
        
        Args:
            zip_path: Path to zip file
            zip_number: Current zip number (for logging)
            total_zips: Total number of zip files
            use_sync_method: Whether to use Photos library sync method
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_path.name}")
            logger.info("=" * 60)
            
            # Extract this zip file
            extracted_dir = self.extractor.extract_zip(zip_path)
            
            # Process metadata for this zip
            media_json_pairs = self.extractor.identify_media_json_pairs(extracted_dir)
            logger.info(f"Found {len(media_json_pairs)} media files in this zip")
            
            if not media_json_pairs:
                logger.warning(f"No media files found in {zip_path.name}, skipping")
                return True
            
            # Merge metadata
            processed_dir = self.base_dir / self.config['processing']['processed_dir']
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            # Process metadata in batches
            batch_size = self.config['processing']['batch_size']
            all_files = list(media_json_pairs.keys())
            
            for i in range(0, len(all_files), batch_size):
                batch = all_files[i:i + batch_size]
                batch_pairs = {f: media_json_pairs[f] for f in batch}
                logger.info(f"Processing metadata batch {i // batch_size + 1}/{(len(all_files) + batch_size - 1) // batch_size}")
                self.metadata_merger.merge_all_metadata(batch_pairs, output_dir=processed_dir)
            
            # Parse albums for this zip
            parser = AlbumParser()
            parser.parse_from_directory_structure(extracted_dir)
            parser.parse_from_json_metadata(media_json_pairs)
            albums = parser.get_all_albums()
            
            # Upload files from this zip
            if self.icloud_uploader is None:
                self.setup_icloud_uploader(use_sync_method=use_sync_method)
            
            # Build file-to-album mapping
            file_to_album = {}
            for album_name, files in albums.items():
                for file_path in files:
                    file_to_album[file_path] = album_name
            
            # Get processed files
            processed_files = []
            for media_file in media_json_pairs.keys():
                processed_file = processed_dir / media_file.name
                if processed_file.exists():
                    processed_files.append(processed_file)
                else:
                    processed_files.append(media_file)
            
            # Upload
            if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
                upload_results = self.icloud_uploader.upload_files_batch(
                    processed_files,
                    albums=file_to_album
                )
            else:
                # Group by album
                upload_results = {}
                for album_name, files in albums.items():
                    # Map to processed files
                    processed_album_files = [f for f in processed_files 
                                           if file_to_album.get(f, '') == album_name]
                    if processed_album_files:
                        logger.info(f"Uploading album: {album_name} ({len(processed_album_files)} files)")
                        album_results = self.icloud_uploader.upload_photos_batch(
                            processed_album_files,
                            album_name=album_name
                        )
                        upload_results.update(album_results)
            
            successful = sum(1 for v in upload_results.values() if v)
            logger.info(f"Uploaded {successful}/{len(upload_results)} files from {zip_path.name}")
            
            # Cleanup extracted files for this zip (save disk space)
            import shutil
            if extracted_dir.exists():
                logger.info(f"Cleaning up extracted files for {zip_path.name}")
                shutil.rmtree(extracted_dir)
            
            logger.info(f"✓ Completed processing {zip_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process {zip_path.name}: {e}", exc_info=True)
            return False
    
    def run(self, use_sync_method: bool = False):
        """Run the complete migration process."""
        try:
            # Phase 1: Download all zip files (but don't extract yet)
            logger.info("=" * 60)
            logger.info("Phase 1: Downloading zip files from Google Drive")
            logger.info("=" * 60)
            
            drive_config = self.config['google_drive']
            zip_dir = self.base_dir / self.config['processing']['zip_dir']
            
            zip_files = self.downloader.download_all_zips(
                destination_dir=zip_dir,
                folder_id=drive_config.get('folder_id') or None,
                pattern=drive_config.get('zip_file_pattern') or None
            )
            
            if not zip_files:
                logger.error("No zip files found. Exiting.")
                return
            
            logger.info(f"Downloaded {len(zip_files)} zip files")
            logger.info("")
            logger.info("Now processing each zip file individually:")
            logger.info("  - Extract → Process metadata → Upload → Cleanup")
            logger.info("")
            
            # Setup iCloud uploader once (before processing zips)
            self.setup_icloud_uploader(use_sync_method=use_sync_method)
            
            # Process each zip file one at a time
            successful = 0
            failed = 0
            
            for i, zip_file in enumerate(zip_files, 1):
                if self.process_single_zip(zip_file, i, len(zip_files), use_sync_method):
                    successful += 1
                else:
                    failed += 1
                    logger.warning(f"Skipping remaining processing for {zip_file.name}")
            
            # Final cleanup
            if self.config['processing'].get('cleanup_after_upload', False):
                logger.info("=" * 60)
                logger.info("Final cleanup")
                logger.info("=" * 60)
                processed_dir = self.base_dir / self.config['processing']['processed_dir']
                if processed_dir.exists():
                    import shutil
                    logger.info(f"Removing processed files: {processed_dir}")
                    shutil.rmtree(processed_dir)
            
            logger.info("=" * 60)
            logger.info(f"Migration completed!")
            logger.info(f"  Successful: {successful}/{len(zip_files)} zip files")
            if failed > 0:
                logger.info(f"  Failed: {failed}/{len(zip_files)} zip files")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate Google Photos to iCloud Photos'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--use-sync',
        action='store_true',
        help='Use Photos library sync method instead of API upload'
    )
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator(args.config)
    orchestrator.run(use_sync_method=args.use_sync)


if __name__ == '__main__':
    main()

