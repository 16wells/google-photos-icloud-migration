"""
Google Drive API integration for downloading Google Takeout zip files.
"""
import os
import json
from pathlib import Path
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
import logging

logger = logging.getLogger(__name__)

# Scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class DriveDownloader:
    """Handles downloading files from Google Drive."""
    
    def __init__(self, credentials_file: str):
        """
        Initialize the Drive downloader.
        
        Args:
            credentials_file: Path to Google Drive API credentials JSON file
        """
        self.credentials_file = credentials_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None
        token_file = 'token.json'
        
        # Load existing token if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                
                # Check if we're in a headless environment (no DISPLAY)
                # Use manual authorization for headless environments
                if os.environ.get('DISPLAY') is None or not self._can_open_browser():
                    logger.info("=" * 60)
                    logger.info("Running in headless mode - Manual authorization required")
                    logger.info("=" * 60)
                    # Use out-of-band redirect URI for headless/console mode
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    logger.info("")
                    logger.info("Please visit this URL to authorize the application:")
                    logger.info("")
                    logger.info(auth_url)
                    logger.info("")
                    logger.info("After authorizing, you will see a code.")
                    logger.info("Copy that code and paste it here:")
                    logger.info("")
                    code = input("Enter the authorization code: ").strip()
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                else:
                    creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully authenticated with Google Drive API")
    
    def _can_open_browser(self):
        """Check if we can open a browser."""
        try:
            import webbrowser
            browser = webbrowser.get()
            return browser is not None
        except:
            return False
    
    def list_zip_files(self, folder_id: Optional[str] = None, 
                       pattern: Optional[str] = None) -> List[dict]:
        """
        List zip files in Google Drive.
        
        Args:
            folder_id: Optional folder ID to search in
            pattern: Optional file name pattern (e.g., "takeout-*.zip")
        
        Returns:
            List of file metadata dictionaries
        """
        query = "mimeType='application/zip' or mimeType='application/x-zip-compressed'"
        
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        if pattern:
            # Convert pattern to Drive query format
            # Remove wildcards and use contains
            pattern_clean = pattern.replace('*', '').replace('.zip', '')
            query += f" and name contains '{pattern_clean}'"
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name, size, modifiedTime)",
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"Found {len(files)} zip files in Google Drive")
        
        return files
    
    def download_file(self, file_id: str, file_name: str, 
                     destination_dir: Path) -> Path:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            destination_dir: Directory to save the file
        
        Returns:
            Path to downloaded file
        """
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = destination_dir / file_name
        
        # Skip if file already exists
        if destination_path.exists():
            logger.info(f"File {file_name} already exists, skipping download")
            return destination_path
        
        logger.info(f"Downloading {file_name}...")
        
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")
        
        logger.info(f"Downloaded {file_name} ({destination_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return destination_path
    
    def download_all_zips(self, destination_dir: Path, 
                         folder_id: Optional[str] = None,
                         pattern: Optional[str] = None) -> List[Path]:
        """
        Download all zip files matching criteria.
        
        Args:
            destination_dir: Directory to save zip files
            folder_id: Optional folder ID to search in
            pattern: Optional file name pattern
        
        Returns:
            List of paths to downloaded files
        """
        files = self.list_zip_files(folder_id=folder_id, pattern=pattern)
        downloaded_files = []
        
        for file_info in files:
            file_path = self.download_file(
                file_info['id'],
                file_info['name'],
                destination_dir
            )
            downloaded_files.append(file_path)
        
        logger.info(f"Downloaded {len(downloaded_files)} zip files")
        return downloaded_files

