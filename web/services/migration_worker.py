"""
Background worker for running migrations.
This runs the actual migration process in a separate thread.
"""
import sys
import os
import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import fnmatch

# Import core modules
from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser
from icloud_uploader import iCloudUploader

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationWorker:
    """Background worker for migration process"""
    
    def __init__(self, google_credentials, icloud_credentials, folder_id=None, 
                 zip_pattern='takeout-*.zip', session_id=None):
        self.google_credentials = google_credentials
        self.icloud_credentials = icloud_credentials
        self.folder_id = folder_id
        self.zip_pattern = zip_pattern
        self.session_id = session_id
        self.base_dir = Path('/tmp/google-photos-migration')
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize status file path
        self.status_file = Path(f'/tmp/migration_status_{self.session_id}.json')
        self._init_status()
        
    def _init_status(self):
        """Initialize status file"""
        initial_status = {
            'status': 'idle',
            'phase': 'Not started',
            'progress': 0,
            'current_file': '',
            'total_files': 0,
            'processed_files': 0,
            'log': []
        }
        self.status_file.write_text(json.dumps(initial_status))
        
    def update_status(self, status, phase, progress, current_file='', 
                     total_files=0, processed_files=0, log_message=''):
        """Update migration status"""
        try:
            # Load existing status
            if self.status_file.exists():
                existing = json.loads(self.status_file.read_text())
                log = existing.get('log', [])
            else:
                log = []
            
            # Add new log message
            if log_message:
                log.append(log_message)
                # Keep only last 100 log entries
                log = log[-100:]
            
            status_data = {
                'status': status,
                'phase': phase,
                'progress': progress,
                'current_file': current_file,
                'total_files': total_files,
                'processed_files': processed_files,
                'log': log
            }
            self.status_file.write_text(json.dumps(status_data, indent=2))
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
    
    def _create_drive_service(self):
        """Create Google Drive service from credentials"""
        creds = Credentials(
            token=self.google_credentials['token'],
            refresh_token=self.google_credentials.get('refresh_token'),
            token_uri=self.google_credentials['token_uri'],
            client_id=self.google_credentials['client_id'],
            client_secret=self.google_credentials['client_secret'],
            scopes=self.google_credentials['scopes']
        )
        
        # Refresh token if needed
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        
        return build('drive', 'v3', credentials=creds)
    
    def _download_zip_files(self, drive_service) -> List[Path]:
        """Download zip files from Google Drive"""
        self.update_status('running', 'Finding zip files', 5, log_message='Searching Google Drive...')
        
        # Build query
        query = "mimeType='application/zip' or mimeType='application/x-zip-compressed'"
        if self.folder_id:
            query += f" and '{self.folder_id}' in parents"
        
        # List files
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, size)",
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        
        # Filter by pattern
        if self.zip_pattern:
            files = [f for f in files if fnmatch.fnmatch(f['name'].lower(), self.zip_pattern.lower())]
        
        if not files:
            raise Exception("No zip files found matching the criteria")
        
        self.update_status('running', f'Found {len(files)} zip files', 10, 
                          total_files=len(files), log_message=f'Found {len(files)} zip files to download')
        
        # Download files
        zip_dir = self.base_dir / 'zips'
        zip_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files = []
        
        for i, file_info in enumerate(files):
            file_id = file_info['id']
            file_name = file_info['name']
            destination_path = zip_dir / file_name
            
            # Skip if already downloaded
            if destination_path.exists():
                self.update_status('running', f'Downloading ({i+1}/{len(files)})', 
                                10 + int((i+1) / len(files) * 20),
                                current_file=file_name, log_message=f'Skipping {file_name} (already exists)')
                downloaded_files.append(destination_path)
                continue
            
            self.update_status('running', f'Downloading ({i+1}/{len(files)})', 
                            10 + int((i+1) / len(files) * 20),
                            current_file=file_name, log_message=f'Downloading {file_name}...')
            
            # Download file
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(destination_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            downloaded_files.append(destination_path)
            self.update_status('running', f'Downloading ({i+1}/{len(files)})', 
                            10 + int((i+1) / len(files) * 20),
                            current_file=file_name, log_message=f'Downloaded {file_name}')
        
        return downloaded_files
    
    def run(self):
        """Run the migration process"""
        try:
            self.update_status('running', 'Initializing', 0, log_message='Starting migration...')
            
            # Create Drive service
            drive_service = self._create_drive_service()
            
            # Download zip files
            zip_files = self._download_zip_files(drive_service)
            
            if not zip_files:
                raise Exception("No zip files downloaded")
            
            # Initialize components
            extractor = Extractor(self.base_dir)
            metadata_merger = MetadataMerger(
                preserve_dates=True,
                preserve_gps=True,
                preserve_descriptions=True
            )
            album_parser = AlbumParser()
            
            # Initialize iCloud uploader
            self.update_status('running', 'Connecting to iCloud', 30, log_message='Authenticating with iCloud...')
            try:
                icloud_uploader = iCloudUploader(
                    apple_id=self.icloud_credentials['apple_id'],
                    password=self.icloud_credentials['password'],
                    trusted_device_id=None  # 2FA should already be handled in web interface
                )
            except Exception as e:
                # If authentication fails, it might need 2FA again
                # For POC, we'll raise an error - in production, handle this better
                raise Exception(f"iCloud authentication failed. Please ensure 2FA is completed: {str(e)}")
            
            processed_dir = self.base_dir / 'processed'
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            total_processed = 0
            
            # Process each zip file
            for zip_idx, zip_file in enumerate(zip_files):
                zip_number = zip_idx + 1
                total_zips = len(zip_files)
                
                self.update_status('running', f'Processing zip {zip_number}/{total_zips}', 
                                30 + int(zip_idx / total_zips * 60),
                                current_file=zip_file.name, 
                                log_message=f'Processing {zip_file.name}...')
                
                try:
                    # Extract zip
                    self.update_status('running', f'Extracting {zip_file.name}', 
                                    30 + int(zip_idx / total_zips * 60),
                                    current_file=zip_file.name, 
                                    log_message=f'Extracting {zip_file.name}...')
                    extracted_dir = extractor.extract_zip(zip_file)
                    
                    # Find media files
                    media_json_pairs = extractor.identify_media_json_pairs(extracted_dir)
                    
                    if not media_json_pairs:
                        logger.warning(f"No media files found in {zip_file.name}")
                        self.update_status('running', f'Processing zip {zip_number}/{total_zips}', 
                                        30 + int(zip_idx / total_zips * 60),
                                        log_message=f'No media files in {zip_file.name}, skipping')
                        continue
                    
                    # Process metadata
                    self.update_status('running', f'Processing metadata ({zip_number}/{total_zips})', 
                                    30 + int(zip_idx / total_zips * 60),
                                    log_message=f'Processing metadata for {len(media_json_pairs)} files...')
                    
                    # Process in batches
                    batch_size = 100
                    all_files = list(media_json_pairs.keys())
                    
                    for batch_idx in range(0, len(all_files), batch_size):
                        batch = all_files[batch_idx:batch_idx + batch_size]
                        batch_pairs = {f: media_json_pairs[f] for f in batch}
                        metadata_merger.merge_all_metadata(batch_pairs, output_dir=processed_dir)
                    
                    # Parse albums
                    album_parser.parse_from_directory_structure(extracted_dir)
                    album_parser.parse_from_json_metadata(media_json_pairs)
                    albums = album_parser.get_all_albums()
                    
                    # Get processed files
                    processed_files = []
                    for media_file in media_json_pairs.keys():
                        processed_file = processed_dir / media_file.name
                        if processed_file.exists():
                            processed_files.append(processed_file)
                        else:
                            processed_files.append(media_file)
                    
                    # Upload files
                    self.update_status('running', f'Uploading ({zip_number}/{total_zips})', 
                                    30 + int(zip_idx / total_zips * 60),
                                    log_message=f'Uploading {len(processed_files)} files to iCloud...')
                    
                    # Group by album
                    file_to_album = {}
                    for album_name, files in albums.items():
                        for file_path in files:
                            file_to_album[file_path] = album_name
                    
                    upload_results = {}
                    for album_name, files in albums.items():
                        # Map to processed files
                        processed_album_files = [
                            f for f in processed_files 
                            if file_to_album.get(f, '') == album_name
                        ]
                        if processed_album_files:
                            logger.info(f"Uploading album: {album_name} ({len(processed_album_files)} files)")
                            album_results = icloud_uploader.upload_photos_batch(
                                processed_album_files,
                                album_name=album_name
                            )
                            upload_results.update(album_results)
                    
                    successful = sum(1 for v in upload_results.values() if v)
                    total_processed += successful
                    
                    self.update_status('running', f'Completed zip {zip_number}/{total_zips}', 
                                    30 + int((zip_idx + 1) / total_zips * 60),
                                    processed_files=total_processed,
                                    log_message=f'Uploaded {successful}/{len(upload_results)} files from {zip_file.name}')
                    
                    # Cleanup extracted files
                    if extracted_dir.exists():
                        shutil.rmtree(extracted_dir)
                    
                except Exception as e:
                    logger.error(f"Error processing {zip_file.name}: {e}", exc_info=True)
                    self.update_status('running', f'Error in {zip_file.name}', 
                                    30 + int(zip_idx / total_zips * 60),
                                    log_message=f'Error processing {zip_file.name}: {str(e)}')
                    continue
            
            # Final cleanup
            if processed_dir.exists():
                shutil.rmtree(processed_dir)
            
            self.update_status('completed', 'Migration complete', 100, 
                            processed_files=total_processed, 
                            log_message=f'Migration completed successfully! Processed {total_processed} files.')
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            self.update_status('error', f'Error: {str(e)}', 0, log_message=f'Migration failed: {str(e)}')

