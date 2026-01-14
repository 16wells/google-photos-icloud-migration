"""
Migration orchestrator.
"""
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
from tqdm import tqdm

from google_photos_icloud_migration.downloader.drive_downloader import DriveDownloader
from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
from google_photos_icloud_migration.config import MigrationConfig
from google_photos_icloud_migration.exceptions import ExtractionError
from google_photos_icloud_migration.utils.state_manager import StateManager, ZipProcessingState
from google_photos_icloud_migration.reporting.migration_statistics import MigrationStatistics
from google_photos_icloud_migration.reporting.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrates the entire migration process."""
    
    def __init__(self, config_path: str):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = MigrationConfig.from_yaml(config_path)
        self.base_dir = self.config.processing.base_path
        
        # Ensure directories exist
        self.config.processing.zip_path.mkdir(parents=True, exist_ok=True)
        self.config.processing.extracted_path.mkdir(parents=True, exist_ok=True)
        self.config.processing.processed_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.downloader = DriveDownloader(
            credentials_file=self.config.google_drive.credentials_file,
            download_dir=self.config.processing.zip_path,
            max_retries=self.config.google_drive.max_retries,
            chunk_size_mb=self.config.google_drive.chunk_size_mb
        )
        
        self.extractor = Extractor(self.base_dir)
        self.metadata_merger = MetadataMerger(self.base_dir)
        self.album_parser = AlbumParser(self.base_dir)
        
        self.uploader = iCloudPhotosSyncUploader(
            upload_tracking_file=self.config.icloud.upload_tracking_file
        )
            
        self.statistics = MigrationStatistics()
        
        # Initialize state manager
        self.state_manager = StateManager(self.base_dir)
        
        # Track failed uploads for retrying
        self.failed_uploads_file = self.base_dir / 'failed_uploads.json'
        
        # Track corrupted zip files
        self.corrupted_zips_file = self.base_dir / 'corrupted_zips.json'
        
        # Flag for re-downloading zips during retry mode
        self._redownload_zips = False
        
        # Configure logging to file as well
        self.log_file_path = self.base_dir / f"migration_{logging.getLogger().name}.log"
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
        
    def _save_failed_uploads(self, failed_files: List[Dict]):
        """Save failed uploads to a JSON file for later retrying."""
        if not failed_files:
            return
            
        current_failed = []
        if self.failed_uploads_file.exists():
            try:
                with open(self.failed_uploads_file, 'r') as f:
                    current_failed = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Add new failures (avoiding duplicates based on file path)
        existing_paths = {item['file_path'] for item in current_failed}
        for item in failed_files:
            if item['file_path'] not in existing_paths:
                current_failed.append(item)
                existing_paths.add(item['file_path'])
        
        with open(self.failed_uploads_file, 'w') as f:
            json.dump(current_failed, f, indent=2)
            
    def _save_corrupted_zips(self, corrupted_files: Dict[str, Dict]):
        """Save corrupted zip file info to a JSON file."""
        if not corrupted_files:
            return
            
        current_corrupted = {}
        if self.corrupted_zips_file.exists():
            try:
                with open(self.corrupted_zips_file, 'r') as f:
                    current_corrupted = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Update with new failures
        current_corrupted.update(corrupted_files)
        
        with open(self.corrupted_zips_file, 'w') as f:
            json.dump(current_corrupted, f, indent=2)

    def _process_failed_uploads(self):
        """Process previously failed uploads."""
        if not self.failed_uploads_file.exists():
            logger.info("No failed uploads file found.")
            return

        with open(self.failed_uploads_file, 'r') as f:
            failed_uploads = json.load(f)

        if not failed_uploads:
            logger.info("No failed uploads to process.")
            return

        logger.info(f"Retrying {len(failed_uploads)} failed uploads...")
        
        # Group by zip filename if re-downloading is requested
        if self._redownload_zips:
            # Get list of corrupted zip IDs if available, or just re-download all relevant zips
            # For now, if _redownload_zips is True, we need to know which zip contained the file.
            # But the failed_uploads.json might not have zip info if it wasn't recorded.
            # Assuming we just retry upload for existing files, unless we implement complex mapping.
            # If the user wants to re-download, they probably should delete the corrupted zip or use the corrupted_zips.json flow.
            # This flag implementation depends on how much info we have.
            pass

        successful_retries = []
        new_failures = []

        for item in tqdm(failed_uploads, desc="Retrying uploads"):
            file_path = Path(item['file_path'])
            album_name = item.get('album')
            
            if not file_path.exists():
                logger.warning(f"File not found for retry: {file_path}")
                # If we are in re-download mode and we can map this file to a zip, we would try to fetch it.
                # For simplicity in this refactor, we just log warning.
                new_failures.append(item)
                continue

            try:
                # Basic media type check
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.heic', '.gif', '.tiff', '.bmp']:
                     # For retry, we assume metadata is already merged if the file exists in processed_dir
                     # If it's raw extracted file, we might need merging. 
                     # But typically failed_uploads.json points to files ready for upload.
                     pass

                success, error = self.uploader.upload_file(file_path, album_name)
                if success:
                    successful_retries.append(item)
                    self.statistics.record_upload(file_path.name, file_path.stat().st_size)
                else:
                    new_failures.append(item)
                    self.statistics.record_upload(file_path.name, success=False, error=error)
            except Exception as e:
                logger.error(f"Error retrying {file_path}: {e}")
                new_failures.append(item)
                self.statistics.record_upload(file_path.name, success=False, error=str(e))

        logger.info(f"Retry complete: {len(successful_retries)} successful, {len(new_failures)} failed.")
        
        # Update failed uploads file
        if new_failures:
            with open(self.failed_uploads_file, 'w') as f:
                json.dump(new_failures, f, indent=2)
        else:
            if self.failed_uploads_file.exists():
                self.failed_uploads_file.unlink()

    def run(self, retry_failed: bool = False):
        """
        Run the migration process.
        
        Args:
            retry_failed: If True, only retry previously failed uploads
        """
        self.statistics.start()
        
        try:
            if retry_failed:
                self._process_failed_uploads()
                self._generate_final_report(0, 0) # Basic report
                return

            logger.info("Starting migration process...")
            
            # Phase 1: Download
            logger.info("Phase 1: Checking for Google Takeout zip files...")
            self.downloader.authenticate()
            
            # List all zip files
            zip_files = self.downloader.list_zip_files(
                folder_id=self.config.google_drive.folder_id,
                pattern="*.zip"
            )
            
            self.statistics.zip_files_total = len(zip_files)
            
            processed_zips = []
            failed_zips = []
            
            # Process each zip file
            for i, zip_info in enumerate(zip_files):
                zip_name = zip_info['name']
                zip_id = zip_info['id']
                file_size_bytes = int(zip_info.get('size', 0))
                
                logger.info(f"\nProcessing zip file {i+1}/{len(zip_files)}: {zip_name}")
                
                # Check state
                if self.state_manager.is_zip_processed(zip_id):
                    logger.info(f"Zip {zip_name} already fully processed. Skipping.")
                    self.statistics.record_zip_processed(True)
                    processed_zips.append(zip_info)
                    continue
                
                try:
                    # Download
                    download_path = self.config.processing.zip_path / zip_name
                    
                    # Check if already downloaded
                    if download_path.exists():
                        # Verify size matches approximately (if available)
                        if file_size_bytes > 0:
                            local_size = download_path.stat().st_size
                            if local_size == file_size_bytes:
                                logger.info(f"Zip file already downloaded: {zip_name}")
                                self.statistics.record_zip_download(zip_name, local_size, success=True)
                            else:
                                logger.info(f"Zip file partial/mismatch, re-downloading: {zip_name}")
                                download_path = self.downloader.download_file(
                                    zip_id, zip_name, self.config.processing.zip_path, file_size_bytes
                                )
                                self.statistics.record_zip_download(zip_name, download_path.stat().st_size, success=True)
                        else:
                            logger.info(f"Zip file already downloaded (size unknown): {zip_name}")
                            self.statistics.record_zip_download(zip_name, download_path.stat().st_size, success=True)
                    else:
                        download_path = self.downloader.download_file(
                            zip_id, zip_name, self.config.processing.zip_path, file_size_bytes
                        )
                        self.statistics.record_zip_download(zip_name, download_path.stat().st_size, success=True)
                    
                    # Update state
                    self.state_manager.update_zip_state(zip_id, zip_name, ZipProcessingState.DOWNLOADED)
                    
                    # Phase 2: Extract
                    logger.info(f"Extracting {zip_name}...")
                    extract_path = self.config.processing.extracted_path / Path(zip_name).stem
                    try:
                        self.extractor.extract_zip(download_path, extract_path)
                        self.statistics.record_zip_extraction(zip_name, success=True)
                        self.state_manager.update_zip_state(zip_id, zip_name, ZipProcessingState.EXTRACTED)
                    except ExtractionError as e:
                        logger.error(f"Extraction failed for {zip_name}: {e}")
                        self.statistics.record_zip_extraction(zip_name, success=False, error=str(e))
                        # Mark as corrupted if it's a zip error
                        self.statistics.record_zip_corrupted(zip_name, str(e))
                        self._save_corrupted_zips({
                            zip_id: {
                                'file_name': zip_name,
                                'error': str(e),
                                'file_size': file_size_bytes,
                                'local_size_mb': download_path.stat().st_size / (1024*1024) if download_path.exists() else 0
                            }
                        })
                        failed_zips.append(zip_info)
                        continue

                    # Phase 3: Process & Merge Metadata
                    logger.info("Processing media files...")
                    media_files = self.extractor.find_media_files_list(extract_path)
                    json_pairs = self.extractor.identify_media_json_pairs(extract_path)
                    
                    self.statistics.record_media_files(len(media_files), len([j for j in json_pairs.values() if j]))
                    
                    processed_media_files = []
                    metadata_failures = []
                    
                    for media_file in tqdm(media_files, desc="Merging metadata"):
                        json_file = json_pairs.get(media_file)
                        try:
                            processed_file = self.metadata_merger.process_file(
                                media_file, json_file, self.config.processing.processed_path
                            )
                            if processed_file:
                                processed_media_files.append(processed_file)
                                self.statistics.record_metadata_processing(success=True)
                            else:
                                self.statistics.record_metadata_processing(success=False, error="Skipped/Failed", file_name=media_file.name)
                        except Exception as e:
                            logger.error(f"Error merging metadata for {media_file}: {e}")
                            self.statistics.record_metadata_processing(success=False, error=str(e), file_name=media_file.name)
                            metadata_failures.append(media_file)

                    self.state_manager.update_zip_state(zip_id, zip_name, ZipProcessingState.METADATA_PROCESSED)
                    
                    # Phase 4: Identify Albums
                    logger.info("Identifying albums...")
                    # We look at the extracted structure to guess albums
                    # Note: process_file typically moves files to processed_dir/AlbumName/File if preserve_albums is True
                    # So we should scan the PROCESSED directory's structure relative to base
                    
                    # But actually `get_album_structure` was designed for the raw structure.
                    # Since we moved files to `processed_path`, let's check structure there for the files we just processed.
                    # Or better, we know where we put them.
                    
                    # Let's use the album_parser on the extracted structure to know what SHOULD be the albums,
                    # but we upload from processed paths.
                    # Actually, `MetadataMerger` puts files in `processed_path / album_name` if configured.
                    
                    # Let's map processed files to albums based on their new parent directory name
                    files_to_upload = []
                    for p_file in processed_media_files:
                        # Assuming processed_path/Album/File or processed_path/File
                        rel_path = p_file.relative_to(self.config.processing.processed_path)
                        if len(rel_path.parts) > 1:
                            album = rel_path.parts[0]
                        else:
                            album = None # "All Photos"
                        files_to_upload.append((p_file, album))
                        
                    # Phase 5: Upload
                    logger.info(f"Uploading {len(files_to_upload)} files to iCloud Photos...")
                    
                    uploaded_count = 0
                    failed_upload_batch = []
                    
                    for file_path, album in tqdm(files_to_upload, desc="Uploading"):
                        try:
                            success, error = self.uploader.upload_file(file_path, album)
                            if success:
                                uploaded_count += 1
                                self.statistics.record_upload(file_path.name, file_path.stat().st_size)
                            else:
                                failed_upload_batch.append({
                                    'file_path': str(file_path),
                                    'album': album,
                                    'error': error,
                                    'original_zip': zip_name
                                })
                                self.statistics.record_upload(file_path.name, success=False, error=error)
                        except Exception as e:
                            logger.error(f"Upload exception for {file_path}: {e}")
                            failed_upload_batch.append({
                                    'file_path': str(file_path),
                                    'album': album,
                                    'error': str(e),
                                    'original_zip': zip_name
                                })
                            self.statistics.record_upload(file_path.name, success=False, error=str(e))
                            
                    if failed_upload_batch:
                        self._save_failed_uploads(failed_upload_batch)
                        
                    self.state_manager.update_zip_state(zip_id, zip_name, ZipProcessingState.UPLOADED)
                    self.state_manager.update_zip_state(zip_id, zip_name, ZipProcessingState.COMPLETED)
                    self.statistics.record_zip_processed(True)
                    processed_zips.append(zip_info)
                    
                    # Cleanup
                    if self.config.processing.cleanup_after_upload:
                         # Remove extracted files for this zip
                         import shutil
                         if extract_path.exists():
                             shutil.rmtree(extract_path)
                         # Also clean up processed files for this batch? 
                         # We dumped them into a common processed folder. It might be hard to distinguish if we mix zips.
                         # But we process one zip at a time. So processed_path might accumulate or be cleaned.
                         # If we assume we process sequentially and clean up, we can clean, but we must be careful not to delete files from other zips if parallel (not parallel here).
                         pass

                except Exception as e:
                    logger.error(f"Failed to process zip {zip_name}: {e}", exc_info=True)
                    self.statistics.record_zip_processed(False)
                    failed_zips.append(zip_info)
                    continue
            
            # Final Report
            self._generate_final_report(len(processed_zips), len(zip_files))

        except Exception as e:
            logger.error(f"Global migration error: {e}", exc_info=True)
            self.statistics.finish()
            raise
            
    def _generate_final_report(self, successful: int = 0, total_zips: int = 0):
        """Generate and save the final migration report."""
        self.statistics.finish()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("GENERATING MIGRATION REPORT")
        logger.info("=" * 80)
        
        report_generator = ReportGenerator(
            statistics=self.statistics,
            base_dir=self.base_dir,
            log_file=self.log_file_path,
            failed_uploads_file=self.failed_uploads_file,
            corrupted_zips_file=self.corrupted_zips_file
        )
        
        report_path = report_generator.save_report()
        logger.info(f"✓ Migration report saved to: {report_path.absolute()}")
        
        # Save statistics
        stats_path = self.base_dir / 'migration_statistics.json'
        self.statistics.save(stats_path)
        logger.info(f"✓ Statistics saved to: {stats_path.absolute()}")
