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
                    # For Desktop apps, use localhost redirect but handle manually
                    # Set redirect_uri to localhost (works with Desktop app OAuth clients)
                    flow.redirect_uri = 'http://localhost:8080/'
                    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                    logger.info("")
                    logger.info("Please visit this URL to authorize the application:")
                    logger.info("")
                    logger.info(auth_url)
                    logger.info("")
                    logger.info("After authorizing, Google will try to redirect to localhost.")
                    logger.info("Since localhost won't work, look for the 'code' parameter in the URL.")
                    logger.info("The URL will look like: http://localhost:8080/?code=XXXXX&scope=...")
                    logger.info("")
                    logger.info("Copy the ENTIRE redirect URL and paste it here:")
                    logger.info("")
                    authorization_response = input("Enter the authorization response URL: ").strip()
                    # Extract code from URL
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(authorization_response)
                    params = parse_qs(parsed.query)
                    if 'code' in params:
                        code = params['code'][0]
                        logger.info("Extracted authorization code, fetching token...")
                        flow.fetch_token(code=code)
                    else:
                        # Try as-is if it's already just a code
                        flow.fetch_token(code=authorization_response)
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
        
        results = self.service.files().list(
            q=query,
            fields="files(id, name, size, modifiedTime)",
            pageSize=1000
        ).execute()
        
        all_files = results.get('files', [])
        
        # Filter by pattern if provided (do this in Python for better pattern matching)
        if pattern:
            import fnmatch
            filtered_files = []
            for file_info in all_files:
                file_name = file_info.get('name', '')
                # Use fnmatch for proper wildcard matching
                if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                    filtered_files.append(file_info)
            files = filtered_files
            logger.info(f"Found {len(files)} zip files matching pattern '{pattern}' (out of {len(all_files)} total zip files)")
        else:
            files = all_files
            logger.info(f"Found {len(files)} zip files in Google Drive")
        
        # Log file names for debugging
        if files:
            logger.info("Files to download:")
            for file_info in files[:10]:  # Show first 10
                logger.info(f"  - {file_info.get('name')} ({file_info.get('size', 0) / 1024 / 1024:.1f} MB)")
            if len(files) > 10:
                logger.info(f"  ... and {len(files) - 10} more files")
        
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

