# Workaround for Python < 3.10 compatibility with dependencies that use importlib.metadata.packages_distributions
# This attribute was added in Python 3.10, so we need to handle it gracefully on older Python versions
import sys
if sys.version_info < (3, 10):
    try:
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            # Add a dummy function to prevent AttributeError
            def _packages_distributions():
                """Compatibility shim for Python < 3.10"""
                return {}
            importlib.metadata.packages_distributions = _packages_distributions
    except (ImportError, AttributeError):
        pass

import argparse
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
from tqdm import tqdm

# Add parent directory to path to allow imports from package
import sys
from pathlib import Path
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google_photos_icloud_migration.downloader.drive_downloader import DriveDownloader
from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader

from scripts.migration_statistics import MigrationStatistics
from scripts.report_generator import ReportGenerator
from google_photos_icloud_migration.exceptions import ExtractionError
from google_photos_icloud_migration.utils.state_manager import StateManager, ZipProcessingState

logger = logging.getLogger(__name__)


class MigrationStoppedException(Exception):
    """Exception raised when user chooses to stop migration."""
    pass


class MigrationOrchestrator:
    """Orchestrates the entire migration process."""
    
    def __init__(self, config_path: str):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = config_path
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
        
        # Initialize metadata merger with parallel processing support
        metadata_config = self.config['metadata']
        processing_config = self.config.get('processing', {})
        enable_parallel = processing_config.get('enable_parallel_processing', True)
        max_workers = processing_config.get('max_workers')
        
        self.metadata_merger = MetadataMerger(
            preserve_dates=metadata_config['preserve_dates'],
            preserve_gps=metadata_config['preserve_gps'],
            preserve_descriptions=metadata_config['preserve_descriptions'],
            enable_parallel=enable_parallel,
            max_workers=max_workers,
            cache_metadata=True  # Enable metadata caching for performance
        )
        
        # Initialize album parser
        self.album_parser = AlbumParser()
        
        # Initialize iCloud uploader (will be set up later)
        self.icloud_uploader = None
        
        # Initialize state manager for tracking completed zips
        self.state_manager = StateManager(self.base_dir)
        
        # Failed uploads tracking
        self.failed_uploads_file = self.base_dir / 'failed_uploads.json'
        
        # Corrupted zip files tracking
        self.corrupted_zips_file = self.base_dir / 'corrupted_zips.json'
        
        # Verification failure handling
        self.ignore_all_verification_failures = False
        
        # Continue prompt handling
        self._skip_continue_prompts = False
        self._restart_requested = False
        
        # Statistics tracking
        self.statistics = MigrationStatistics()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Ensure processing section exists with defaults
        if 'processing' not in config:
            config['processing'] = {}
        
        processing_defaults = {
            'base_dir': '/tmp/google-photos-migration',
            'zip_dir': 'zips',
            'extracted_dir': 'extracted',
            'processed_dir': 'processed',
            'batch_size': 100,
            'cleanup_after_upload': True,
            'max_disk_space_gb': None  # None = unlimited
        }
        
        for key, default_value in processing_defaults.items():
            if key not in config['processing']:
                config['processing'][key] = default_value

        # Ensure metadata section exists with defaults
        if 'metadata' not in config:
            config['metadata'] = {}
            
        metadata_defaults = {
            'preserve_dates': True,
            'preserve_gps': True,
            'preserve_descriptions': True,
            'preserve_albums': True
        }
        
        for key, default_value in metadata_defaults.items():
            if key not in config['metadata']:
                config['metadata'][key] = default_value
        
        return config
    
    def _setup_logging(self):
        """Set up logging configuration."""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'migration.log')
        # Store log file path for report generation
        self.log_file_path = Path(log_file)
        
        class SafeFileHandler(logging.FileHandler):
            """File handler that gracefully handles disk space errors."""
            def emit(self, record):
                try:
                    super().emit(record)
                except OSError as e:
                    if e.errno == 28:  # No space left on device
                        # Silently skip logging to file if disk is full
                        pass
                    else:
                        raise
        
        handlers = [logging.StreamHandler(sys.stdout)]
        
        # Try to add file handler, but don't fail if disk is full
        try:
            file_handler = SafeFileHandler(log_file)
            handlers.append(file_handler)
        except (OSError, IOError) as e:
            # If we can't create log file (e.g., no disk space), just use console
            print(f"Warning: Could not create log file '{log_file}': {e}", file=sys.stderr)
            print("Continuing with console logging only.", file=sys.stderr)
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
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
        
        self.statistics.zip_files_total = len(zip_files)
        self.statistics.zip_files_downloaded = len(zip_files)
        
        logger.info(f"Downloaded {len(zip_files)} zip files")
        return zip_files
    
    def extract_files(self, zip_files: List[Path]) -> List[Path]:
        """
        Extract all zip files from the provided list.
        
        This method extracts zip files sequentially, tracking progress and handling
        errors gracefully. Failed extractions are logged but don't stop the entire process.
        
        Args:
            zip_files: List of zip file paths to extract
        
        Returns:
            List of extracted directory paths (only successful extractions)
        
        Note:
            Uses the extractor's extract_all_zips_list() method which collects
            generator results into a list. For memory-efficient processing of many
            large zips, consider using extract_all_zips() directly.
        """
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
        
        # Use list method for backward compatibility
        extracted_dirs = self.extractor.extract_all_zips_list(zip_files)
        
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
        
        # Track statistics
        total_media = len(all_pairs)
        with_metadata = sum(1 for v in all_pairs.values() if v is not None)
        self.statistics.record_media_files(total_media, with_metadata)
        
        logger.info(f"Found {len(all_pairs)} media files to process")
        
        # Merge metadata
        processed_dir = self.base_dir / self.config['processing']['processed_dir']
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Process in batches (parallel processing is handled inside merge_all_metadata)
        batch_size = self.config['processing']['batch_size']
        all_files = list(all_pairs.keys())
        processing_config = self.config.get('processing', {})
        max_workers = processing_config.get('max_workers')
        
        for i in range(0, len(all_files), batch_size):
            batch = all_files[i:i + batch_size]
            batch_pairs = {f: all_pairs[f] for f in batch}
            
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(all_files) + batch_size - 1) // batch_size} "
                       f"({len(batch_pairs)} files)")
            # merge_all_metadata handles parallel processing internally if enabled
            self.metadata_merger.merge_all_metadata(
                batch_pairs, 
                output_dir=processed_dir,
                max_workers=max_workers
            )
        
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
        self.statistics.record_albums(len(albums))
        logger.info(f"Identified {len(albums)} albums")
        
        return albums
    
    def setup_icloud_uploader(self):
        """
        Set up iCloud uploader using PhotoKit sync method (macOS only).
        
        This method uses Apple's PhotoKit framework to save photos directly
        to the Photos library, which then automatically syncs to iCloud Photos.
        """
        icloud_config = self.config['icloud']
        
        # Get photos library path from config if specified
        photos_library_path = icloud_config.get('photos_library_path')
        if photos_library_path:
            photos_library_path = Path(photos_library_path).expanduser()
        
        # Always use PhotoKit sync method (macOS only)
        # PhotoKit handles concurrency internally
        self.icloud_uploader = iCloudPhotosSyncUploader(
            photos_library_path=photos_library_path
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
        
        # Create verification failure callback
        def verification_failure_callback(failed_file_path: Path):
            """Callback for handling verification failures."""
            self.statistics.record_verification_failure(failed_file_path.name, "Verification failed")
            action = self._handle_verification_failure(failed_file_path)
            if action == 'stop':
                raise MigrationStoppedException(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
        
        # Upload files
        all_files = list(media_json_pairs.keys())
        
        # Always use PhotoKit sync method upload
        results = self.icloud_uploader.upload_files_batch(
            all_files,
            albums=file_to_album,
            verify_after_upload=True,
            on_verification_failure=verification_failure_callback
        )
        
        successful = sum(1 for v in results.values() if v)
        failed_count = len(results) - successful
        
        # Track statistics
        for file_path, success in results.items():
            file_size = file_path.stat().st_size if file_path.exists() else 0
            self.statistics.record_upload(
                file_path.name,
                size=file_size,
                success=success,
                error=None if success else "Upload failed"
            )
        
        logger.info(f"Uploaded {successful}/{len(results)} files to iCloud Photos")
        
        # Save failed uploads for retry
        if failed_count > 0:
            failed_files = [str(path) for path, success in results.items() if not success]
            self._save_failed_uploads(failed_files, albums)
            logger.warning("=" * 60)
            logger.warning(f"⚠️  {failed_count} files failed to upload")
            logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
            logger.warning("You can retry failed uploads using: --retry-failed")
            logger.warning("=" * 60)
        
        return results
    
    def _ask_continue_after_zip(self, processed_count: int, total_zips: int) -> bool:
        """
        Ask user if they want to continue processing after a zip file is completed.
        
        Args:
            processed_count: Number of zip files processed so far
            total_zips: Total number of zip files to process
        
        Returns:
            True if user wants to continue, False if they want to stop
        """
        # Check if we're in a non-interactive environment
        import sys
        is_interactive = sys.stdin.isatty()
        
        if not is_interactive:
            # In non-interactive mode, continue automatically
            logger.debug("Non-interactive mode detected, continuing automatically")
            return True
        
        # Check if this is the last zip file
        if processed_count >= total_zips:
            logger.info("All zip files processed!")
            return True
        
        remaining = total_zips - processed_count
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Completed processing zip {processed_count}/{total_zips}")
        logger.info(f"Remaining: {remaining} zip file(s)")
        logger.info("=" * 60)
        logger.info("")
        logger.info("What would you like to do?")
        logger.info("  (C) Continue - Process the next zip file")
        logger.info("  (A) Continue All - Process all remaining zip files without asking")
        logger.info("  (S) Stop - Stop processing and exit")
        logger.info("  (R) Restart from scratch - Redownload all zip files and reprocess everything")
        logger.info("")
        
        while True:
            try:
                choice = input("Enter your choice (C/A/S/R): ").strip().upper()
                if choice == 'C':
                    logger.info("Continuing to next zip file...")
                    return True
                elif choice == 'A':
                    logger.info("Continuing to process all remaining zip files without further prompts...")
                    # Set a flag to skip future prompts
                    self._skip_continue_prompts = True
                    return True
                elif choice == 'S':
                    logger.info("Stopping migration as requested.")
                    return False
                elif choice == 'R':
                    logger.info("Restarting from scratch as requested...")
                    self._restart_requested = True
                    return True  # Return True to continue, but restart will be handled in run()
                else:
                    logger.warning("Invalid choice. Please enter C (Continue), A (Continue All), S (Stop), or R (Restart from scratch).")
            except (EOFError, KeyboardInterrupt) as e:
                logger.warning("")
                logger.warning("Input interrupted. Stopping migration.")
                return False
    
    def _handle_verification_failure(self, file_path: Path) -> str:
        """
        Handle verification failure by prompting the user.
        
        Args:
            file_path: Path to the file that failed verification
        
        Returns:
            'stop', 'continue', or 'ignore_all'
        """
        if self.ignore_all_verification_failures:
            return 'ignore_all'
        
        logger.warning("=" * 60)
        logger.warning(f"⚠️  Upload verification failed for: {file_path.name}")
        logger.warning("=" * 60)
        logger.warning("The file may not have been successfully uploaded to iCloud.")
        logger.warning("")
        logger.warning("What would you like to do?")
        logger.warning("  (A) Stop - Stop processing and exit")
        logger.warning("  (B) Continue - Continue processing remaining files")
        logger.warning("  (I) Ignore all - Ignore all future verification failures and continue")
        logger.warning("")
        
        while True:
            choice = input("Enter your choice (A/B/I): ").strip().upper()
            if choice == 'A':
                logger.info("Stopping migration as requested.")
                return 'stop'
            elif choice == 'B':
                logger.info("Continuing with remaining files.")
                return 'continue'
            elif choice == 'I':
                logger.info("Ignoring all future verification failures.")
                self.ignore_all_verification_failures = True
                return 'ignore_all'
            else:
                logger.warning("Invalid choice. Please enter A, B, or I.")
    
    def _save_failed_uploads(self, failed_files: List[str], albums: Dict[Path, str]):
        """
        Save failed uploads to a JSON file for later retry.
        
        Args:
            failed_files: List of file paths (as strings) that failed to upload
            albums: Dictionary mapping file paths to album names
        """
        # Load existing failed uploads
        existing_failed = {}
        if self.failed_uploads_file.exists():
            try:
                with open(self.failed_uploads_file, 'r') as f:
                    existing_failed = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read existing failed uploads file: {e}")
                existing_failed = {}
        
        # Add new failed files
        for file_path_str in failed_files:
            file_path = Path(file_path_str)
            album_name = albums.get(file_path, '')
            existing_failed[file_path_str] = {
                'file': file_path_str,
                'album': album_name,
                'retry_count': existing_failed.get(file_path_str, {}).get('retry_count', 0)
            }
        
        # Save updated failed uploads
        try:
            with open(self.failed_uploads_file, 'w') as f:
                json.dump(existing_failed, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save failed uploads file: {e}")
    
    def _save_corrupted_zip(self, file_info: dict, zip_path: Path, error_message: str):
        """
        Save corrupted zip file info for later re-download.
        
        Args:
            file_info: Google Drive file metadata dictionary with 'id', 'name', 'size'
            zip_path: Local path to the corrupted zip file
            error_message: Error message describing the corruption
        """
        # Load existing corrupted zips
        existing_corrupted = {}
        if self.corrupted_zips_file.exists():
            try:
                with open(self.corrupted_zips_file, 'r') as f:
                    existing_corrupted = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read existing corrupted zips file: {e}")
                existing_corrupted = {}
        
        # Add this corrupted zip
        file_id = file_info.get('id', '')
        file_name = file_info.get('name', zip_path.name)
        file_size = file_info.get('size', '0')
        
        existing_corrupted[file_id] = {
            'file_id': file_id,
            'file_name': file_name,
            'file_size': file_size,
            'local_path': str(zip_path),
            'error': error_message,
            'detected_at': str(Path(zip_path).stat().st_mtime) if zip_path.exists() else None,
            'local_size_mb': zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else None
        }
        
        # Save updated corrupted zips
        try:
            with open(self.corrupted_zips_file, 'w') as f:
                json.dump(existing_corrupted, f, indent=2)
            logger.warning(f"⚠️  Corrupted zip file saved to: {self.corrupted_zips_file}")
            logger.warning(f"   File: {file_name}")
            logger.warning(f"   You can re-download it later from Google Drive")
        except IOError as e:
            logger.error(f"Could not save corrupted zips file: {e}")
    
    def retry_failed_uploads(self, redownload_zips: bool = False) -> Dict[Path, bool]:
        """
        Retry uploading files that previously failed using PhotoKit sync method.
        
        Args:
            redownload_zips: If True, re-download and re-process zip files that contain failed uploads
            
        Returns:
            Dictionary mapping file paths to upload success status
        """
        if not self.failed_uploads_file.exists():
            logger.info("No failed uploads file found. Nothing to retry.")
            return {}
        
        logger.info("=" * 60)
        logger.info("Retrying failed uploads")
        logger.info("=" * 60)
        
        # Load failed uploads
        try:
            with open(self.failed_uploads_file, 'r') as f:
                failed_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Could not read failed uploads file: {e}")
            return {}
        
        if not failed_data:
            logger.info("No failed uploads to retry.")
            return {}
        
        logger.info(f"Found {len(failed_data)} files in failed uploads list")
        logger.info("")
        logger.info("This will:")
        logger.info("  1. Check if processed files still exist (with path corrections)")
        logger.info("  2. Look for missing files in extracted directories (using state file)")
        logger.info("  3. Re-process files found in extracted directories")
        if redownload_zips:
            logger.info("  4. Re-download and re-process zip files containing failed uploads")
        logger.info("  5. Retry uploading all available files")
        logger.info("")
        
        # Setup uploader if needed
        if self.icloud_uploader is None:
            self.setup_icloud_uploader()
        
        # Group files by album and handle missing files
        files_by_album: Dict[str, List[Path]] = {}
        missing_files = []
        reprocess_needed = []
        
        extracted_dir = self.base_dir / self.config['processing']['extracted_dir']
        processed_dir = self.base_dir / self.config['processing']['processed_dir']
        
        # Helper function to correct path if it points to wrong base directory
        def correct_path(original_path: Path) -> Path:
            """Correct path if it points to wrong base directory."""
            original_str = str(original_path)
            # If path points to /tmp/ but base_dir is different, correct it
            if '/tmp/google-photos-migration' in original_str:
                # Replace /tmp/google-photos-migration with actual base_dir
                corrected_str = original_str.replace('/tmp/google-photos-migration', str(self.base_dir))
                return Path(corrected_str)
            return original_path
        
        # Helper function to find file in extracted directories using state file
        def find_in_extracted_dirs(file_name: str) -> Optional[Path]:
            """Find file in extracted directories using state file paths."""
            # First check current extracted_dir structure
            if extracted_dir.exists():
                for extracted_subdir in extracted_dir.iterdir():
                    if extracted_subdir.is_dir():
                        potential_file = extracted_subdir / file_name
                        if potential_file.exists():
                            return potential_file
                        # Check subdirectories
                        for subdir in extracted_subdir.rglob('*'):
                            if subdir.is_file() and subdir.name == file_name:
                                return subdir
            
            # Also check state file for extracted_dir paths
            for zip_name, zip_data in self.state_manager._zip_state.items():
                extracted_dir_path = zip_data.get('extracted_dir')
                if extracted_dir_path:
                    extracted_path = Path(extracted_dir_path)
                    # Correct path if needed
                    if not extracted_path.exists() and '/tmp/google-photos-migration' in str(extracted_path):
                        corrected_path = Path(str(extracted_path).replace('/tmp/google-photos-migration', str(self.base_dir)))
                        if corrected_path.exists():
                            extracted_path = corrected_path
                    
                    if extracted_path.exists():
                        potential_file = extracted_path / file_name
                        if potential_file.exists():
                            return potential_file
                        # Check subdirectories
                        for subdir in extracted_path.rglob('*'):
                            if subdir.is_file() and subdir.name == file_name:
                                return subdir
            return None
        
        for file_data in failed_data.values():
            original_file_path = Path(file_data['file'])
            album_name = file_data.get('album', '')
            
            # Try corrected path first
            file_path = correct_path(original_file_path)
            
            if file_path.exists():
                # File exists, can retry directly
                if album_name not in files_by_album:
                    files_by_album[album_name] = []
                files_by_album[album_name].append(file_path)
            else:
                # File doesn't exist - try to find it in extracted directory
                file_name = file_path.name
                missing_files.append((file_path, file_name, album_name))
                
                # Search for the file in extracted directories (using state file)
                found_in_extracted = find_in_extracted_dirs(file_name)
                
                if found_in_extracted:
                    # Found in extracted - need to re-process
                    logger.info(f"Found {file_name} in extracted directory, will re-process")
                    reprocess_needed.append((found_in_extracted, file_name, album_name))
                else:
                    logger.debug(f"File no longer exists and not found in extracted: {file_path.name}")
        
        # Re-process files that were found in extracted directory
        if reprocess_needed:
            logger.info(f"Re-processing {len(reprocess_needed)} files from extracted directory...")
            processed_files = []
            
            for extracted_file, file_name, album_name in reprocess_needed:
                try:
                    # Find corresponding JSON file
                    json_file = None
                    json_candidates = [
                        extracted_file.with_suffix('.json'),
                        extracted_file.parent / (extracted_file.stem + '.json'),
                    ]
                    for candidate in json_candidates:
                        if candidate.exists():
                            json_file = candidate
                            break
                    
                    # Process the file (merge metadata)
                    processed_file = processed_dir / file_name
                    if json_file and json_file.exists():
                        # Copy file to processed directory first
                        import shutil
                        processed_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(extracted_file, processed_file)
                        
                        # Merge metadata
                        self.metadata_merger.merge_metadata(processed_file, json_file)
                        logger.debug(f"Re-processed {file_name}")
                    else:
                        # No JSON, just copy the file
                        import shutil
                        processed_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(extracted_file, processed_file)
                        logger.debug(f"Copied {file_name} (no JSON metadata)")
                    
                    if processed_file.exists():
                        processed_files.append((processed_file, album_name))
                except Exception as e:
                    logger.error(f"Error re-processing {file_name}: {e}")
            
            # Add re-processed files to upload queue
            for processed_file, album_name in processed_files:
                if album_name not in files_by_album:
                    files_by_album[album_name] = []
                files_by_album[album_name].append(processed_file)
            
            logger.info(f"✓ Re-processed {len(processed_files)} files, ready for upload")
        
        # If redownload_zips is True and we have missing files, identify which zips need re-downloading
        if redownload_zips and missing_files:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Re-downloading zip files containing failed uploads")
            logger.info("=" * 60)
            
            # Identify which zips contain the failed files
            # We need to map file names to zip files - this is approximate since we don't track this
            # But we can re-download all zips that are in "converted" state (they have failed uploads)
            zips_to_redownload = []
            for zip_name, zip_data in self.state_manager._zip_state.items():
                zip_state = zip_data.get('state')
                if zip_state == 'converted':  # Converted but may have failed uploads
                    zips_to_redownload.append(zip_name)
            
            if zips_to_redownload:
                logger.info(f"Found {len(zips_to_redownload)} zip files to re-download and re-process")
                logger.info("This will re-extract and re-process files, then retry uploads")
                logger.info("")
                
                # Re-download and re-process these zips
                drive_config = self.config['google_drive']
                zip_dir = self.base_dir / self.config['processing']['zip_dir']
                
                # List zip files from Drive
                zip_file_list = self.downloader.list_zip_files(
                    folder_id=drive_config.get('folder_id') or None,
                    pattern=drive_config.get('zip_file_pattern') or None
                )
                
                # Create mapping from zip name to file_info
                zip_info_by_name = {info['name']: info for info in zip_file_list}
                
                for zip_name in zips_to_redownload:
                    if zip_name in zip_info_by_name:
                        zip_info = zip_info_by_name[zip_name]
                        zip_path = zip_dir / zip_name
                        
                        logger.info(f"Re-downloading {zip_name}...")
                        try:
                            # Convert size to int if available (Google Drive API returns it as string)
                            file_size = None
                            if 'size' in zip_info:
                                try:
                                    file_size = int(zip_info['size'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # Download the zip
                            downloaded_path = self.downloader.download_file(
                                zip_info['id'],
                                zip_name,
                                zip_dir,
                                file_size=file_size
                            )
                            
                            if downloaded_path.exists():
                                logger.info(f"✓ Downloaded {zip_name}")
                                
                                # Re-process the zip (extract, convert, upload)
                                zip_number = zips_to_redownload.index(zip_name) + 1
                                total_zips = len(zips_to_redownload)
                                
                                # Reset zip state so it gets fully re-processed
                                self.state_manager.set_zip_state(zip_name, ZipProcessingState.PENDING, {})
                                
                                # Process the zip
                                if self.process_single_zip(downloaded_path, zip_number, total_zips, zip_info):
                                    logger.info(f"✓ Successfully re-processed {zip_name}")
                                else:
                                    logger.warning(f"⚠️  Re-processing failed for {zip_name}")
                            else:
                                logger.error(f"❌ Download failed for {zip_name}")
                        except Exception as e:
                            logger.error(f"❌ Error re-downloading {zip_name}: {e}")
                    else:
                        logger.warning(f"⚠️  Zip file {zip_name} not found in Google Drive listing")
                
                # After re-downloading, re-run retry to pick up newly processed files
                logger.info("")
                logger.info("Re-running retry after re-download...")
                return self.retry_failed_uploads(redownload_zips=False)
        
        if not files_by_album:
            logger.warning("No files available to retry (all files are missing and not found in extracted directory)")
            logger.warning(f"  Missing files: {len(missing_files)}")
            logger.warning(f"  Found in extracted: {len(reprocess_needed)}")
            if not redownload_zips:
                logger.warning("")
                logger.warning("💡 Tip: Run with --redownload-zips to re-download and re-process zip files")
                logger.warning("   containing failed uploads")
            return {}
        
        # Upload files
        results = {}
        file_to_album = {}
        for album_name, files in files_by_album.items():
            for file_path in files:
                file_to_album[file_path] = album_name
        
        # Create verification failure callback
        def verification_failure_callback(failed_file_path: Path):
            """Callback for handling verification failures."""
            self.statistics.record_verification_failure(failed_file_path.name, "Verification failed")
            action = self._handle_verification_failure(failed_file_path)
            if action == 'stop':
                raise MigrationStoppedException(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
        
        all_files = [f for files in files_by_album.values() for f in files]
        
        # Always use PhotoKit sync method upload
        results = self.icloud_uploader.upload_files_batch(
            all_files,
            albums=file_to_album,
            verify_after_upload=True,
            on_verification_failure=verification_failure_callback
        )
        
        # Update failed uploads file (remove successful ones)
        # Match successful files by both original path and processed path
        successful_files = {str(path) for path, success in results.items() if success}
        successful_file_names = {Path(path).name for path, success in results.items() if success}
        
        remaining_failed = {}
        for k, v in failed_data.items():
            file_path_str = v.get('file', '')
            file_name = Path(file_path_str).name
            
            # Check if this file was successfully uploaded (by path or by name)
            if file_path_str not in successful_files and file_name not in successful_file_names:
                remaining_failed[k] = v
        
        # Increment retry count for still-failed files
        for file_path_str in remaining_failed:
            remaining_failed[file_path_str]['retry_count'] = \
                remaining_failed[file_path_str].get('retry_count', 0) + 1
        
        # Save updated failed uploads
        try:
            with open(self.failed_uploads_file, 'w') as f:
                json.dump(remaining_failed, f, indent=2)
        except IOError as e:
            logger.error(f"Could not update failed uploads file: {e}")
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Retried: {successful}/{len(results)} files succeeded")
        
        if len(remaining_failed) > 0:
            logger.warning(f"⚠️  {len(remaining_failed)} files still failed after retry")
            logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
        else:
            logger.info("✓ All failed uploads have been successfully retried!")
            # Optionally remove the failed uploads file if all succeeded
            if successful == len(results):
                self.failed_uploads_file.unlink()
                logger.info("Removed failed uploads file (all uploads succeeded)")
        
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
    
    def _process_upload_only(self, zip_name: str, zip_number: int, total_zips: int) -> bool:
        """
        Process upload-only for a zip that's already been converted using PhotoKit sync method.
        Used when zip file doesn't exist but processed files do.
        
        Args:
            zip_name: Name of the zip file
            zip_number: Current zip number (for logging)
            total_zips: Total number of zip files
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info(f"Processing upload-only for {zip_name} (zip file not needed)")
            logger.info("=" * 60)
            
            # Find processed files
            processed_dir = self.base_dir / self.config['processing']['processed_dir']
            from google_photos_icloud_migration.processor.extractor import MEDIA_EXTENSIONS
            processed_files = [
                Path(f) for f in processed_dir.glob("*")
                if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
            ]
            
            if not processed_files:
                logger.error(f"❌ No processed files found for {zip_name}")
                return False
            
            logger.info(f"Found {len(processed_files)} processed files to upload")
            
            # Setup uploader if needed
            if self.icloud_uploader is None:
                self.setup_icloud_uploader()
            
            # Upload without album info (we don't have extraction data)
            file_to_album = {}
            logger.warning(f"⚠️  Album information not available for {zip_name} (skipped extraction)")
            logger.warning(f"   Files will be uploaded without album assignments")
            
            # Create verification failure callback
            def verification_failure_callback(failed_file_path: Path):
                """Callback for handling verification failures."""
                self.statistics.record_verification_failure(failed_file_path.name, "Verification failed")
                action = self._handle_verification_failure(failed_file_path)
                if action == 'stop':
                    raise RuntimeError(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
            
            # Create upload success callback for incremental cleanup
            def upload_success_callback(file_path: Path):
                """Delete processed file immediately after successful upload to free space."""
                if file_path.exists() and str(file_path).startswith(str(processed_dir)):
                    try:
                        file_path.unlink()
                        logger.debug(f"✓ Deleted {file_path.name} after successful upload")
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path.name} after upload: {e}")
            
            # Upload
            # Always use PhotoKit sync method upload
            upload_results = self.icloud_uploader.upload_files_batch(
                processed_files,
                albums=file_to_album,
                verify_after_upload=True,
                on_verification_failure=verification_failure_callback,
                on_upload_success=upload_success_callback
            )
            
            successful = sum(1 for v in upload_results.values() if v)
            failed_count = len(upload_results) - successful
            
            # Track statistics
            for file_path, success in upload_results.items():
                file_size = file_path.stat().st_size if file_path.exists() else 0
                self.statistics.record_upload(
                    file_path.name,
                    size=file_size,
                    success=success,
                    error=None if success else "Upload failed"
                )
            
            logger.info(f"Uploaded {successful}/{len(upload_results)} files from {zip_name}")
            
            # Mark as uploaded in state (save immediately, even if some files failed)
            # Only mark as complete if all files uploaded successfully
            if failed_count == 0:
                logger.info(f"💾 Marking {zip_name} as uploaded (complete) in state")
                self.state_manager.mark_zip_uploaded(zip_name)
            else:
                logger.warning(f"⚠️  {zip_name} has {failed_count} failed uploads - not marking as complete")
            
            # Save failed uploads for retry
            if failed_count > 0:
                failed_files = [str(path) for path, success in upload_results.items() if not success]
                self._save_failed_uploads(failed_files, file_to_album)
                logger.warning(f"⚠️  {failed_count} files from {zip_name} failed to upload")
            
            # Cleanup successfully uploaded processed files
            cleaned_count = 0
            for file_path, success in upload_results.items():
                if success and file_path.exists() and str(file_path).startswith(str(processed_dir)):
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete processed file {file_path.name}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"✓ Cleaned up {cleaned_count} successfully uploaded processed files")
            
            logger.info(f"✓ Completed upload-only processing for {zip_name}")
            self.statistics.record_zip_processed(success=True)
            return True
            
        except Exception as e:
            logger.error(f"Failed to process upload-only for {zip_name}: {e}", exc_info=True)
            self.statistics.record_zip_processed(success=False)
            return False
    
    def process_single_zip(self, zip_path: Path, zip_number: int, total_zips: int, 
                           file_info: Optional[dict] = None) -> bool:
        """
        Process a single zip file using PhotoKit sync method: extract, process metadata, upload, cleanup.
        
        Args:
            zip_path: Path to zip file
            zip_number: Current zip number (for logging)
            total_zips: Total number of zip files
            file_info: Optional Google Drive file metadata (for tracking corrupted files)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("=" * 60)
            logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_path.name}")
            logger.info("=" * 60)
            
            # Check current state and skip completed steps
            zip_state = self.state_manager.get_zip_state(zip_path.name)
            zip_state_data = self.state_manager._zip_state.get(zip_path.name, {})
            
            # Check if already converted - if so, skip extraction and conversion, go straight to upload
            if self.state_manager.is_zip_converted(zip_path.name):
                logger.info(f"⏭️  {zip_path.name} is already converted (state: {zip_state})")
                logger.info(f"   Skipping extraction and conversion steps, proceeding directly to upload")
                
                # Try to find processed files
                processed_dir = self.base_dir / self.config['processing']['processed_dir']
                processed_files = list(processed_dir.glob("*"))
                
                if not processed_files:
                    logger.warning(f"⚠️  No processed files found for {zip_path.name}")
                    logger.warning(f"   Will need to re-extract and re-convert")
                    # Fall through to extraction
                    extracted_dir = None
                else:
                    logger.info(f"   Found {len(processed_files)} processed files, proceeding to upload")
                    # Skip extraction and conversion, go straight to upload
                    extracted_dir = None  # Not needed for upload
                    skip_to_upload = True
            elif self.state_manager.is_zip_extracted(zip_path.name):
                logger.info(f"⏭️  {zip_path.name} already extracted (state: {zip_state}), skipping extraction step")
                # Try to find the extracted directory from state or default location
                extracted_dir_path = zip_state_data.get('extracted_dir')
                if extracted_dir_path:
                    extracted_dir = Path(extracted_dir_path)
                else:
                    extracted_dir = self.base_dir / self.config['processing']['extracted_dir'] / zip_path.stem
                
                if not extracted_dir.exists():
                    logger.warning(f"   Extracted directory not found at {extracted_dir}, will re-extract")
                    extracted_dir = None
                else:
                    logger.info(f"   Using existing extracted directory: {extracted_dir}")
                skip_to_upload = False
            else:
                extracted_dir = None
                skip_to_upload = False
            
            # Extract this zip file if not already extracted
            if extracted_dir is None and not skip_to_upload:
                try:
                    extracted_dir = self.extractor.extract_zip(zip_path)
                    self.statistics.record_zip_extraction(zip_path.name, success=True)
                    
                    # Mark as extracted in state (save immediately)
                    logger.info(f"💾 Marking {zip_path.name} as extracted in state")
                    self.state_manager.mark_zip_extracted(zip_path.name, str(extracted_dir))
                except (zipfile.BadZipFile, ExtractionError, RuntimeError) as e:
                    # Handle corrupted zip file
                    error_msg = str(e)
                    logger.error(f"❌ Corrupted zip file detected: {zip_path.name}")
                    logger.error(f"   Error: {error_msg}")
                    
                    # Track statistics
                    self.statistics.record_zip_corrupted(zip_path.name, error_msg)
                    
                    # Save to corrupted zips file if we have file_info
                    if file_info:
                        self._save_corrupted_zip(file_info, zip_path, error_msg)
                    else:
                        # Try to create minimal file_info from zip_path
                        minimal_info = {
                            'id': 'unknown',
                            'name': zip_path.name,
                            'size': str(zip_path.stat().st_size) if zip_path.exists() else '0'
                        }
                        self._save_corrupted_zip(minimal_info, zip_path, error_msg)
                    
                    # Mark as failed extraction
                    self.state_manager.mark_zip_failed(
                        zip_path.name,
                        ZipProcessingState.FAILED_EXTRACTION,
                        error_msg
                    )
                    
                    # Delete corrupted file so it can be re-downloaded
                    logger.warning(f"⚠️  Deleting corrupted zip file: {zip_path.name}")
                    logger.warning(f"   This file has been saved to corrupted_zips.json and will be re-downloaded")
                    try:
                        zip_path.unlink()
                        logger.info(f"   ✓ Deleted corrupted file: {zip_path.name}")
                    except Exception as delete_error:
                        logger.error(f"   Could not delete corrupted file: {delete_error}")
                    
                    return False
            
            # If already converted, skip to upload step
            if skip_to_upload:
                logger.info(f"⏭️  Skipping extraction and conversion for {zip_path.name}, proceeding to upload")
                processed_dir = self.base_dir / self.config['processing']['processed_dir']
                processed_files = list(processed_dir.glob("*"))
                
                if not processed_files:
                    logger.error(f"❌ No processed files found for {zip_path.name} - cannot proceed with upload")
                    logger.error(f"   You may need to re-extract and re-convert this zip file")
                    return False
                
                # Build file list from processed files (only image/video files)
                from google_photos_icloud_migration.processor.extractor import MEDIA_EXTENSIONS
                processed_file_paths = [
                    Path(f) for f in processed_files 
                    if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
                ]
                logger.info(f"Found {len(processed_file_paths)} processed files to upload")
                
                if not processed_file_paths:
                    logger.error(f"❌ No valid processed files found for {zip_path.name}")
                    logger.error(f"   Cannot proceed with upload - may need to re-extract")
                    return False
                
                # Create a minimal file-to-album mapping (we don't have album info without extraction)
                file_to_album = {}
                albums = {}
                processed_files = processed_file_paths  # Set for upload section
                
                # Try to get album info from file names or metadata if possible
                # For now, upload without album info
                logger.warning(f"⚠️  Album information not available for {zip_path.name} (skipped extraction)")
                logger.warning(f"   Files will be uploaded without album assignments")
                
                # Skip to upload section
                upload_ready = True
            else:
                upload_ready = False
                
                # Identify media files and their JSON metadata pairs
                if extracted_dir and extracted_dir.exists():
                    media_json_pairs = self.extractor.identify_media_json_pairs(extracted_dir)
                else:
                    logger.error(f"❌ Extracted directory not found for {zip_path.name}")
                    return False
                
            if not upload_ready:
                logger.info(f"Found {len(media_json_pairs)} media files in this zip")
                
                # Track statistics
                total_media = len(media_json_pairs)
                with_metadata = sum(1 for v in media_json_pairs.values() if v is not None)
                self.statistics.record_media_files(total_media, with_metadata)
                
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
                
                # Mark as converted (metadata processed) in state (save immediately)
                logger.info(f"💾 Marking {zip_path.name} as converted (metadata processed) in state")
                self.state_manager.mark_zip_converted(zip_path.name)
                
                # Parse albums for this zip
                parser = AlbumParser()
                parser.parse_from_directory_structure(extracted_dir)
                parser.parse_from_json_metadata(media_json_pairs)
                albums = parser.get_all_albums()
                self.statistics.record_albums(len(albums))
                
                # Build file-to-album mapping from original files
                original_file_to_album = {}
                for album_name, files in albums.items():
                    for file_path in files:
                        original_file_to_album[file_path] = album_name
                
                # Get processed files and build mapping from processed files to albums
                processed_files = []
                file_to_album = {}  # Maps processed/original file paths to album names
                skipped_files = []
                for media_file in media_json_pairs.keys():
                    processed_file = processed_dir / media_file.name
                    if processed_file.exists():
                        processed_files.append(processed_file)
                        # Map processed file to album using original file's album
                        album_name = original_file_to_album.get(media_file, '')
                        if album_name:
                            file_to_album[processed_file] = album_name
                    elif media_file.exists():
                        # Fall back to original file if processed file doesn't exist
                        processed_files.append(media_file)
                        # Map original file to album
                        album_name = original_file_to_album.get(media_file, '')
                        if album_name:
                            file_to_album[media_file] = album_name
                    else:
                        # Neither processed nor original file exists - skip it
                        skipped_files.append(media_file)
                        logger.warning(f"File does not exist (processed or original), skipping: {media_file.name}")
                
                if skipped_files:
                    logger.warning(f"Skipping {len(skipped_files)} missing files out of {len(media_json_pairs)} total")
            
            # Upload files from this zip
            if self.icloud_uploader is None:
                self.setup_icloud_uploader()
            
            # Create verification failure callback
            def verification_failure_callback(failed_file_path: Path):
                """Callback for handling verification failures."""
                self.statistics.record_verification_failure(failed_file_path.name, "Verification failed")
                action = self._handle_verification_failure(failed_file_path)
                if action == 'stop':
                    raise RuntimeError(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
            
            # Create upload success callback for incremental cleanup
            def upload_success_callback(file_path: Path):
                """Delete processed file immediately after successful upload to free space."""
                processed_dir = self.base_dir / self.config['processing']['processed_dir']
                if file_path.exists() and str(file_path).startswith(str(processed_dir)):
                    try:
                        file_path.unlink()
                        logger.debug(f"✓ Deleted {file_path.name} after successful upload")
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path.name} after upload: {e}")
            
            # Upload using PhotoKit sync method
            upload_results = self.icloud_uploader.upload_files_batch(
                processed_files,
                albums=file_to_album,
                verify_after_upload=True,
                on_verification_failure=verification_failure_callback,
                on_upload_success=upload_success_callback
            )
            
            successful = sum(1 for v in upload_results.values() if v)
            failed_count = len(upload_results) - successful
            
            # Track statistics
            for file_path, success in upload_results.items():
                file_size = file_path.stat().st_size if file_path.exists() else 0
                self.statistics.record_upload(
                    file_path.name,
                    size=file_size,
                    success=success,
                    error=None if success else "Upload failed"
                )
            
            logger.info(f"Uploaded {successful}/{len(upload_results)} files from {zip_path.name}")
            
            # Mark as uploaded in state (save immediately, even if some files failed)
            # Only mark as complete if all files uploaded successfully
            if failed_count == 0:
                logger.info(f"💾 Marking {zip_path.name} as uploaded (complete) in state")
                self.state_manager.mark_zip_uploaded(zip_path.name)
            else:
                # Some files failed - mark as partial upload but don't mark as complete
                logger.warning(f"⚠️  {zip_path.name} has {failed_count} failed uploads - not marking as complete")
                # State remains at CONVERTED so it can be retried
            
            # Save failed uploads for retry
            failed_files = []
            if failed_count > 0:
                failed_files = [str(path) for path, success in upload_results.items() if not success]
                self._save_failed_uploads(failed_files, file_to_album)
                logger.warning(f"⚠️  {failed_count} files from {zip_path.name} failed to upload")
                logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
            
            # Cleanup successfully uploaded processed files (save disk space)
            # Keep failed uploads for retry
            import shutil
            cleaned_count = 0
            for file_path, success in upload_results.items():
                # Only delete processed files (not original extracted files)
                # and only if upload was successful
                if success and file_path.exists() and str(file_path).startswith(str(processed_dir)):
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete processed file {file_path.name}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"✓ Cleaned up {cleaned_count} successfully uploaded processed files")
            
            # Cleanup extracted files for this zip (save disk space)
            if extracted_dir.exists():
                logger.info(f"Cleaning up extracted files for {zip_path.name}")
                shutil.rmtree(extracted_dir)
                logger.info(f"✓ Cleaned up extracted files for {zip_path.name}")
            
            logger.info(f"✓ Completed processing {zip_path.name}")
            self.statistics.record_zip_processed(success=True)
            return True
            
        except MigrationStoppedException:
            # Re-raise to stop migration
            raise
        except Exception as e:
            logger.error(f"Failed to process {zip_path.name}: {e}", exc_info=True)
            self.statistics.record_zip_processed(success=False)
            return False
    
    def _restart_from_scratch(self):
        """
        Clean up all downloaded files, extracted files, processed files, and tracking files.
        This allows the migration to restart from scratch, re-downloading and reprocessing everything.
        """
        logger.info("=" * 60)
        logger.info("Restarting from scratch - Cleaning up all files and history")
        logger.info("=" * 60)
        
        import shutil
        
        # Clean up zip files
        zip_dir = self.base_dir / self.config['processing']['zip_dir']
        if zip_dir.exists():
            zip_files = list(zip_dir.glob("*.zip"))
            if zip_files:
                logger.info(f"Deleting {len(zip_files)} downloaded zip file(s)...")
                for zip_file in zip_files:
                    try:
                        zip_file.unlink()
                        logger.debug(f"  Deleted: {zip_file.name}")
                    except Exception as e:
                        logger.warning(f"  Could not delete {zip_file.name}: {e}")
        
        # Clean up extracted files
        extracted_dir = self.base_dir / self.config['processing']['extracted_dir']
        if extracted_dir.exists():
            logger.info(f"Deleting extracted files directory: {extracted_dir}")
            try:
                shutil.rmtree(extracted_dir)
                logger.info("  ✓ Deleted extracted files")
            except Exception as e:
                logger.warning(f"  Could not delete extracted directory: {e}")
        
        # Clean up processed files
        processed_dir = self.base_dir / self.config['processing']['processed_dir']
        if processed_dir.exists():
            logger.info(f"Deleting processed files directory: {processed_dir}")
            try:
                shutil.rmtree(processed_dir)
                logger.info("  ✓ Deleted processed files")
            except Exception as e:
                logger.warning(f"  Could not delete processed directory: {e}")
        
        # Clean up tracking files
        if self.failed_uploads_file.exists():
            logger.info(f"Deleting failed uploads tracking file: {self.failed_uploads_file}")
            try:
                self.failed_uploads_file.unlink()
                logger.info("  ✓ Deleted failed uploads file")
            except Exception as e:
                logger.warning(f"  Could not delete failed uploads file: {e}")
        
        if self.corrupted_zips_file.exists():
            logger.info(f"Deleting corrupted zips tracking file: {self.corrupted_zips_file}")
            try:
                self.corrupted_zips_file.unlink()
                logger.info("  ✓ Deleted corrupted zips file")
            except Exception as e:
                logger.warning(f"  Could not delete corrupted zips file: {e}")
        
        # Clear state manager (since we're restarting from scratch)
        logger.info("Clearing state manager...")
        self.state_manager.clear_state()
        logger.info("  ✓ Cleared state manager")
        
        # Reset state flags
        self._skip_continue_prompts = False
        self.ignore_all_verification_failures = False
        
        logger.info("=" * 60)
        logger.info("✓ Cleanup complete - Ready to restart from scratch")
        logger.info("=" * 60)
        logger.info("")
    
    def _find_existing_zips(self, zip_dir: Path, zip_file_list: List[dict]) -> List[Path]:
        """
        Find zip files that are already downloaded locally and validate them.
        
        Args:
            zip_dir: Directory containing zip files
            zip_file_list: List of zip file metadata from Google Drive
        
        Returns:
            List of paths to existing zip files
        """
        existing_zips = []
        zip_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dict mapping file names to file_info for quick lookup and size validation
        expected_files = {file_info['name']: file_info for file_info in zip_file_list}
        
        # Find matching zip files in the directory and validate them
        for zip_file in zip_dir.glob("*.zip"):
            if zip_file.name in expected_files:
                file_info = expected_files[zip_file.name]
                expected_size = None
                if 'size' in file_info:
                    try:
                        expected_size = int(file_info['size'])
                    except (ValueError, TypeError):
                        pass
                
                # Validate that this is a valid zip file
                if self._validate_zip_file(zip_file, expected_size=expected_size):
                    existing_zips.append(zip_file)
                else:
                    # File is corrupted - delete it so it will be re-downloaded
                    logger.warning(f"⚠️  Found corrupted/invalid zip file: {zip_file.name}")
                    logger.warning(f"   Deleting corrupted file - it will be re-downloaded")
                    try:
                        zip_file.unlink()
                        logger.info(f"   ✓ Deleted corrupted file: {zip_file.name}")
                    except Exception as e:
                        logger.error(f"   Could not delete corrupted file {zip_file.name}: {e}")
        
        return sorted(existing_zips)  # Sort for consistent processing order
    
    def _get_current_disk_usage_gb(self) -> float:
        """
        Calculate current disk usage in the base directory.
        
        Returns:
            Current disk usage in GB
        """
        import shutil
        total_size = 0
        
        # Calculate size of all files in base directory
        for root, dirs, files in os.walk(self.base_dir):
            for file in files:
                try:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
                except (OSError, FileNotFoundError):
                    # Skip files that can't be accessed
                    continue
        
        return total_size / (1024 ** 3)
    
    def _validate_zip_file(self, zip_path: Path, expected_size: Optional[int] = None) -> bool:
        """
        Validate that a zip file is valid and complete.
        
        Args:
            zip_path: Path to zip file to validate
            expected_size: Optional expected file size in bytes
        
        Returns:
            True if valid, False if corrupted or incomplete
        """
        # Check if file exists
        if not zip_path.exists():
            return False
        
        # Check file size if expected size is provided
        actual_size = zip_path.stat().st_size
        if expected_size:
            # If file is smaller than expected, it's likely incomplete
            if actual_size < expected_size:
                logger.warning(
                    f"File {zip_path.name} is smaller than expected: "
                    f"{actual_size / (1024*1024):.1f} MB vs {expected_size / (1024*1024):.1f} MB"
                )
                return False
            # If file is significantly larger, it might be corrupted (but allow some tolerance)
            elif actual_size > expected_size * 1.1:  # 10% tolerance
                logger.warning(
                    f"File {zip_path.name} is significantly larger than expected: "
                    f"{actual_size / (1024*1024):.1f} MB vs {expected_size / (1024*1024):.1f} MB"
                )
        
        # Try to open and validate the zip file
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                # Test zip integrity
                test_zip.testzip()
            return True
        except zipfile.BadZipFile:
            logger.warning(f"File {zip_path.name} is not a valid zip file")
            return False
        except (OSError, IOError) as e:
            logger.warning(f"Error accessing {zip_path.name}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error validating {zip_path.name}: {e}")
            return False
    
    def run(self, retry_failed: bool = False):
        """
        Run the complete migration process using PhotoKit sync method (macOS only).
        
        Args:
            retry_failed: If True, only retry previously failed uploads
        """
        # If retry mode, just retry failed uploads and exit
        if retry_failed:
            self.statistics.start()
            self.setup_icloud_uploader()
            # Check if we should also re-download zips
            redownload_zips = getattr(self, '_redownload_zips', False)
            self.retry_failed_uploads(redownload_zips=redownload_zips)
            self._generate_final_report(0, 0)
            return
        
        try:
            # Phase 1: List all zip files (without downloading yet)
            logger.info("=" * 60)
            logger.info("Phase 1: Listing zip files from Google Drive")
            logger.info("=" * 60)
            
            drive_config = self.config['google_drive']
            zip_dir = self.base_dir / self.config['processing']['zip_dir']
            
            # Start statistics tracking
            self.statistics.start()
            
            # Log state file location for debugging
            state_file = self.state_manager.zip_state_file
            logger.info(f"📂 State file location: {state_file}")
            if state_file.exists():
                logger.info(f"   State file exists: {state_file.stat().st_size} bytes")
            else:
                logger.info("   State file does not exist (will be created)")
            
            # Display disk space limit if configured
            max_disk_space_gb = self.config['processing'].get('max_disk_space_gb')
            if max_disk_space_gb:
                logger.info(f"Disk space limit: {max_disk_space_gb} GB")
            else:
                logger.info("Disk space limit: Unlimited")
            
            # List files without downloading
            zip_file_list = self.downloader.list_zip_files(
                folder_id=drive_config.get('folder_id') or None,
                pattern=drive_config.get('zip_file_pattern') or None
            )
            
            if not zip_file_list:
                logger.error("No zip files found. Exiting.")
                self._generate_final_report(0, 0)
                return
            
            # Sort zip files by name for consistent processing order
            zip_file_list = sorted(zip_file_list, key=lambda x: x['name'])
            
            self.statistics.zip_files_total = len(zip_file_list)
            
            # Check state manager for already completed zips
            completed_zips = set()
            converted_zips = set()  # Zips that are converted but not uploaded
            all_state_zips = set(self.state_manager._zip_state.keys())
            logger.debug(f"State contains {len(all_state_zips)} zip file entries")
            
            for zip_info in zip_file_list:
                zip_name = zip_info['name']
                zip_state = self.state_manager.get_zip_state(zip_name)
                if zip_state:
                    logger.debug(f"Zip {zip_name} has state: {zip_state}")
                    if zip_state == ZipProcessingState.CONVERTED.value:
                        converted_zips.add(zip_name)
                if self.state_manager.is_zip_complete(zip_name):
                    completed_zips.add(zip_name)
            
            if completed_zips:
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"✅ Found {len(completed_zips)} already-completed zip files in state")
                logger.info("These will be skipped during processing")
                logger.info("=" * 60)
                # Log first few completed zips for visibility
                completed_list = sorted(list(completed_zips))[:10]
                for zip_name in completed_list:
                    logger.info(f"  ✓ {zip_name} (already completed)")
                if len(completed_zips) > 10:
                    logger.info(f"  ... and {len(completed_zips) - 10} more completed zips")
                logger.info("=" * 60)
                logger.info("")
            
            if converted_zips:
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"🔄 Found {len(converted_zips)} zip files that are converted but not uploaded")
                logger.info("These will resume from upload step (skipping extraction/conversion)")
                logger.info("=" * 60)
                # Log first few converted zips for visibility
                converted_list = sorted(list(converted_zips))[:10]
                for zip_name in converted_list:
                    logger.info(f"  ↻ {zip_name} (will resume upload)")
                if len(converted_zips) > 10:
                    logger.info(f"  ... and {len(converted_zips) - 10} more converted zips")
                logger.info("=" * 60)
                logger.info("")
            
            if not completed_zips and not converted_zips:
                logger.info("")
                logger.info("ℹ️  No previously processed zip files found in state")
                logger.info("   All zip files will be processed from the beginning")
                logger.info("")
            
            # Setup iCloud uploader once (before processing zips)
            self.setup_icloud_uploader()
            
            # Create mapping from file name to file_info for looking up existing zips
            file_info_by_name = {file_info['name']: file_info for file_info in zip_file_list}
            
            successful = 0
            failed = 0
            total_zips = len(zip_file_list)
            processed_count = 0
            
            # ZERO: Process converted zips that have processed files (upload-only, no zip file needed)
            # This MUST run BEFORE _find_existing_zips to catch zips that don't need zip files
            converted_zips_processed = set()
            for zip_info in zip_file_list:
                zip_name = zip_info['name']
                zip_state = self.state_manager.get_zip_state(zip_name)
                if zip_state == ZipProcessingState.CONVERTED.value:
                    processed_dir = self.base_dir / self.config['processing']['processed_dir']
                    processed_files = list(processed_dir.glob("*"))
                    if processed_files:
                        # This zip is converted and has processed files - upload directly (no zip file needed)
                        processed_count += 1
                        try:
                            logger.info("=" * 60)
                            logger.info(f"Processing converted zip {processed_count}/{total_zips}: {zip_name} (upload-only, no zip file needed)")
                            logger.info("=" * 60)
                            
                            if self._process_upload_only(zip_name, processed_count, total_zips):
                                successful += 1
                                converted_zips_processed.add(zip_name)
                            else:
                                failed += 1
                            
                            # Ask user if they want to continue after each zip (unless they chose "Continue All")
                            if not self._skip_continue_prompts:
                                if not self._ask_continue_after_zip(processed_count, total_zips):
                                    logger.info("Migration stopped by user after zip file processing.")
                                    self._generate_final_report(successful, total_zips)
                                    return
                        except Exception as e:
                            failed += 1
                            logger.error(f"Error processing upload-only for {zip_name}: {e}", exc_info=True)
            
            # Check for already-downloaded zip files
            # Filter out zips that are converted and have processed files (they don't need zip files)
            zips_needing_download = []
            for file_info in zip_file_list:
                zip_name = file_info['name']
                # Skip if we already processed it in upload-only mode
                if zip_name in converted_zips_processed:
                    continue
                zip_state = self.state_manager.get_zip_state(zip_name)
                if zip_state == ZipProcessingState.CONVERTED.value:
                    processed_dir = self.base_dir / self.config['processing']['processed_dir']
                    processed_files = list(processed_dir.glob("*"))
                    if processed_files:
                        # This zip doesn't need to be downloaded - we have processed files
                        logger.debug(f"Skipping {zip_name} from download check - has processed files")
                        continue
                zips_needing_download.append(file_info)
            
            existing_zips = self._find_existing_zips(zip_dir, zips_needing_download)
            
            if existing_zips:
                total_size_gb = sum(f.stat().st_size for f in existing_zips) / (1024 ** 3)
                self.statistics.zip_files_skipped_existing = len(existing_zips)
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"Found {len(existing_zips)} already-downloaded zip files ({total_size_gb:.2f} GB)")
                logger.info("These will be processed FIRST to free up disk space")
                logger.info("=" * 60)
                logger.info("")
            
            logger.info(f"Found {len(zip_file_list)} zip files total to process")
            logger.info("")
            logger.info("Processing each zip file individually:")
            logger.info("  - Download → Extract → Process metadata → Upload → Cleanup")
            logger.info("  (This approach minimizes disk space usage)")
            logger.info("")
            
            # FIRST: Process already-downloaded zip files to free up space
            for existing_zip in existing_zips:
                # Skip if already completed according to state
                if self.state_manager.is_zip_complete(existing_zip.name):
                    logger.info(f"⏭️  Skipping {existing_zip.name} - already completed (marked in state)")
                    # Delete the zip file if it exists but is already completed
                    if existing_zip.exists():
                        logger.info(f"🗑️  Deleting already-completed zip file: {existing_zip.name}")
                        existing_zip.unlink()
                    continue
                
                # Check current state and log it
                current_state = self.state_manager.get_zip_state(existing_zip.name)
                if current_state:
                    logger.info(f"📊 {existing_zip.name} current state: {current_state}")
                    # If already downloaded but not extracted, mark as downloaded
                    if current_state == ZipProcessingState.PENDING.value:
                        logger.info(f"💾 Marking {existing_zip.name} as downloaded (file exists)")
                        self.state_manager.set_zip_state(
                            existing_zip.name,
                            ZipProcessingState.DOWNLOADED,
                            metadata={'file_size': existing_zip.stat().st_size if existing_zip.exists() else 0}
                        )
                
                processed_count += 1
                try:
                    logger.info("=" * 60)
                    logger.info(f"Processing existing zip {processed_count}/{total_zips}: {existing_zip.name}")
                    logger.info("=" * 60)
                    
                    # Look up file_info for this existing zip
                    file_info = file_info_by_name.get(existing_zip.name)
                    
                    # Process this zip file (state is now tracked inside process_single_zip)
                    if self.process_single_zip(existing_zip, processed_count, total_zips, file_info=file_info):
                        successful += 1
                        # State is already marked as uploaded inside process_single_zip
                        
                        # Cleanup zip file after successful processing to free up space
                        logger.info(f"Deleting zip file to free up disk space: {existing_zip.name}")
                        existing_zip.unlink()
                        logger.info(f"✓ Deleted {existing_zip.name}")
                    else:
                        failed += 1
                        logger.warning(f"Failed to process {existing_zip.name}, keeping zip file for retry")
                    
                    # Ask user if they want to continue after each zip (unless they chose "Continue All")
                    if not self._skip_continue_prompts:
                        if not self._ask_continue_after_zip(processed_count, total_zips):
                            logger.info("Migration stopped by user after zip file processing.")
                            self._generate_final_report(successful, total_zips)
                            return
                        
                        # Check if restart was requested
                        if self._restart_requested:
                            self._restart_from_scratch()
                            self._restart_requested = False
                            logger.info("Restarting migration from scratch...")
                            # Recursively call run() to restart the entire process
                            return self.run(retry_failed=False)
                        
                except MigrationStoppedException as e:
                    logger.info("Migration stopped by user.")
                    logger.info(f"Reason: {e}")
                    self._generate_final_report(successful, total_zips)
                    return
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {existing_zip.name}: {e}", exc_info=True)
                    logger.warning(f"Skipping remaining processing for {existing_zip.name}")
            
            # THEN: Download and process remaining zip files
            for file_info in zip_file_list:
                zip_name = file_info['name']
                zip_file_path = zip_dir / zip_name
                
                # Skip if already completed according to state
                if self.state_manager.is_zip_complete(zip_name):
                    logger.info(f"⏭️  Skipping {zip_name} - already completed (marked in state)")
                    continue
                
                # Skip if we already processed this in upload-only mode (ZERO step)
                if zip_name in converted_zips_processed:
                    logger.debug(f"Skipping {zip_name} - already processed in upload-only mode")
                    continue
                
                # Skip if zip is already converted and has processed files (but wasn't processed yet)
                # This means zip file exists and we should process it (will skip extraction/conversion)
                zip_state = self.state_manager.get_zip_state(zip_name)
                if zip_state == ZipProcessingState.CONVERTED.value:
                    processed_dir = self.base_dir / self.config['processing']['processed_dir']
                    processed_files = list(processed_dir.glob("*"))
                    if processed_files and not zip_file_path.exists():
                        # Processed files exist but zip doesn't - should have been handled in ZERO step
                        # But if we get here, skip it to avoid re-downloading
                        logger.info(f"⏭️  Skipping {zip_name} - has processed files, no zip file needed")
                        continue
                
                # Skip if we already downloaded this file (but haven't processed it yet)
                if zip_file_path.exists():
                    continue
                
                # Check disk space limit before downloading
                max_disk_space_gb = self.config['processing'].get('max_disk_space_gb')
                if max_disk_space_gb:
                    current_usage_gb = self._get_current_disk_usage_gb()
                    file_size_gb = int(file_info.get('size', 0)) / (1024 ** 3) if file_info.get('size') else 0
                    
                    # Estimate total usage after download (zip + extracted + processed)
                    # Rough estimate: zip size * 2.5 (zip + extracted + processed)
                    estimated_usage_after = current_usage_gb + (file_size_gb * 2.5)
                    
                    if estimated_usage_after > max_disk_space_gb:
                        logger.warning("=" * 60)
                        logger.warning(f"⚠️  Disk space limit reached: {current_usage_gb:.1f} GB used / {max_disk_space_gb} GB limit")
                        logger.warning(f"   Skipping download of {zip_name} ({file_size_gb:.1f} GB)")
                        logger.warning(f"   Estimated usage after download: {estimated_usage_after:.1f} GB")
                        logger.warning("   Processing existing files to free up space...")
                        logger.warning("   You can increase the limit with --max-disk-space or in config.yaml")
                        logger.warning("=" * 60)
                        continue
                
                processed_count += 1
                try:
                    # Download this zip file
                    logger.info("=" * 60)
                    logger.info(f"Downloading zip {processed_count}/{total_zips}: {file_info['name']}")
                    logger.info("=" * 60)
                    
                    try:
                        zip_file = self.downloader.download_single_zip(file_info, zip_dir)
                        file_size = zip_file.stat().st_size if zip_file.exists() else 0
                        self.statistics.record_zip_download(file_info['name'], size=file_size, success=True)
                        
                        # Mark as downloaded in state (save immediately)
                        logger.info(f"💾 Marking {zip_file.name} as downloaded in state")
                        self.state_manager.set_zip_state(
                            zip_file.name, 
                            ZipProcessingState.DOWNLOADED,
                            metadata={'file_size': file_size}
                        )
                    except Exception as download_error:
                        self.statistics.record_zip_download(
                            file_info['name'], 
                            size=0, 
                            success=False, 
                            error=str(download_error)
                        )
                        # Mark as failed download
                        self.state_manager.mark_zip_failed(
                            file_info['name'],
                            ZipProcessingState.FAILED_DOWNLOAD,
                            str(download_error)
                        )
                        raise
                    
                    # Process this zip file (state is now tracked inside process_single_zip)
                    if self.process_single_zip(zip_file, processed_count, total_zips, file_info=file_info):
                        successful += 1
                        # State is already marked as uploaded inside process_single_zip
                        
                        # Cleanup zip file after successful processing to free up space
                        logger.info(f"Deleting zip file to free up disk space: {zip_file.name}")
                        zip_file.unlink()
                        logger.info(f"✓ Deleted {zip_file.name}")
                    else:
                        failed += 1
                        logger.warning(f"Failed to process {zip_file.name}, keeping zip file for retry")
                    
                    # Ask user if they want to continue after each zip (unless they chose "Continue All")
                    if not self._skip_continue_prompts:
                        if not self._ask_continue_after_zip(processed_count, total_zips):
                            logger.info("Migration stopped by user after zip file processing.")
                            self._generate_final_report(successful, total_zips)
                            return
                        
                        # Check if restart was requested
                        if self._restart_requested:
                            self._restart_from_scratch()
                            self._restart_requested = False
                            logger.info("Restarting migration from scratch...")
                            # Recursively call run() to restart the entire process
                            return self.run(retry_failed=False)
                        
                except MigrationStoppedException as e:
                    logger.info("Migration stopped by user.")
                    logger.info(f"Reason: {e}")
                    self._generate_final_report(successful, total_zips)
                    return
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {file_info.get('name', 'unknown')}: {e}", exc_info=True)
                    logger.warning(f"Skipping remaining processing for {file_info.get('name', 'unknown')}")
            
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
            
            # Check for failed uploads and corrupted zips
            failed_uploads_exist = self.failed_uploads_file.exists() and self.failed_uploads_file.stat().st_size > 0
            corrupted_zips_exist = self.corrupted_zips_file.exists() and self.corrupted_zips_file.stat().st_size > 0
            
            logger.info("=" * 60)
            logger.info(f"Migration completed!")
            logger.info(f"  Successful: {successful}/{len(zip_file_list)} zip files")
            if failed > 0:
                logger.info(f"  Failed: {failed}/{len(zip_file_list)} zip files")
            
            if corrupted_zips_exist:
                logger.info("")
                logger.warning("=" * 60)
                logger.warning("⚠️  CORRUPTED ZIP FILES DETECTED")
                logger.warning("=" * 60)
                try:
                    with open(self.corrupted_zips_file, 'r') as f:
                        corrupted_data = json.load(f)
                    corrupted_count = len(corrupted_data)
                    logger.warning(f"Found {corrupted_count} corrupted zip file(s)")
                    logger.warning(f"Corrupted zip files saved to: {self.corrupted_zips_file}")
                    logger.warning("")
                    logger.warning("These files need to be re-downloaded from Google Drive:")
                    for file_id, file_data in corrupted_data.items():
                        logger.warning(f"  - {file_data.get('file_name', 'unknown')}")
                        if file_data.get('local_size_mb'):
                            logger.warning(f"    Local size: {file_data['local_size_mb']:.1f} MB")
                        if file_data.get('file_size'):
                            try:
                                expected_size_mb = int(file_data['file_size']) / (1024 * 1024)
                                logger.warning(f"    Expected size: {expected_size_mb:.1f} MB")
                            except (ValueError, TypeError):
                                pass
                    logger.warning("")
                    logger.warning("You can manually re-download these files from Google Drive")
                    logger.warning("or delete the corrupted local files and re-run the script")
                    logger.warning("=" * 60)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read corrupted zips file: {e}")
            
            if failed_uploads_exist:
                logger.info("")
                logger.warning("⚠️  Some files failed to upload to iCloud")
                logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
                logger.warning("To retry failed uploads, run:")
                logger.warning(f"  python main.py --config {self.config_path} --retry-failed")
            
            # Generate final report
            self._generate_final_report(successful, total_zips)
            
        except Exception as e:
            self.statistics.finish()
            logger.error(f"Migration failed: {e}", exc_info=True)
            # Generate report even on failure
            self._generate_final_report(0, 0)
            raise
    
    def _generate_final_report(self, successful: int = 0, total_zips: int = 0):
        """
        Generate and save the final migration report.
        
        Args:
            successful: Number of successfully processed zip files
            total_zips: Total number of zip files
        """
        # Finish statistics tracking
        self.statistics.finish()
        
        # Generate and save report
        logger.info("")
        logger.info("=" * 80)
        logger.info("GENERATING MIGRATION REPORT")
        logger.info("=" * 80)
        
        report_generator = ReportGenerator(
            statistics=self.statistics,
            base_dir=self.base_dir,
            log_file=self.log_file_path if hasattr(self, 'log_file_path') else None,
            failed_uploads_file=self.failed_uploads_file,
            corrupted_zips_file=self.corrupted_zips_file
        )
        
        report_path = report_generator.save_report()
        logger.info("")
        logger.info(f"✓ Migration report saved to: {report_path.absolute()}")
        logger.info("")
        
        # Also save statistics to JSON
        stats_path = self.base_dir / 'migration_statistics.json'
        self.statistics.save(stats_path)
        logger.info(f"✓ Statistics saved to: {stats_path.absolute()}")
        logger.info("")
        
        # Print summary to console
        logger.info("=" * 80)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        if total_zips > 0:
            logger.info(f"Zip Files:        {successful}/{total_zips} successful")
        logger.info(f"Media Files:      {self.statistics.media_files_found} found, {self.statistics.files_uploaded_successfully} uploaded")
        logger.info(f"Albums:           {self.statistics.albums_identified} identified")
        if self.statistics.get_duration():
            logger.info(f"Duration:         {report_generator._format_duration(self.statistics.get_duration())}")
        logger.info("")
        logger.info(f"📄 Full report:   {report_path.absolute()}")
        logger.info(f"📊 Statistics:    {stats_path.absolute()}")
        logger.info("=" * 80)


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
    # PhotoKit sync method is now the only method (macOS only)
    # No --use-sync flag needed as sync is always used
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retry previously failed uploads (skips download/extract/process steps)'
    )
    parser.add_argument(
        '--redownload-zips',
        action='store_true',
        help='When used with --retry-failed, also re-download and re-process zip files containing failed uploads'
    )
    parser.add_argument(
        '--max-disk-space',
        type=float,
        default=None,
        metavar='GB',
        help='Maximum disk space to use in GB (overrides config file). Set to 0 for unlimited. Example: --max-disk-space 100'
    )
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator(args.config)
    
    # Override max_disk_space_gb from command line if provided
    if args.max_disk_space is not None:
        if args.max_disk_space == 0:
            orchestrator.config['processing']['max_disk_space_gb'] = None
            logger.info("Disk space limit: Unlimited (set via --max-disk-space 0)")
        else:
            orchestrator.config['processing']['max_disk_space_gb'] = args.max_disk_space
            logger.info(f"Disk space limit: {args.max_disk_space} GB (set via --max-disk-space)")
    
    # Store redownload_zips flag in orchestrator for retry mode
    if args.retry_failed and args.redownload_zips:
        orchestrator._redownload_zips = True
    
    orchestrator.run(retry_failed=args.retry_failed)


if __name__ == '__main__':
    main()
