"""
Main orchestration script for Google Photos to iCloud Photos migration.
"""
import argparse
import json
import logging
import os
import sys
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

from drive_downloader import DriveDownloader
from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser
from icloud_uploader import iCloudUploader, iCloudPhotosSyncUploader
from exceptions import ConfigurationError
from config import MigrationConfig

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
        
        # Verification failure handling
        self.ignore_all_verification_failures = False
        
        # Continue prompt handling
        self._skip_continue_prompts = False
        self._restart_requested = False
    
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
        """Set up logging configuration."""
        log_config = self.config.get('logging', {})
        level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'migration.log')
        
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
            # Get photos library path from config if specified
            photos_library_path = icloud_config.get('photos_library_path')
            if photos_library_path:
                photos_library_path = Path(photos_library_path).expanduser()
            self.icloud_uploader = iCloudPhotosSyncUploader(photos_library_path=photos_library_path)
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
                two_fa_code=icloud_config.get('two_fa_code')  # Support 2FA code from config or env var
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
        try:
            logger.info("=" * 60)
            logger.info(f"Processing zip {zip_number}/{total_zips}: {zip_path.name}")
            logger.info("=" * 60)
            
            # Extract this zip file
            try:
                extracted_dir = self.extractor.extract_zip(zip_path)
            except (zipfile.BadZipFile, RuntimeError) as e:
                # Handle corrupted zip file (BadZipFile from extractor, RuntimeError from validation)
                error_msg = str(e)
                logger.error(f"❌ Corrupted zip file detected: {zip_path.name}")
                logger.error(f"   Error: {error_msg}")
                
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
                
                logger.warning(f"⚠️  Skipping corrupted zip file: {zip_path.name}")
                logger.warning(f"   This file has been saved to corrupted_zips.json for later re-download")
                return False
            
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
            
            # Upload
            if isinstance(self.icloud_uploader, iCloudPhotosSyncUploader):
                upload_results = self.icloud_uploader.upload_files_batch(
                    processed_files,
                    albums=file_to_album,
                    verify_after_upload=True,
                    on_verification_failure=verification_failure_callback
                )
            else:
                # Group by album using file_to_album mapping
                upload_results = {}
                # Group processed files by album
                files_by_album = {}
                for file_path in processed_files:
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
            
            successful = sum(1 for v in upload_results.values() if v)
            failed_count = len(upload_results) - successful
            logger.info(f"Uploaded {successful}/{len(upload_results)} files from {zip_path.name}")
            
            # Save failed uploads for retry
            if failed_count > 0:
                failed_files = [str(path) for path, success in upload_results.items() if not success]
                self._save_failed_uploads(failed_files, file_to_album)
                logger.warning(f"⚠️  {failed_count} files from {zip_path.name} failed to upload")
                logger.warning(f"Failed uploads saved to: {self.failed_uploads_file}")
            
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
            logger.error(f"Failed to process {zip_path.name}: {e}", exc_info=True)
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
                    if self.process_single_zip(existing_zip, processed_count, total_zips, use_sync_method, file_info=file_info):
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
                    if self.process_single_zip(zip_file, processed_count, total_zips, use_sync_method, file_info=file_info):
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
                        
                except MigrationStoppedException as e:
                    logger.info("Migration stopped by user.")
                    logger.info(f"Reason: {e}")
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
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator(args.config)
    orchestrator.run(use_sync_method=args.use_sync, retry_failed=args.retry_failed)


if __name__ == '__main__':
    main()

