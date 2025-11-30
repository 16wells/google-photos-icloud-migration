"""
Google Drive API integration for downloading Google Takeout zip files.
"""
import os
import json
import shutil
import time
import socket
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
import httplib2
import requests

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
                try:
                    creds.refresh(Request())
                except (socket.gaierror, OSError, requests.exceptions.ConnectionError) as e:
                    self._handle_network_error(e, "refreshing authentication token")
                except Exception as e:
                    # Check if it's a network-related error from requests/urllib3
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ['connection', 'dns', 'resolve', 'network', 'timeout']):
                        self._handle_network_error(e, "refreshing authentication token")
                    else:
                        # Re-raise other exceptions (e.g., authentication errors)
                        raise
            else:
                try:
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
                            try:
                                flow.fetch_token(code=code)
                            except (socket.gaierror, OSError, requests.exceptions.ConnectionError) as e:
                                self._handle_network_error(e, "fetching OAuth token")
                                raise
                        else:
                            # Try as-is if it's already just a code
                            try:
                                flow.fetch_token(code=authorization_response)
                            except (socket.gaierror, OSError, requests.exceptions.ConnectionError) as e:
                                self._handle_network_error(e, "fetching OAuth token")
                                raise
                        creds = flow.credentials
                    else:
                        try:
                            creds = flow.run_local_server(port=0)
                        except (socket.gaierror, OSError, requests.exceptions.ConnectionError) as e:
                            self._handle_network_error(e, "running OAuth local server")
                            raise
                except (socket.gaierror, OSError) as e:
                    self._handle_network_error(e, "initializing OAuth flow")
                    raise
                except requests.exceptions.ConnectionError as e:
                    self._handle_network_error(e, "connecting to Google OAuth servers")
                    raise
            
            # Save the credentials for the next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        # Configure HTTP client with increased timeouts for large file downloads
        # Default socket timeout is often too short for multi-GB files
        try:
            # Set timeout to 10 minutes (600 seconds) for large file downloads
            http = httplib2.Http(timeout=600)
            http.disable_ssl_certificate_validation = False
            self.service = build('drive', 'v3', credentials=creds, http=http)
            logger.debug("Using custom HTTP client with 10-minute timeout for large file downloads")
        except Exception as e:
            # Fall back to default HTTP client if configuration fails
            logger.warning(f"Could not configure custom HTTP timeout: {e}. Using default HTTP client.")
            self.service = build('drive', 'v3', credentials=creds)
        
        logger.info("Successfully authenticated with Google Drive API")
    
    def _handle_network_error(self, error: Exception, context: str = "authentication"):
        """
        Handle network connectivity errors with helpful error messages.
        
        Args:
            error: The exception that was raised
            context: Description of what operation was being performed
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__
        
        # Check for DNS resolution errors
        if isinstance(error, socket.gaierror) or 'nodename nor servname provided' in error_msg or 'name resolution' in error_msg:
            logger.error("=" * 70)
            logger.error("NETWORK CONNECTIVITY ERROR")
            logger.error("=" * 70)
            logger.error("")
            logger.error(f"Cannot connect to Google's authentication servers while {context}.")
            logger.error("This usually indicates a network connectivity or DNS issue.")
            logger.error("")
            logger.error("Troubleshooting steps:")
            logger.error("  1. Check your internet connection")
            logger.error("  2. Verify DNS is working: try 'ping google.com' or 'nslookup oauth2.googleapis.com'")
            logger.error("  3. Check if you're behind a firewall or proxy that blocks Google services")
            logger.error("  4. Try restarting your network connection")
            logger.error("  5. If on a corporate network, contact IT about firewall rules")
            logger.error("")
            logger.error("You can test connectivity by running:")
            logger.error("  python3 -c \"import socket; socket.create_connection(('oauth2.googleapis.com', 443), timeout=5)\"")
            logger.error("")
            raise AuthenticationError(
                f"Network connectivity error during {context}: Cannot resolve or connect to oauth2.googleapis.com. "
                "Please check your internet connection and DNS settings."
            ) from error
        else:
            # Other network errors
            logger.error("=" * 70)
            logger.error("NETWORK ERROR")
            logger.error("=" * 70)
            logger.error("")
            logger.error(f"Network error during {context}: {error}")
            logger.error(f"Error type: {error_type}")
            logger.error("")
            logger.error("Troubleshooting steps:")
            logger.error("  1. Check your internet connection")
            logger.error("  2. Verify you can access Google services in a web browser")
            logger.error("  3. Check firewall/proxy settings")
            logger.error("  4. Try again in a few moments")
            logger.error("")
            raise AuthenticationError(
                f"Network error during {context}: {error}. "
                "Please check your internet connection and try again."
            ) from error
    
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
        Download a file from Google Drive with resumable download support.
        
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
        
        # Check if we have a partial download
        if destination_path.exists():
            existing_size = destination_path.stat().st_size
            # If file exists and is smaller than expected, it might be partial
            if file_size and existing_size < file_size and existing_size > 0:
                logger.warning(
                    f"Found partial download of {file_name} ({existing_size / 1024 / 1024:.2f} MB of "
                    f"expected {file_size / 1024 / 1024:.2f} MB). "
                    f"This partial file will be deleted and download will restart."
                )
                # Delete partial file - we'll restart the download from beginning
                destination_path.unlink()
                logger.info("Deleted partial file, will restart download from beginning")
            elif file_size and existing_size >= file_size:
                # File appears complete
                logger.info(f"File {file_name} already exists and appears complete, skipping download")
                return destination_path
            else:
                # File exists but we can't verify size - skip it
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
        # Use more retries for timeout errors specifically
        max_retries = 5  # Increased from 3 to handle timeouts better
        retry_delay = 5.0  # Increased initial delay
        timeout_retries = 0
        max_timeout_retries = 10  # Additional retries specifically for timeouts
        
        for attempt in range(max_retries):
            try:
                request = self.service.files().get_media(fileId=file_id)
                fh = io.FileIO(destination_path, 'wb')  # Always start fresh
                
                downloader = MediaIoBaseDownload(fh, request)
                
                # Track progress for large files
                last_progress = 0
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        # Log progress every 10% for large files
                        if progress - last_progress >= 10 or done:
                            downloaded_mb = destination_path.stat().st_size / 1024 / 1024
                            logger.info(
                                f"Download progress: {progress}% "
                                f"({downloaded_mb:.1f} MB downloaded)"
                            )
                            last_progress = progress
                
                fh.close()
                
                # Verify file size if we know the expected size
                final_size = destination_path.stat().st_size
                if file_size and final_size < file_size:
                    logger.warning(
                        f"Downloaded file size ({final_size / 1024 / 1024:.2f} MB) "
                        f"is smaller than expected ({file_size / 1024 / 1024:.2f} MB). "
                        f"File may be incomplete."
                    )
                
                logger.info(f"Downloaded {file_name} ({final_size / 1024 / 1024:.2f} MB)")
                return destination_path
                
            except socket.timeout as e:
                timeout_retries += 1
                if timeout_retries <= max_timeout_retries:
                    wait_time = retry_delay * (2 ** min(attempt, 3))  # Cap exponential growth
                    logger.warning(
                        f"Download timeout for {file_name} (timeout retry {timeout_retries}/{max_timeout_retries}): "
                        f"{e}. The connection timed out during download. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )
                    time.sleep(wait_time)
                    # Remove partial file if it exists - we'll restart from beginning
                    if destination_path.exists():
                        partial_size = destination_path.stat().st_size
                        logger.info(f"Removing partial file ({partial_size / 1024 / 1024:.2f} MB) to restart download")
                        destination_path.unlink()
                    continue
                else:
                    raise DownloadError(
                        f"Download failed for {file_name} after {max_timeout_retries} timeout retries: {e}. "
                        f"This may indicate a network connectivity issue or very slow connection. "
                        f"You can try running the script again - partial files will be automatically deleted and "
                        f"downloads will restart from the beginning."
                    ) from e
            except HttpError as e:
                if attempt < max_retries - 1 and e.resp.status in (500, 502, 503, 504, 429):
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Download failed for {file_name} (attempt {attempt + 1}/{max_retries}): "
                        f"HTTP {e.resp.status}. Retrying in {wait_time:.1f} seconds..."
                    )
                    time.sleep(wait_time)
                    # Don't remove partial file for server errors - we might be able to resume
                    continue
                else:
                    raise DownloadError(
                        f"Failed to download {file_name} from Google Drive: HTTP {e.resp.status} - {e}"
                    ) from e
            except (OSError, IOError) as e:
                # For I/O errors, check if it's a timeout-related error
                error_str = str(e).lower()
                if 'timeout' in error_str or 'timed out' in error_str:
                    timeout_retries += 1
                    if timeout_retries <= max_timeout_retries:
                        wait_time = retry_delay * (2 ** min(attempt, 3))
                        logger.warning(
                            f"IO timeout for {file_name} (timeout retry {timeout_retries}/{max_timeout_retries}): "
                            f"{e}. Retrying in {wait_time:.1f} seconds..."
                        )
                        time.sleep(wait_time)
                        continue
                
                raise DownloadError(
                    f"Failed to save {file_name} to disk: {e}. "
                    f"Check disk space and file permissions."
                ) from e
            except Exception as e:
                # Check if it's a timeout-related exception
                error_str = str(e).lower()
                if 'timeout' in error_str or 'timed out' in error_str:
                    timeout_retries += 1
                    if timeout_retries <= max_timeout_retries:
                        wait_time = retry_delay * (2 ** min(attempt, 3))
                        logger.warning(
                            f"Timeout error for {file_name} (timeout retry {timeout_retries}/{max_timeout_retries}): "
                            f"{e}. Retrying in {wait_time:.1f} seconds..."
                        )
                        time.sleep(wait_time)
                        continue
                
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

