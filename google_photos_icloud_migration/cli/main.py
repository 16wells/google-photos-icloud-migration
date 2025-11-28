"""
Main orchestration script for Google Photos to iCloud Photos migration.
"""
import argparse
import json
import logging
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import jsonschema
from tqdm import tqdm

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from google_photos_icloud_migration.downloader.drive_downloader import DriveDownloader
from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.parser.album_parser import AlbumParser
from google_photos_icloud_migration.uploader.icloud_uploader import iCloudUploader, iCloudPhotosSyncUploader
from google_photos_icloud_migration.exceptions import ConfigurationError, ExtractionError, CorruptedZipException
from google_photos_icloud_migration.config import MigrationConfig
from google_photos_icloud_migration.utils.logging_config import setup_logging
from google_photos_icloud_migration.utils.state_manager import (
    StateManager, FileProcessingState, ZipProcessingState
)

logger = logging.getLogger(__name__)


class MigrationStoppedException(Exception):
    """Exception raised when user chooses to stop migration."""
    pass


class MigrationOrchestrator:
    """Orchestrates the entire migration process."""
    
    def __init__(self, config_path: str, use_config_class: bool = True):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Path to configuration YAML file
            use_config_class: If True, use MigrationConfig dataclass (recommended)
        """
        self.config_path = config_path
        
        # Load configuration using new Config class if enabled
        if use_config_class:
            try:
                self.migration_config = MigrationConfig.from_yaml(config_path, validate=True)
                # Create backward-compatible dict for gradual migration
                self.config = self._config_to_dict(self.migration_config)
            except ValueError as e:
                raise ConfigurationError(str(e)) from e
        else:
            # Fallback to old dict-based config loading
            self.migration_config = None
            self.config = self._load_config(config_path)
        
        self._setup_logging()
        
        # Initialize components - use config object if available
        if self.migration_config:
            self.base_dir = self.migration_config.processing.base_path
            self.base_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize downloader
            self.downloader = DriveDownloader(
                self.migration_config.google_drive.credentials_file
            )
            
            # Initialize metadata merger
            self.metadata_merger = MetadataMerger(
                preserve_dates=self.migration_config.metadata.preserve_dates,
                preserve_gps=self.migration_config.metadata.preserve_gps,
                preserve_descriptions=self.migration_config.metadata.preserve_descriptions
            )
        else:
            # Fallback to dict-based access
            self.base_dir = Path(self.config['processing']['base_dir'])
            self.base_dir.mkdir(parents=True, exist_ok=True)
            
            drive_config = self.config['google_drive']
            self.downloader = DriveDownloader(drive_config['credentials_file'])
            
            metadata_config = self.config['metadata']
            self.metadata_merger = MetadataMerger(
                preserve_dates=metadata_config['preserve_dates'],
                preserve_gps=metadata_config['preserve_gps'],
                preserve_descriptions=metadata_config['preserve_descriptions']
            )
        
        # Initialize extractor (same for both)
        self.extractor = Extractor(self.base_dir)
        
        # Initialize album parser
        self.album_parser = AlbumParser()
        
        # Initialize iCloud uploader (will be set up later)
        self.icloud_uploader = None
        
        # Failed uploads tracking
        self.failed_uploads_file = self.base_dir / 'failed_uploads.json'
        
        # Corrupted zip files tracking
        self.corrupted_zips_file = self.base_dir / 'corrupted_zips.json'
        
        # Upload tracking to prevent duplicate uploads
        self.upload_tracking_file = self.base_dir / 'uploaded_files.json'
        
        # State management for granular tracking and resumption
        self.state_manager = StateManager(self.base_dir)
        
        # Verification failure handling
        self.ignore_all_verification_failures = False
        
        # Continue prompt handling
        self._skip_continue_prompts = False
        self._restart_requested = False
        self._proceed_after_retries = False
        self._paused_for_retries = False
        self._proceed_after_retries = False
        self._paused_for_retries = False
    
    def _config_to_dict(self, config: MigrationConfig) -> Dict:
        """Convert MigrationConfig object to dict for backward compatibility."""
        return {
            'google_drive': {
                'credentials_file': config.google_drive.credentials_file,
                'folder_id': config.google_drive.folder_id,
                'zip_file_pattern': config.google_drive.zip_file_pattern,
            },
            'icloud': {
                'apple_id': config.icloud.apple_id,
                'password': config.icloud.password,
                'trusted_device_id': config.icloud.trusted_device_id,
                'two_fa_code': config.icloud.two_fa_code,
                'photos_library_path': config.icloud.photos_library_path,
                'method': config.icloud.method,
            },
            'processing': {
                'base_dir': config.processing.base_dir,
                'zip_dir': config.processing.zip_dir,
                'extracted_dir': config.processing.extracted_dir,
                'processed_dir': config.processing.processed_dir,
                'batch_size': config.processing.batch_size,
                'cleanup_after_upload': config.processing.cleanup_after_upload,
            },
            'metadata': {
                'preserve_dates': config.metadata.preserve_dates,
                'preserve_gps': config.metadata.preserve_gps,
                'preserve_descriptions': config.metadata.preserve_descriptions,
                'preserve_albums': config.metadata.preserve_albums,
            },
            'logging': {
                'level': config.logging.level,
                'file': config.logging.file,
            },
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file with validation and environment variable support."""
        # Load YAML config
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except (yaml.YAMLError, IOError, OSError) as e:
            raise ConfigurationError(f"Failed to load configuration file '{config_path}': {e}") from e
        
        if config is None:
            raise ConfigurationError(f"Configuration file '{config_path}' is empty or invalid")
        
        # Note: Validation and env overrides are now handled in MigrationConfig class
        # This method is kept for backward compatibility when use_config_class=False
        
        # Ensure processing section exists with defaults
        if 'processing' not in config:
            config['processing'] = {}
        
        processing_defaults = {
            'base_dir': '/tmp/google-photos-migration',
            'zip_dir': 'zips',
            'extracted_dir': 'extracted',
            'processed_dir': 'processed',
            'batch_size': 100,
            'cleanup_after_upload': True
        }
        
        for key, default_value in processing_defaults.items():
            if key not in config['processing']:
                config['processing'][key] = default_value
        
        return config
    
    def _validate_config(self, config: Dict) -> None:
        """Validate configuration against JSON schema."""
        try:
            schema_path = Path(__file__).parent / 'config_schema.json'
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                
                jsonschema.validate(instance=config, schema=schema)
                logger.debug("Configuration validated against schema")
        except jsonschema.ValidationError as e:
            raise ConfigurationError(
                f"Configuration validation failed: {e.message}\n"
                f"Path: {'.'.join(str(p) for p in e.path)}"
            ) from e
        except (IOError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load configuration schema for validation: {e}")
            # Continue without validation if schema file is missing
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides to configuration."""
        # Create a deep copy to avoid modifying the original
        config = json.loads(json.dumps(config))
        
        # iCloud credentials from environment
        if 'icloud' not in config:
            config['icloud'] = {}
        
        # Override with environment variables if present
        env_apple_id = os.getenv('ICLOUD_APPLE_ID')
        if env_apple_id:
            config['icloud']['apple_id'] = env_apple_id
            logger.debug("Using Apple ID from ICLOUD_APPLE_ID environment variable")
        
        env_password = os.getenv('ICLOUD_PASSWORD')
        if env_password:
            config['icloud']['password'] = env_password
            logger.debug("Using password from ICLOUD_PASSWORD environment variable")
        
        env_2fa_code = os.getenv('ICLOUD_2FA_CODE')
        if env_2fa_code:
            config['icloud']['two_fa_code'] = env_2fa_code
            logger.debug("Using 2FA code from ICLOUD_2FA_CODE environment variable")
        
        env_device_id = os.getenv('ICLOUD_2FA_DEVICE_ID')
        if env_device_id:
            config['icloud']['trusted_device_id'] = env_device_id
            logger.debug("Using device ID from ICLOUD_2FA_DEVICE_ID environment variable")
        
        # Google Drive credentials
        if 'google_drive' not in config:
            config['google_drive'] = {}
        
        env_credentials = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE')
        if env_credentials:
            config['google_drive']['credentials_file'] = env_credentials
            logger.debug("Using credentials file from GOOGLE_DRIVE_CREDENTIALS_FILE environment variable")
        
        return config
    
    def _setup_logging(self):
        """Set up logging configuration with rotation and optional structured logging."""
        # Get logging config from either MigrationConfig or dict
        if self.migration_config:
            log_config = self.migration_config.logging
            log_file = log_config.file
            level = log_config.level
        else:
            log_config = self.config.get('logging', {})
            log_file = log_config.get('file', 'migration.log')
            level = log_config.get('level', 'INFO')
        
        # Set up logging with rotation
        try:
            setup_logging(
                log_file=log_file,
                level=level,
                enable_json=False,  # Can be made configurable
                enable_rotation=True,
                max_bytes=10 * 1024 * 1024,  # 10MB
                backup_count=5,
                separate_error_log=True
            )
        except (OSError, IOError) as e:
            # If we can't create log file (e.g., no disk space), fallback to basic logging
            print(f"Warning: Could not set up advanced logging for '{log_file}': {e}", file=sys.stderr)
            print("Falling back to basic console logging.", file=sys.stderr)
            logging.basicConfig(
                level=getattr(logging, level.upper(), logging.INFO),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
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
        
        # Ask user if this is a new migration or continuing
        is_continuing = self._ask_migration_type()
        
        # If new migration, clear the upload tracking file
        if not is_continuing and self.upload_tracking_file.exists():
            try:
                self.upload_tracking_file.unlink()
                logger.info(f"✓ Cleared upload tracking file: {self.upload_tracking_file}")
            except Exception as e:
                logger.warning(f"Could not clear upload tracking file: {e}")
        
        # Always use tracking file (it will be empty if we just cleared it for new migration)
        if use_sync_method:
            # Get photos library path from config if specified
            photos_library_path = icloud_config.get('photos_library_path')
            if photos_library_path:
                photos_library_path = Path(photos_library_path).expanduser()
            self.icloud_uploader = iCloudPhotosSyncUploader(
                photos_library_path=photos_library_path,
                upload_tracking_file=self.upload_tracking_file
            )
        else:
            password = icloud_config.get('password', '').strip() if icloud_config.get('password') else ''
            # Prompt for password if empty
            if not password:
                import getpass
                logger.info("iCloud password not set in config. Please enter your Apple ID password:")
                logger.info("(Note: If you have 2FA enabled, use your regular password and you'll be prompted for 2FA code)")
                password = getpass.getpass("Password: ").strip()
            
            # Validate Apple ID is present
            apple_id = icloud_config.get('apple_id', '').strip()
            if not apple_id:
                raise ValueError("Apple ID is required in config file (icloud.apple_id)")
            
            self.icloud_uploader = iCloudUploader(
                apple_id=apple_id,
                password=password,
                trusted_device_id=icloud_config.get('trusted_device_id'),
                two_fa_code=icloud_config.get('two_fa_code'),  # Support 2FA code from config or env var
                upload_tracking_file=self.upload_tracking_file
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
            action = self._handle_verification_failure(failed_file_path)
            if action == 'stop':
                raise MigrationStoppedException(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
        
        # Upload files
        all_files = list(media_json_pairs.keys())
        
        if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
            results = self.icloud_uploader.upload_files_batch(
                all_files,
                albums=file_to_album,
                verify_after_upload=True,
                on_verification_failure=verification_failure_callback
            )
        else:
            # Group by album for regular uploader
            results = {}
            for album_name, files in albums.items():
                logger.info(f"Uploading album: {album_name} ({len(files)} files)")
                album_results = self.icloud_uploader.upload_photos_batch(
                    files,
                    album_name=album_name,
                    verify_after_upload=True,
                    on_verification_failure=verification_failure_callback
                )
                results.update(album_results)
        
        successful = sum(1 for v in results.values() if v)
        failed_count = len(results) - successful
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
    
    def _ask_proceed_after_retries(self) -> bool:
        """
        Ask user if they want to proceed with cleanup after retrying failed uploads.
        
        Returns:
            True if user wants to proceed, False if they want to stop
        """
        # Check if we're in a non-interactive environment (web UI)
        import sys
        is_interactive = sys.stdin.isatty()
        
        if not is_interactive:
            # In non-interactive mode (web UI), wait for proceed signal
            logger.info("Waiting for proceed signal from web UI...")
            # Check the proceed flag (set externally by web UI)
            max_wait = 3600  # Wait up to 1 hour
            waited = 0
            while not self._proceed_after_retries and waited < max_wait:
                time.sleep(1)
                waited += 1
                # Check stop flag if available (set by web UI)
                if hasattr(self, '_stop_requested') and self._stop_requested:
                    return False
            
            if waited >= max_wait:
                logger.warning("Timeout waiting for proceed signal. Proceeding automatically.")
                return True
            
            self._proceed_after_retries = False  # Reset for next time
            return True
        
        # Interactive mode - ask user
        logger.info("")
        logger.info("=" * 60)
        logger.info("PROCEED WITH CLEANUP?")
        logger.info("=" * 60)
        logger.info("You have retried failed uploads (or chosen to proceed anyway).")
        logger.info("")
        logger.info("What would you like to do?")
        logger.info("  (P) Proceed - Continue with cleanup and finish migration")
        logger.info("  (S) Stop - Stop here and keep files for manual retry later")
        logger.info("")
        
        while True:
            try:
                choice = input("Enter your choice (P/S): ").strip().upper()
                if choice == 'P':
                    logger.info("Proceeding with cleanup...")
                    return True
                elif choice == 'S':
                    logger.info("Stopping migration. Files kept for manual retry.")
                    return False
                else:
                    logger.warning("Invalid choice. Please enter P (Proceed) or S (Stop).")
            except (EOFError, KeyboardInterrupt) as e:
                logger.warning("")
                logger.warning("Input interrupted. Stopping migration.")
                return False
    
    def _ask_migration_type(self) -> bool:
        """
        Ask user if this is a new migration or continuing an existing one.
        
        Returns:
            True if continuing existing migration (keep tracking), False if new migration (clear tracking)
        """
        # Check if we're in a non-interactive environment
        import sys
        is_interactive = sys.stdin.isatty()
        
        if not is_interactive:
            # In non-interactive mode, check if tracking file exists
            # If it exists, assume continuing; if not, assume new
            if self.upload_tracking_file.exists():
                logger.info("Non-interactive mode: Found existing upload tracking file, continuing existing migration")
                return True
            else:
                logger.info("Non-interactive mode: No upload tracking file found, starting new migration")
                return False
        
        # Check if tracking file exists
        tracking_exists = self.upload_tracking_file.exists()
        
        if tracking_exists:
            logger.info("")
            logger.info("=" * 60)
            logger.info("UPLOAD TRACKING FILE FOUND")
            logger.info("=" * 60)
            logger.info(f"Found existing upload tracking file: {self.upload_tracking_file}")
            logger.info("This file tracks which photos/videos have already been uploaded.")
            logger.info("")
            logger.info("Is this:")
            logger.info("  (N) New Migration - Start fresh, clear upload history")
            logger.info("  (C) Continue Migration - Keep existing upload history (skip already-uploaded files)")
            logger.info("")
            
            while True:
                try:
                    choice = input("Enter your choice (N/C): ").strip().upper()
                    if choice == 'N':
                        logger.info("Starting new migration - clearing upload tracking...")
                        return False
                    elif choice == 'C':
                        logger.info("Continuing existing migration - keeping upload tracking...")
                        return True
                    else:
                        logger.warning("Invalid choice. Please enter N (New Migration) or C (Continue Migration).")
                except (EOFError, KeyboardInterrupt) as e:
                    logger.warning("")
                    logger.warning("Input interrupted. Defaulting to continue existing migration.")
                    return True
        else:
            logger.info("")
            logger.info("=" * 60)
            logger.info("NEW MIGRATION DETECTED")
            logger.info("=" * 60)
            logger.info("No upload tracking file found. This appears to be a new migration.")
            logger.info("Upload tracking will be created to prevent duplicate uploads.")
            logger.info("")
            return False
    
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
    
    def retry_failed_uploads(self, use_sync_method: bool = False) -> Dict[Path, bool]:
        """
        Retry uploading files that previously failed.
        
        Args:
            use_sync_method: Whether to use Photos library sync method
            
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
        
        logger.info(f"Found {len(failed_data)} files to retry")
        
        # Setup uploader if needed
        if self.icloud_uploader is None:
            self.setup_icloud_uploader(use_sync_method=use_sync_method)
        
        # Group files by album
        files_by_album: Dict[str, List[Path]] = {}
        for file_data in failed_data.values():
            file_path = Path(file_data['file'])
            album_name = file_data.get('album', '')
            
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path}")
                continue
            
            if album_name not in files_by_album:
                files_by_album[album_name] = []
            files_by_album[album_name].append(file_path)
        
        # Upload files
        results = {}
        file_to_album = {}
        for album_name, files in files_by_album.items():
            for file_path in files:
                file_to_album[file_path] = album_name
        
        # Create verification failure callback
        def verification_failure_callback(failed_file_path: Path):
            """Callback for handling verification failures."""
            action = self._handle_verification_failure(failed_file_path)
            if action == 'stop':
                raise MigrationStoppedException(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
        
        all_files = [f for files in files_by_album.values() for f in files]
        
        if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
            results = self.icloud_uploader.upload_files_batch(
                all_files,
                albums=file_to_album,
                verify_after_upload=True,
                on_verification_failure=verification_failure_callback
            )
        else:
            # Group by album for regular uploader
            for album_name, files in files_by_album.items():
                logger.info(f"Retrying album: {album_name} ({len(files)} files)")
                album_results = self.icloud_uploader.upload_photos_batch(
                    files,
                    album_name=album_name,
                    verify_after_upload=True,
                    on_verification_failure=verification_failure_callback
                )
                results.update(album_results)
        
        # Update failed uploads file (remove successful ones)
        successful_files = {str(path) for path, success in results.items() if success}
        remaining_failed = {
            k: v for k, v in failed_data.items() 
            if k not in successful_files
        }
        
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
    
    def retry_failed_extractions(self) -> Dict[str, bool]:
        """
        Retry extracting zip files that previously failed extraction.
        
        Returns:
            Dictionary mapping zip names to extraction success status
        """
        logger.info("=" * 60)
        logger.info("Retrying failed extractions")
        logger.info("=" * 60)
        
        failed_zips = self.state_manager.get_zips_by_state(ZipProcessingState.FAILED_EXTRACTION)
        
        if not failed_zips:
            logger.info("No failed extractions to retry.")
            return {}
        
        logger.info(f"Found {len(failed_zips)} zip files with failed extractions")
        
        zip_dir = self.base_dir / self.config['processing']['zip_dir']
        results = {}
        
        for zip_name in failed_zips:
            zip_path = zip_dir / zip_name
            if not zip_path.exists():
                logger.warning(f"Zip file no longer exists: {zip_name}")
                continue
            
            logger.info(f"Retrying extraction: {zip_name}")
            try:
                extracted_dir = self.extractor.extract_zip(zip_path)
                self.state_manager.mark_zip_extracted(zip_name, str(extracted_dir))
                results[zip_name] = True
                logger.info(f"✓ Successfully extracted {zip_name}")
            except Exception as e:
                logger.error(f"Failed to extract {zip_name}: {e}")
                self.state_manager.mark_zip_failed(
                    zip_name,
                    ZipProcessingState.FAILED_EXTRACTION,
                    str(e)
                )
                results[zip_name] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Retried extractions: {successful}/{len(results)} succeeded")
        
        return results
    
    def retry_failed_conversions(self) -> Dict[str, bool]:
        """
        Retry converting files that previously failed conversion.
        
        Returns:
            Dictionary mapping file paths to conversion success status
        """
        logger.info("=" * 60)
        logger.info("Retrying failed conversions")
        logger.info("=" * 60)
        
        failed_files = self.state_manager.get_files_by_state(FileProcessingState.FAILED_CONVERSION)
        
        if not failed_files:
            logger.info("No failed conversions to retry.")
            return {}
        
        logger.info(f"Found {len(failed_files)} files with failed conversions")
        
        # Group files by zip
        files_by_zip: Dict[str, List[Path]] = {}
        for file_path_str in failed_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path}")
                continue
            
            file_state = self.state_manager._file_state.get(file_path_str, {})
            zip_name = file_state.get('zip_name', 'unknown')
            if zip_name not in files_by_zip:
                files_by_zip[zip_name] = []
            files_by_zip[zip_name].append(file_path)
        
        results = {}
        processed_dir = self.base_dir / self.config['processing']['processed_dir']
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        for zip_name, files in files_by_zip.items():
            logger.info(f"Retrying conversions for zip: {zip_name} ({len(files)} files)")
            
            # Need to find JSON metadata files for these files
            # For now, try to find JSON files in the same directory
            media_json_pairs = {}
            for file_path in files:
                json_path = file_path.with_suffix('.json')
                if json_path.exists():
                    media_json_pairs[file_path] = json_path
                else:
                    media_json_pairs[file_path] = None
            
            # Process metadata
            for file_path, json_path in media_json_pairs.items():
                try:
                    logger.debug(f"Retrying conversion: {file_path.name}")
                    processed_file = processed_dir / file_path.name
                    
                    # Copy file if needed
                    if not processed_file.exists():
                        import shutil
                        shutil.copy2(file_path, processed_file)
                    
                    # Merge metadata
                    self.metadata_merger.merge_metadata(processed_file, json_path)
                    self.state_manager.mark_file_converted(str(processed_file), zip_name)
                    results[str(file_path)] = True
                    logger.debug(f"✓ Successfully converted {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to convert {file_path.name}: {e}")
                    self.state_manager.mark_file_failed(
                        str(file_path),
                        zip_name,
                        FileProcessingState.FAILED_CONVERSION,
                        str(e)
                    )
                    results[str(file_path)] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Retried conversions: {successful}/{len(results)} succeeded")
        
        return results
    
    def retry_failed_photos_copies(self, use_sync_method: bool = False) -> Dict[Path, bool]:
        """
        Retry copying files to Photos library that previously failed.
        
        Args:
            use_sync_method: Whether to use Photos library sync method
            
        Returns:
            Dictionary mapping file paths to copy success status
        """
        logger.info("=" * 60)
        logger.info("Retrying failed Photos library copies")
        logger.info("=" * 60)
        
        failed_files = self.state_manager.get_files_by_state(FileProcessingState.FAILED_PHOTOS_COPY)
        
        if not failed_files:
            logger.info("No failed Photos copies to retry.")
            return {}
        
        logger.info(f"Found {len(failed_files)} files with failed Photos copies")
        
        # Setup uploader if needed
        if self.icloud_uploader is None:
            self.setup_icloud_uploader(use_sync_method=use_sync_method)
        
        if not isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
            logger.warning("Photos copy retry only works with sync method. Current uploader is not iCloudPhotosSyncUploader.")
            return {}
        
        # Group files by album
        files_by_album: Dict[str, List[Path]] = {}
        file_to_album = {}
        
        for file_path_str in failed_files:
            file_path = Path(file_path_str)
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path}")
                continue
            
            file_state = self.state_manager._file_state.get(file_path_str, {})
            album_name = file_state.get('album', '')
            file_to_album[file_path] = album_name
            
            if album_name not in files_by_album:
                files_by_album[album_name] = []
            files_by_album[album_name].append(file_path)
        
        # Upload files
        results = {}
        for album_name, files in files_by_album.items():
            display_name = album_name if album_name else '(no album)'
            logger.info(f"Retrying Photos copy for album: {display_name} ({len(files)} files)")
            
            for file_path in files:
                try:
                    logger.debug(f"Retrying Photos copy: {file_path.name}")
                    success = self.icloud_uploader.upload_file(file_path, album_name=album_name if album_name else None)
                    
                    if success:
                        file_state = self.state_manager._file_state.get(str(file_path), {})
                        zip_name = file_state.get('zip_name', 'unknown')
                        # Get asset identifier if available
                        asset_id = None
                        if hasattr(self.icloud_uploader, '_get_asset_identifier'):
                            asset_id = self.icloud_uploader._get_asset_identifier(file_path)
                        self.state_manager.mark_file_copied_to_photos(str(file_path), zip_name, asset_id)
                        results[file_path] = True
                        logger.debug(f"✓ Successfully copied {file_path.name} to Photos")
                    else:
                        file_state = self.state_manager._file_state.get(str(file_path), {})
                        zip_name = file_state.get('zip_name', 'unknown')
                        self.state_manager.mark_file_failed(
                            str(file_path),
                            zip_name,
                            FileProcessingState.FAILED_PHOTOS_COPY,
                            "Upload returned False"
                        )
                        results[file_path] = False
                except Exception as e:
                    logger.error(f"Failed to copy {file_path.name} to Photos: {e}")
                    file_state = self.state_manager._file_state.get(str(file_path), {})
                    zip_name = file_state.get('zip_name', 'unknown')
                    self.state_manager.mark_file_failed(
                        str(file_path),
                        zip_name,
                        FileProcessingState.FAILED_PHOTOS_COPY,
                        str(e)
                    )
                    results[file_path] = False
        
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Retried Photos copies: {successful}/{len(results)} succeeded")
        
        return results
    
    def _do_final_cleanup(self):
        """Perform final cleanup of processed files."""
        if self.config['processing'].get('cleanup_after_upload', False):
            logger.info("=" * 60)
            logger.info("Final cleanup")
            logger.info("=" * 60)
            processed_dir = self.base_dir / self.config['processing']['processed_dir']
            if processed_dir.exists():
                import shutil
                logger.info(f"Removing processed files: {processed_dir}")
                shutil.rmtree(processed_dir)
    
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
                           use_sync_method: bool = False, file_info: Optional[dict] = None) -> bool:
        """
        Process a single zip file: extract, process metadata, upload, cleanup.
        
        Args:
            zip_path: Path to zip file
            zip_number: Current zip number (for logging)
            total_zips: Total number of zip files
            use_sync_method: Whether to use Photos library sync method
            file_info: Optional Google Drive file metadata (for tracking corrupted files)
        
        Returns:
            True if successful, False otherwise
        """
        zip_name = zip_path.name
        try:
            logger.info("=" * 60)
            logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_name}")
            logger.info("=" * 60)
            
            # Check if zip is already complete
            if self.state_manager.is_zip_complete(zip_name):
                logger.info(f"⏭️  Skipping {zip_name} - already fully processed")
                return True
            
            # Set checkpoint
            self.state_manager.set_checkpoint('extract', zip_name=zip_name)
            
            # Extract this zip file
            # Check if already extracted
            extracted_dir = None
            if self.state_manager.is_zip_extracted(zip_name):
                zip_state = self.state_manager._zip_state.get(zip_name, {})
                extracted_dir_str = zip_state.get('extracted_dir')
                if extracted_dir_str and Path(extracted_dir_str).exists():
                    extracted_dir = Path(extracted_dir_str)
                    logger.info(f"⏭️  Zip {zip_name} already extracted, using existing extraction")
                else:
                    logger.info(f"Zip {zip_name} marked as extracted but directory missing, re-extracting")
            
            if extracted_dir is None:
                try:
                    logger.info(f"Extracting {zip_name}...")
                    extracted_dir = self.extractor.extract_zip(zip_path)
                    self.state_manager.mark_zip_extracted(zip_name, str(extracted_dir))
                    logger.info(f"✓ Extracted {zip_name}")
                except ExtractionError as e:
                    # Handle corrupted zip file - raise CorruptedZipException to stop and prompt user
                    error_msg = str(e)
                    file_size_mb = zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else None
                    
                    # Create minimal file_info if not provided
                    if not file_info:
                        file_info = {
                            'id': 'unknown',
                            'name': zip_path.name,
                            'size': str(zip_path.stat().st_size) if zip_path.exists() else '0'
                        }
                    
                    # Mark as failed extraction
                    self.state_manager.mark_zip_failed(
                        zip_name,
                        ZipProcessingState.FAILED_EXTRACTION,
                        error_msg
                    )
                    
                    # Raise CorruptedZipException to stop processing and show modal
                    raise CorruptedZipException(
                        error_msg,
                        str(zip_path),
                        file_info,
                        file_size_mb
                    ) from e
                except (zipfile.BadZipFile, RuntimeError) as e:
                    # Fallback for other zip errors
                    error_msg = str(e)
                    file_size_mb = zip_path.stat().st_size / (1024 * 1024) if zip_path.exists() else None
                    
                    if not file_info:
                        file_info = {
                            'id': 'unknown',
                            'name': zip_path.name,
                            'size': str(zip_path.stat().st_size) if zip_path.exists() else '0'
                        }
                    
                    # Mark as failed extraction
                    self.state_manager.mark_zip_failed(
                        zip_name,
                        ZipProcessingState.FAILED_EXTRACTION,
                        error_msg
                    )
                    
                    raise CorruptedZipException(
                        error_msg,
                        str(zip_path),
                        file_info,
                        file_size_mb
                    ) from e
            
            # Set checkpoint
            self.state_manager.set_checkpoint('convert', zip_name=zip_name)
            
            # Process metadata for this zip
            logger.info(f"Identifying media files in {zip_name}...")
            media_json_pairs = self.extractor.identify_media_json_pairs(extracted_dir)
            logger.info(f"Found {len(media_json_pairs)} media files in this zip")
            
            if not media_json_pairs:
                logger.warning(f"No media files found in {zip_name}, skipping")
                self.state_manager.mark_zip_uploaded(zip_name)  # Mark as complete (nothing to process)
                return True
            
            # Mark files as extracted
            for media_file in media_json_pairs.keys():
                self.state_manager.mark_file_extracted(str(media_file), zip_name)
            
            # Merge metadata
            processed_dir = self.base_dir / self.config['processing']['processed_dir']
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            # Process metadata in batches
            batch_size = self.config['processing']['batch_size']
            all_files = list(media_json_pairs.keys())
            
            # Check which files need conversion
            files_to_convert = []
            for media_file in all_files:
                processed_file = processed_dir / media_file.name
                file_state = self.state_manager.get_file_state(str(media_file))
                
                # Skip if already converted and processed file exists
                if file_state == FileProcessingState.CONVERTED.value and processed_file.exists():
                    logger.debug(f"⏭️  Skipping conversion for {media_file.name} - already converted")
                    continue
                
                files_to_convert.append(media_file)
            
            if files_to_convert:
                logger.info(f"Converting {len(files_to_convert)} files (skipping {len(all_files) - len(files_to_convert)} already converted)")
                
                for i in range(0, len(files_to_convert), batch_size):
                    batch = files_to_convert[i:i + batch_size]
                    batch_pairs = {f: media_json_pairs[f] for f in batch}
                    logger.info(f"Processing metadata batch {i // batch_size + 1}/{(len(files_to_convert) + batch_size - 1) // batch_size}")
                    
                    try:
                        self.metadata_merger.merge_all_metadata(batch_pairs, output_dir=processed_dir)
                        
                        # Mark files as converted
                        for media_file in batch:
                            processed_file = processed_dir / media_file.name
                            if processed_file.exists():
                                self.state_manager.mark_file_converted(str(processed_file), zip_name)
                            else:
                                # If processed file doesn't exist, mark original as converted
                                self.state_manager.mark_file_converted(str(media_file), zip_name)
                    except Exception as e:
                        logger.error(f"Error in metadata batch: {e}")
                        # Mark failed files
                        for media_file in batch:
                            self.state_manager.mark_file_failed(
                                str(media_file),
                                zip_name,
                                FileProcessingState.FAILED_CONVERSION,
                                str(e)
                            )
            else:
                logger.info(f"All files in {zip_name} already converted")
            
            # Mark zip as converted
            self.state_manager.mark_zip_converted(zip_name)
            
            # Set checkpoint
            self.state_manager.set_checkpoint('upload', zip_name=zip_name)
            
            # Parse albums for this zip
            parser = AlbumParser()
            parser.parse_from_directory_structure(extracted_dir)
            parser.parse_from_json_metadata(media_json_pairs)
            albums = parser.get_all_albums()
            
            # Upload files from this zip
            if self.icloud_uploader is None:
                self.setup_icloud_uploader(use_sync_method=use_sync_method)
            
            # Build file-to-album mapping from original files
            original_file_to_album = {}
            for album_name, files in albums.items():
                for file_path in files:
                    original_file_to_album[file_path] = album_name
            
            # Get processed files and build mapping from processed files to albums
            processed_files = []
            file_to_album = {}  # Maps processed/original file paths to album names
            for media_file in media_json_pairs.keys():
                processed_file = processed_dir / media_file.name
                if processed_file.exists():
                    processed_files.append(processed_file)
                    # Map processed file to album using original file's album
                    album_name = original_file_to_album.get(media_file, '')
                    if album_name:
                        file_to_album[processed_file] = album_name
                else:
                    processed_files.append(media_file)
                    # Map original file to album
                    album_name = original_file_to_album.get(media_file, '')
                    if album_name:
                        file_to_album[media_file] = album_name
            
            # Create verification failure callback
            def verification_failure_callback(failed_file_path: Path):
                """Callback for handling verification failures."""
                action = self._handle_verification_failure(failed_file_path)
                if action == 'stop':
                    raise RuntimeError(f"Migration stopped by user due to verification failure for {failed_file_path.name}")
            
            # Filter out files that are already uploaded
            files_to_upload = []
            for file_path in processed_files:
                file_state = self.state_manager.get_file_state(str(file_path))
                if file_state == FileProcessingState.SYNCED_TO_ICLOUD.value:
                    logger.debug(f"⏭️  Skipping {file_path.name} - already synced to iCloud")
                    continue
                files_to_upload.append(file_path)
            
            if not files_to_upload:
                logger.info(f"All files in {zip_name} already uploaded")
                self.state_manager.mark_zip_uploaded(zip_name)
                self.state_manager.clear_checkpoint()
                return True
            
            logger.info(f"Uploading {len(files_to_upload)} files from {zip_name} (skipping {len(processed_files) - len(files_to_upload)} already uploaded)")
            
            # Upload
            upload_results = {}
            if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
                logger.info(f"Copying {len(files_to_upload)} files to Photos library...")
                upload_results = self.icloud_uploader.upload_files_batch(
                    files_to_upload,
                    albums=file_to_album,
                    verify_after_upload=True,
                    on_verification_failure=verification_failure_callback
                )
            else:
                # Group by album using file_to_album mapping
                # Group processed files by album
                files_by_album = {}
                for file_path in files_to_upload:
                    album_name = file_to_album.get(file_path, '')
                    if album_name:
                        if album_name not in files_by_album:
                            files_by_album[album_name] = []
                        files_by_album[album_name].append(file_path)
                    else:
                        # Files without album go to default/root
                        if '' not in files_by_album:
                            files_by_album[''] = []
                        files_by_album[''].append(file_path)
                
                # Upload each album
                for album_name, files in files_by_album.items():
                    if files:
                        display_name = album_name if album_name else '(no album)'
                        logger.info(f"Uploading album: {display_name} ({len(files)} files)")
                        album_results = self.icloud_uploader.upload_photos_batch(
                            files,
                            album_name=album_name if album_name else None,
                            verify_after_upload=True,
                            on_verification_failure=verification_failure_callback
                        )
                        upload_results.update(album_results)
            
            # Update state for uploaded files
            for file_path, success in upload_results.items():
                if success:
                    if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
                        # For Photos sync, mark as copied to Photos
                        # Get asset identifier if available
                        asset_id = None
                        if hasattr(self.icloud_uploader, '_get_asset_identifier'):
                            try:
                                asset_id = self.icloud_uploader._get_asset_identifier(file_path)
                            except Exception:
                                pass
                        self.state_manager.mark_file_copied_to_photos(str(file_path), zip_name, asset_id)
                        # Also mark as synced (Photos will sync automatically)
                        self.state_manager.mark_file_synced_to_icloud(str(file_path), zip_name)
                    else:
                        # For API upload, mark as synced directly
                        self.state_manager.mark_file_synced_to_icloud(str(file_path), zip_name)
                else:
                    # Mark as failed upload
                    self.state_manager.mark_file_failed(
                        str(file_path),
                        zip_name,
                        FileProcessingState.FAILED_UPLOAD,
                        "Upload failed"
                    )
            
            successful = sum(1 for v in upload_results.values() if v)
            failed_count = len(upload_results) - successful
            logger.info(f"Uploaded {successful}/{len(upload_results)} files from {zip_name}")
            
            # Save failed uploads for retry
            if failed_count > 0:
                failed_files = [str(path) for path, success in upload_results.items() if not success]
                self._save_failed_uploads(failed_files, file_to_album)
                logger.warning(f"⚠️  {failed_count} files from {zip_name} failed to upload")
                logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
                # Don't delete zip file if there are failed uploads - keep it for retry
                logger.warning(f"⚠️  Keeping zip file {zip_name} for retry of failed uploads")
                # Don't mark zip as uploaded if there are failures
                return True  # Return True but don't delete zip
            
            # Mark zip as uploaded
            self.state_manager.mark_zip_uploaded(zip_name)
            self.state_manager.clear_checkpoint()
            
            # Cleanup extracted files for this zip (save disk space)
            import shutil
            if extracted_dir.exists():
                logger.info(f"Cleaning up extracted files for {zip_path.name}")
                shutil.rmtree(extracted_dir)
                logger.info(f"✓ Cleaned up extracted files for {zip_path.name}")
            
            logger.info(f"✓ Completed processing {zip_path.name}")
            return True
            
        except MigrationStoppedException:
            # Re-raise to stop migration
            raise
        except Exception as e:
            logger.error(f"Failed to process {zip_name}: {e}", exc_info=True)
            # Mark zip as failed (unknown step)
            self.state_manager.mark_zip_failed(
                zip_name,
                ZipProcessingState.FAILED_UPLOAD,
                str(e)
            )
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
        
        # Clear state
        self.state_manager.clear_state()
        logger.info("  ✓ Cleared state files")
        
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
        
        # Reset state flags
        self._skip_continue_prompts = False
        self.ignore_all_verification_failures = False
        
        logger.info("=" * 60)
        logger.info("✓ Cleanup complete - Ready to restart from scratch")
        logger.info("=" * 60)
        logger.info("")
    
    def _find_existing_zips(self, zip_dir: Path, zip_file_list: List[dict]) -> List[Path]:
        """
        Find zip files that are already downloaded locally.
        
        Args:
            zip_dir: Directory containing zip files
            zip_file_list: List of zip file metadata from Google Drive
        
        Returns:
            List of paths to existing zip files
        """
        existing_zips = []
        zip_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a set of expected zip file names for quick lookup
        expected_names = {file_info['name'] for file_info in zip_file_list}
        
        # Find matching zip files in the directory
        for zip_file in zip_dir.glob("*.zip"):
            if zip_file.name in expected_names:
                existing_zips.append(zip_file)
        
        return sorted(existing_zips)  # Sort for consistent processing order
    
    def run(self, use_sync_method: bool = False, retry_failed: bool = False):
        """
        Run the complete migration process.
        
        Args:
            use_sync_method: Whether to use Photos library sync method
            retry_failed: If True, only retry previously failed uploads
        """
        # If retry mode, just retry failed uploads and exit
        if retry_failed:
            self.setup_icloud_uploader(use_sync_method=use_sync_method)
            self.retry_failed_uploads(use_sync_method=use_sync_method)
            return
        
        try:
            # Phase 1: List all zip files (without downloading yet)
            logger.info("=" * 60)
            logger.info("Phase 1: Listing zip files from Google Drive")
            logger.info("=" * 60)
            
            drive_config = self.config['google_drive']
            zip_dir = self.base_dir / self.config['processing']['zip_dir']
            
            # List files without downloading
            zip_file_list = self.downloader.list_zip_files(
                folder_id=drive_config.get('folder_id') or None,
                pattern=drive_config.get('zip_file_pattern') or None
            )
            
            if not zip_file_list:
                logger.error("No zip files found. Exiting.")
                return
            
            # Check for already-downloaded zip files
            existing_zips = self._find_existing_zips(zip_dir, zip_file_list)
            
            if existing_zips:
                total_size_gb = sum(f.stat().st_size for f in existing_zips) / (1024 ** 3)
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
            
            # Setup iCloud uploader once (before processing zips)
            self.setup_icloud_uploader(use_sync_method=use_sync_method)
            
            # Create mapping from file name to file_info for looking up existing zips
            file_info_by_name = {file_info['name']: file_info for file_info in zip_file_list}
            
            successful = 0
            failed = 0
            total_zips = len(zip_file_list)
            processed_count = 0
            
            # FIRST: Process already-downloaded zip files to free up space
            for existing_zip in existing_zips:
                processed_count += 1
                try:
                    logger.info("=" * 60)
                    logger.info(f"Processing existing zip {processed_count}/{total_zips}: {existing_zip.name}")
                    logger.info("=" * 60)
                    
                    # Look up file_info for this existing zip
                    file_info = file_info_by_name.get(existing_zip.name)
                    
                    # Process this zip file
                    process_result = self.process_single_zip(existing_zip, processed_count, total_zips, use_sync_method, file_info=file_info)
                    
                    # Check if there are failed uploads for this zip
                    has_failed_uploads = self.failed_uploads_file.exists() and self.failed_uploads_file.stat().st_size > 0
                    if has_failed_uploads:
                        try:
                            with open(self.failed_uploads_file, 'r') as f:
                                failed_data = json.load(f)
                            # Check if any failed uploads are from this zip's extracted files
                            zip_has_failures = any(
                                str(existing_zip.name) in failed_file or 
                                any(existing_zip.stem in failed_file for failed_file in failed_data.keys())
                                for failed_file in failed_data.keys()
                            )
                            if zip_has_failures:
                                logger.warning(f"⚠️  Keeping zip file {existing_zip.name} due to failed uploads")
                                if process_result:
                                    successful += 1
                                else:
                                    failed += 1
                                continue  # Skip deletion
                        except Exception:
                            pass  # If we can't check, proceed normally
                    
                    if process_result:
                        successful += 1
                        
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
                            return
                        
                        # Check if restart was requested
                        if self._restart_requested:
                            self._restart_from_scratch()
                            self._restart_requested = False
                            logger.info("Restarting migration from scratch...")
                            # Recursively call run() to restart the entire process
                            return self.run(use_sync_method=use_sync_method, retry_failed=False)
                        
                except CorruptedZipException as e:
                    # Corrupted zip detected - stop and emit event for web UI
                    logger.error(f"❌ Corrupted zip file detected: {e.zip_path}")
                    logger.error(f"   Error: {e}")
                    
                    # Save to corrupted zips file
                    self._save_corrupted_zip(e.file_info, Path(e.zip_path), str(e))
                    
                    # Emit socket event for web UI (if available) and wait for redownload
                    try:
                        from web.app import socketio, migration_state
                        socketio.emit('corrupted_zip_detected', {
                            'zip_path': e.zip_path,
                            'file_name': e.file_info.get('name', Path(e.zip_path).name),
                            'file_id': e.file_info.get('id', 'unknown'),
                            'file_size_mb': e.file_size_mb,
                            'error_message': str(e)
                        })
                        # Set flag to wait for redownload
                        migration_state['waiting_for_corrupted_zip_redownload'] = True
                        migration_state['corrupted_zip_redownloaded'] = False
                        migration_state['skip_corrupted_zip'] = False  # Reset skip flag
                        
                        # Wait for redownload (up to 1 hour), but check for skip flag
                        max_wait = 3600
                        waited = 0
                        skipped = False
                        while not migration_state.get('corrupted_zip_redownloaded', False) and waited < max_wait:
                            # Check if user requested to skip this corrupted zip
                            if migration_state.get('skip_corrupted_zip', False):
                                logger.info(f"User requested to skip corrupted zip: {e.zip_path}")
                                migration_state['skip_corrupted_zip'] = False
                                migration_state['waiting_for_corrupted_zip_redownload'] = False
                                skipped = True
                                # In web UI mode, auto-skip continue prompts
                                import sys
                                if not sys.stdin.isatty():
                                    self._skip_continue_prompts = True
                                break
                            
                            time.sleep(1)
                            waited += 1
                            # Check stop flag
                            if hasattr(self, '_stop_requested') and self._stop_requested:
                                raise MigrationStoppedException("Migration stopped by user")
                        
                        # If we skipped or timed out, continue to next zip
                        if skipped or (waited >= max_wait and not migration_state.get('corrupted_zip_redownloaded', False)):
                            if waited >= max_wait and not skipped:
                                logger.warning("Timeout waiting for corrupted zip redownload. Skipping file.")
                            failed += 1
                            # In web UI mode, auto-skip continue prompts
                            import sys
                            if not sys.stdin.isatty():
                                self._skip_continue_prompts = True
                            continue
                        
                        # Reset flags
                        migration_state['waiting_for_corrupted_zip_redownload'] = False
                        migration_state['corrupted_zip_redownloaded'] = False
                        
                        # Try processing again
                        logger.info(f"Retrying processing of {e.zip_path} after redownload...")
                        process_result = self.process_single_zip(Path(e.zip_path), processed_count, total_zips, use_sync_method, file_info=e.file_info)
                        if process_result:
                            successful += 1
                        else:
                            failed += 1
                        # Skip continue prompt after retry in web UI mode
                        import sys
                        if not sys.stdin.isatty():
                            self._skip_continue_prompts = True
                        continue
                        
                    except (ImportError, AttributeError):
                        # Not in web UI mode - re-raise to stop processing
                        raise
                except MigrationStoppedException as e:
                    logger.info("Migration stopped by user.")
                    logger.info(f"Reason: {e}")
                    return
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {existing_zip.name}: {e}", exc_info=True)
                    logger.warning(f"Skipping remaining processing for {existing_zip.name}")
            
            # THEN: Download and process remaining zip files
            for file_info in zip_file_list:
                zip_file_path = zip_dir / file_info['name']
                
                # Skip if we already processed this file (or it failed)
                if zip_file_path.exists():
                    continue
                
                processed_count += 1
                try:
                    # Download this zip file
                    logger.info("=" * 60)
                    logger.info(f"Downloading zip {processed_count}/{total_zips}: {file_info['name']}")
                    logger.info("=" * 60)
                    
                    zip_file = self.downloader.download_single_zip(file_info, zip_dir)
                    
                    # Process this zip file (file_info is already available)
                    process_result = self.process_single_zip(zip_file, processed_count, total_zips, use_sync_method, file_info=file_info)
                    
                    # Check if there are failed uploads for this zip
                    has_failed_uploads = self.failed_uploads_file.exists() and self.failed_uploads_file.stat().st_size > 0
                    if has_failed_uploads:
                        try:
                            with open(self.failed_uploads_file, 'r') as f:
                                failed_data = json.load(f)
                            # Check if any failed uploads are from this zip's extracted files
                            zip_has_failures = any(
                                str(zip_file.name) in failed_file or 
                                any(zip_file.stem in failed_file for failed_file in failed_data.keys())
                                for failed_file in failed_data.keys()
                            )
                            if zip_has_failures:
                                logger.warning(f"⚠️  Keeping zip file {zip_file.name} due to failed uploads")
                                if process_result:
                                    successful += 1
                                else:
                                    failed += 1
                                continue  # Skip deletion
                        except Exception:
                            pass  # If we can't check, proceed normally
                    
                    if process_result:
                        successful += 1
                        
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
                            return
                        
                        # Check if restart was requested
                        if self._restart_requested:
                            self._restart_from_scratch()
                            self._restart_requested = False
                            logger.info("Restarting migration from scratch...")
                            # Recursively call run() to restart the entire process
                            return self.run(use_sync_method=use_sync_method, retry_failed=False)
                        
                except CorruptedZipException as e:
                    # Corrupted zip detected - stop and emit event for web UI
                    logger.error(f"❌ Corrupted zip file detected: {e.zip_path}")
                    logger.error(f"   Error: {e}")
                    
                    # Save to corrupted zips file
                    self._save_corrupted_zip(e.file_info, Path(e.zip_path), str(e))
                    
                    # Emit socket event for web UI (if available) and wait for redownload
                    try:
                        from web.app import socketio, migration_state
                        socketio.emit('corrupted_zip_detected', {
                            'zip_path': e.zip_path,
                            'file_name': e.file_info.get('name', Path(e.zip_path).name),
                            'file_id': e.file_info.get('id', 'unknown'),
                            'file_size_mb': e.file_size_mb,
                            'error_message': str(e)
                        })
                        # Set flag to wait for redownload
                        migration_state['waiting_for_corrupted_zip_redownload'] = True
                        migration_state['corrupted_zip_redownloaded'] = False
                        migration_state['skip_corrupted_zip'] = False  # Reset skip flag
                        
                        # Wait for redownload (up to 1 hour), but check for skip flag
                        max_wait = 3600
                        waited = 0
                        skipped = False
                        while not migration_state.get('corrupted_zip_redownloaded', False) and waited < max_wait:
                            # Check if user requested to skip this corrupted zip
                            if migration_state.get('skip_corrupted_zip', False):
                                logger.info(f"User requested to skip corrupted zip: {e.zip_path}")
                                migration_state['skip_corrupted_zip'] = False
                                migration_state['waiting_for_corrupted_zip_redownload'] = False
                                skipped = True
                                # In web UI mode, auto-skip continue prompts
                                import sys
                                if not sys.stdin.isatty():
                                    self._skip_continue_prompts = True
                                break
                            
                            time.sleep(1)
                            waited += 1
                            # Check stop flag
                            if hasattr(self, '_stop_requested') and self._stop_requested:
                                raise MigrationStoppedException("Migration stopped by user")
                        
                        # If we skipped or timed out, continue to next zip
                        if skipped or (waited >= max_wait and not migration_state.get('corrupted_zip_redownloaded', False)):
                            if waited >= max_wait and not skipped:
                                logger.warning("Timeout waiting for corrupted zip redownload. Skipping file.")
                            failed += 1
                            # In web UI mode, auto-skip continue prompts
                            import sys
                            if not sys.stdin.isatty():
                                self._skip_continue_prompts = True
                            continue
                        
                        # Reset flags
                        migration_state['waiting_for_corrupted_zip_redownload'] = False
                        migration_state['corrupted_zip_redownloaded'] = False
                        
                        # Try processing again
                        logger.info(f"Retrying processing of {e.zip_path} after redownload...")
                        process_result = self.process_single_zip(Path(e.zip_path), processed_count, total_zips, use_sync_method, file_info=e.file_info)
                        if process_result:
                            successful += 1
                        else:
                            failed += 1
                        # Skip continue prompt after retry in web UI mode
                        import sys
                        if not sys.stdin.isatty():
                            self._skip_continue_prompts = True
                        continue
                        
                    except (ImportError, AttributeError):
                        # Not in web UI mode - re-raise to stop processing
                        raise
                except MigrationStoppedException as e:
                    logger.info("Migration stopped by user.")
                    logger.info(f"Reason: {e}")
                    return
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing {file_info.get('name', 'unknown')}: {e}", exc_info=True)
                    logger.warning(f"Skipping remaining processing for {file_info.get('name', 'unknown')}")
            
            # Check for failed uploads before final cleanup
            failed_uploads_exist = self.failed_uploads_file.exists() and self.failed_uploads_file.stat().st_size > 0
            
            # If there are failed uploads, pause and ask user to retry
            if failed_uploads_exist:
                self._paused_for_retries = True
                # Set paused state in web UI if available
                try:
                    from web.app import migration_state
                    migration_state['paused_for_retries'] = True
                except ImportError:
                    pass  # Not in web UI mode
                
                logger.info("")
                logger.warning("=" * 60)
                logger.warning("⚠️  FAILED UPLOADS DETECTED")
                logger.warning("=" * 60)
                logger.warning("Some files failed to upload. The downloaded zip files have been kept")
                logger.warning("so you can retry the failed uploads.")
                logger.warning("")
                logger.warning("Please retry the failed uploads using the web UI or CLI:")
                logger.warning("  - Web UI: Use the 'Retry' buttons in the Failed Uploads section")
                logger.warning("  - CLI: python main.py --config <config> --retry-failed")
                logger.warning("")
                logger.warning("After retrying, you can proceed with cleanup.")
                logger.warning("=" * 60)
                
                # Wait for user to proceed (for web UI, this will be handled via API)
                proceed = self._ask_proceed_after_retries()
                if not proceed:
                    logger.info("Migration paused. Please retry failed uploads and then proceed.")
                    return
                
                # Re-check failed uploads after retries
                failed_uploads_exist = self.failed_uploads_file.exists() and self.failed_uploads_file.stat().st_size > 0
                if failed_uploads_exist:
                    logger.warning("⚠️  Some files still failed after retries. Proceeding with cleanup anyway.")
            
            # Final cleanup (will be done after pause if there are failed uploads)
            self._do_final_cleanup()
            
            # Check for corrupted zips
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
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retry previously failed uploads (skips download/extract/process steps)'
    )
    parser.add_argument(
        '--retry-failed-extractions',
        action='store_true',
        help='Retry only failed zip extractions'
    )
    parser.add_argument(
        '--retry-failed-conversions',
        action='store_true',
        help='Retry only failed file conversions'
    )
    parser.add_argument(
        '--retry-failed-photos-copies',
        action='store_true',
        help='Retry only failed Photos library copies (requires --use-sync)'
    )
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator(args.config)
    
    # Handle retry flags
    if args.retry_failed_extractions:
        orchestrator.retry_failed_extractions()
    elif args.retry_failed_conversions:
        orchestrator.retry_failed_conversions()
    elif args.retry_failed_photos_copies:
        if not args.use_sync:
            logger.error("--retry-failed-photos-copies requires --use-sync flag")
            return
        orchestrator.retry_failed_photos_copies(use_sync_method=True)
    else:
        orchestrator.run(use_sync_method=args.use_sync, retry_failed=args.retry_failed)


if __name__ == '__main__':
    main()

