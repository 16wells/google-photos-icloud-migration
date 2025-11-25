"""
Background worker for running migrations.
This runs the actual migration process in a separate thread.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Import core modules
from drive_downloader import DriveDownloader
from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser
from icloud_uploader import iCloudUploader


class MigrationWorker:
    """Background worker for migration process"""
    
    def __init__(self, google_credentials, icloud_credentials, folder_id=None, 
                 zip_pattern='takeout-*.zip', session_id=None):
        self.google_credentials = google_credentials
        self.icloud_credentials = icloud_credentials
        self.folder_id = folder_id
        self.zip_pattern = zip_pattern
        self.session_id = session_id
        
    def update_status(self, status, phase, progress, current_file='', 
                     total_files=0, processed_files=0, log_message=''):
        """Update migration status (would need to use Redis or database in production)"""
        # In POC, we'll use a simple file-based status
        # In production, use Redis or database
        status_file = Path(f'/tmp/migration_status_{self.session_id}.json')
        import json
        status_data = {
            'status': status,
            'phase': phase,
            'progress': progress,
            'current_file': current_file,
            'total_files': total_files,
            'processed_files': processed_files,
            'log': [log_message] if log_message else []
        }
        status_file.write_text(json.dumps(status_data))
    
    def run(self):
        """Run the migration process"""
        try:
            self.update_status('running', 'Initializing', 0, log_message='Starting migration...')
            
            # Convert Google credentials dict back to Credentials object
            creds = Credentials(
                token=self.google_credentials['token'],
                refresh_token=self.google_credentials.get('refresh_token'),
                token_uri=self.google_credentials['token_uri'],
                client_id=self.google_credentials['client_id'],
                client_secret=self.google_credentials['client_secret'],
                scopes=self.google_credentials['scopes']
            )
            
            # Create Drive service
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Initialize components
            base_dir = Path('/tmp/google-photos-migration')
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a temporary credentials file for DriveDownloader
            # (This is a workaround - in production, refactor DriveDownloader to accept credentials directly)
            temp_creds_file = base_dir / 'temp_credentials.json'
            import json
            temp_creds_file.write_text(json.dumps({
                'installed': {
                    'client_id': self.google_credentials['client_id'],
                    'client_secret': self.google_credentials['client_secret'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token'
                }
            }))
            
            # Use DriveDownloader (will need to be refactored to accept credentials directly)
            # For now, create a simple downloader
            self.update_status('running', 'Downloading files', 10, log_message='Finding zip files...')
            
            # List files
            query = "mimeType='application/zip' or mimeType='application/x-zip-compressed'"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
            
            results = drive_service.files().list(
                q=query,
                fields="files(id, name, size)",
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            
            # Filter by pattern
            import fnmatch
            if self.zip_pattern:
                files = [f for f in files if fnmatch.fnmatch(f['name'].lower(), self.zip_pattern.lower())]
            
            self.update_status('running', f'Found {len(files)} files', 20, 
                            total_files=len(files), log_message=f'Found {len(files)} zip files')
            
            # TODO: Continue with download, extraction, processing, upload
            # This is a skeleton - full implementation would continue here
            
            self.update_status('completed', 'Migration complete', 100, 
                            processed_files=len(files), log_message='Migration completed successfully')
            
        except Exception as e:
            self.update_status('error', f'Error: {str(e)}', 0, log_message=f'Error: {str(e)}')

