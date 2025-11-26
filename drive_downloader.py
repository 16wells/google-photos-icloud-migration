"""
Google Drive API integration for downloading Google Takeout zip files.
"""
import os
import json
import shutil
import time
from pathlib import Path
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import io
import logging

from exceptions import DownloadError, AuthenticationError

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
                
                # Check if we're in a headless environment
                # Use manual authorization for headless environments
                if self._is_headless_environment():
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
        import sys
        try:
            import webbrowser
            # On macOS, browsers work without DISPLAY variable
            if sys.platform == 'darwin':
                return True
            browser = webbrowser.get()
            return browser is not None
        except Exception:
            return False
    
    def _is_headless_environment(self):
        """Check if we're running in a headless environment."""
        import sys
        
        # macOS always has a display (unless SSH without forwarding)
        if sys.platform == 'darwin':
            # Check if we're in an SSH session without display
            if os.environ.get('SSH_CLIENT') and not os.environ.get('DISPLAY'):
                return True
            return False
        
        # Linux: check DISPLAY variable
        if sys.platform.startswith('linux'):
            return os.environ.get('DISPLAY') is None
        
        # Windows typically has display
        if sys.platform == 'win32':
            return False
        
        # Default: try browser check
        return not self._can_open_browser()
    
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
        import time
        from googleapiclient.errors import HttpError
        
        query = "mimeType='application/zip' or mimeType='application/x-zip-compressed'"
        
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        # Retry logic for handling API errors
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name, size, modifiedTime)",
                    pageSize=1000
                ).execute()
                break
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504) and attempt < max_retries - 1:
                    # Server errors - retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Google Drive API returned {e.resp.status} error. "
                        f"Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                elif e.resp.status == 500 and folder_id:
                    # If folder_id query fails, try without folder_id
                    logger.warning("Query with folder_id failed. Trying without folder filter...")
                    query = "mimeType='application/zip' or mimeType='application/x-zip-compressed'"
                    try:
                        results = self.service.files().list(
                            q=query,
                            fields="files(id, name, size, modifiedTime)",
                            pageSize=1000
                        ).execute()
                        break
                    except HttpError as e2:
                        raise DownloadError(
                            f"Failed to list files from Google Drive: HTTP {e2.resp.status} - {e2}"
                        ) from e2
                elif e.resp.status == 401:
                    raise AuthenticationError(
                        "Google Drive API authentication failed. "
                        "Please re-authenticate by deleting token.json and running again."
                    ) from e
                else:
                    raise DownloadError(
                        f"Failed to list zip files from Google Drive: HTTP {e.resp.status} - {e}"
                    ) from e
        
        all_files = results.get('files', [])
        
        # Handle pagination if there are more than 1000 files
        while 'nextPageToken' in results:
            try:
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name, size, modifiedTime)",
                    pageSize=1000,
                    pageToken=results['nextPageToken']
                ).execute()
                all_files.extend(results.get('files', []))
            except HttpError as e:
                logger.warning(
                    f"Error fetching next page of results: HTTP {e.resp.status} - {e}. "
                    f"Continuing with {len(all_files)} files fetched so far."
                )
                break
        
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
                size = file_info.get('size', '0')
                # Convert size to int (Google Drive API returns it as string)
                try:
                    size_mb = int(size) / 1024 / 1024
                    logger.info(f"  - {file_info.get('name')} ({size_mb:.1f} MB)")
                except (ValueError, TypeError):
                    logger.info(f"  - {file_info.get('name')} (size unknown)")
            if len(files) > 10:
                logger.info(f"  ... and {len(files) - 10} more files")
        
        return files
    
    def _check_disk_space(self, path: Path, required_bytes: int, 
                         buffer_percent: float = 0.1) -> bool:
        """
        Check if there's enough disk space available.
        
        Args:
            path: Path to check disk space for
            required_bytes: Required bytes
            buffer_percent: Additional buffer percentage (default 10%)
        
        Returns:
            True if enough space, False otherwise
        """
        stat = shutil.disk_usage(path)
        available_bytes = stat.free
        required_with_buffer = int(required_bytes * (1 + buffer_percent))
        
        if available_bytes < required_with_buffer:
            available_gb = available_bytes / (1024 ** 3)
            required_gb = required_with_buffer / (1024 ** 3)
            logger.error(
                f"Insufficient disk space: {available_gb:.2f} GB available, "
                f"{required_gb:.2f} GB required (with {buffer_percent*100:.0f}% buffer)"
            )
            return False
        
        return True
    
    def download_file(self, file_id: str, file_name: str, 
                     destination_dir: Path, file_size: Optional[int] = None) -> Path:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            destination_dir: Directory to save the file
            file_size: Optional file size in bytes (for disk space checking)
        
        Returns:
            Path to downloaded file
        """
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = destination_dir / file_name
        
        # Skip if file already exists
        if destination_path.exists():
            logger.info(f"File {file_name} already exists, skipping download")
            return destination_path
        
        # Check disk space before downloading
        if file_size:
            if not self._check_disk_space(destination_dir, file_size):
                raise DownloadError(
                    f"Insufficient disk space to download {file_name} "
                    f"({file_size / (1024**3):.2f} GB). "
                    f"Please free up disk space and try again."
                )
        
        logger.info(f"Downloading {file_name}...")
        
        # Retry logic for downloads with exponential backoff
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
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
                
            except HttpError as e:
                if attempt < max_retries - 1 and e.resp.status in (500, 502, 503, 504):
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Download failed for {file_name} (attempt {attempt + 1}/{max_retries}): "
                        f"HTTP {e.resp.status}. Retrying in {wait_time:.1f} seconds..."
                    )
                    time.sleep(wait_time)
                    # Remove partial file if it exists
                    if destination_path.exists():
                        destination_path.unlink()
                    continue
                else:
                    raise DownloadError(
                        f"Failed to download {file_name} from Google Drive: HTTP {e.resp.status} - {e}"
                    ) from e
            except (OSError, IOError) as e:
                raise DownloadError(
                    f"Failed to save {file_name} to disk: {e}. "
                    f"Check disk space and file permissions."
                ) from e
            except Exception as e:
                raise DownloadError(
                    f"Unexpected error downloading {file_name}: {e}"
                ) from e
    
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
            file_size = None
            if 'size' in file_info:
                try:
                    file_size = int(file_info['size'])
                except (ValueError, TypeError):
                    pass
            
            file_path = self.download_file(
                file_info['id'],
                file_info['name'],
                destination_dir,
                file_size=file_size
            )
            downloaded_files.append(file_path)
        
        logger.info(f"Downloaded {len(downloaded_files)} zip files")
        return downloaded_files
    
    def download_single_zip(self, file_info: dict, destination_dir: Path) -> Path:
        """
        Download a single zip file.
        
        Args:
            file_info: File metadata dictionary with 'id', 'name', and optionally 'size'
            destination_dir: Directory to save zip file
        
        Returns:
            Path to downloaded file
        """
        file_size = None
        if 'size' in file_info:
            try:
                file_size = int(file_info['size'])
            except (ValueError, TypeError):
                pass
        
        return self.download_file(
            file_info['id'],
            file_info['name'],
            destination_dir,
            file_size=file_size
        )

