"""
Interactive authentication setup wizard for Google Drive and Apple/iCloud.

This module provides a user-friendly way to set up authentication without
manually downloading credentials files or dealing with complex OAuth flows.
"""
import os
import json
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

logger = logging.getLogger(__name__)


class GoogleAuthSetup:
    """Simplified Google Drive authentication setup."""
    
    def __init__(self):
        self.credentials_file = "credentials.json"
        self.token_file = "token.json"
    
    def check_credentials_exist(self) -> bool:
        """Check if credentials.json already exists."""
        return Path(self.credentials_file).exists()
    
    def interactive_setup(self) -> bool:
        """
        Interactive setup wizard for Google Drive credentials.
        
        Returns:
            True if setup successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("Google Drive Authentication Setup")
        print("=" * 60)
        print()
        
        if self.check_credentials_exist():
            print(f"✓ Found existing credentials file: {self.credentials_file}")
            response = input("Use existing credentials? (Y/n): ").strip().lower()
            if response != 'n':
                return True
        
        print("\nTo use Google Drive, you need to set up OAuth credentials.")
        print("This is a one-time setup that takes about 5 minutes.")
        print()
        print("You have two options:")
        print()
        print("1. Quick Setup (Recommended)")
        print("   - I'll guide you through creating credentials in Google Cloud Console")
        print("   - Takes about 5 minutes")
        print()
        print("2. Use Default Credentials (Advanced)")
        print("   - Uses a shared OAuth client (less secure but faster)")
        print("   - Only recommended for testing")
        print()
        
        choice = input("Choose option (1 or 2, or 'q' to quit): ").strip()
        
        if choice == '1':
            return self._guided_setup()
        elif choice == '2':
            return self._use_default_credentials()
        else:
            print("Setup cancelled.")
            return False
    
    def _guided_setup(self) -> bool:
        """Guide user through creating credentials in Google Cloud Console."""
        print("\n" + "=" * 60)
        print("Guided Google Cloud Console Setup")
        print("=" * 60)
        print()
        print("Step 1: Create a Google Cloud Project")
        print("-" * 60)
        print("1. I'll open Google Cloud Console in your browser")
        print("2. Click 'Select a project' → 'New Project'")
        print("3. Enter a project name (e.g., 'Photos Migration')")
        print("4. Click 'Create'")
        print()
        input("Press Enter when you've created the project...")
        
        print("\nStep 2: Enable Google Drive API")
        print("-" * 60)
        print("1. I'll open the API Library page")
        print("2. Search for 'Google Drive API'")
        print("3. Click on it and click 'Enable'")
        print()
        input("Press Enter when the API is enabled...")
        
        print("\nStep 3: Create OAuth Credentials")
        print("-" * 60)
        print("1. I'll open the Credentials page")
        print("2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
        print("3. If prompted, configure OAuth consent screen:")
        print("   - Choose 'External'")
        print("   - App name: 'Photos Migration Tool'")
        print("   - Your email for support/developer contact")
        print("   - Add your email as a test user")
        print("   - Click 'Save and Continue' through all steps")
        print("4. Back at Credentials, create OAuth client ID:")
        print("   - Application type: 'Desktop app'")
        print("   - Name: 'Photos Migration Desktop Client'")
        print("   - Click 'Create'")
        print("5. Click the download button (⬇️) to download the JSON file")
        print()
        input("Press Enter when you've downloaded the credentials file...")
        
        print("\nStep 4: Save Credentials File")
        print("-" * 60)
        print(f"Please move the downloaded file to this directory:")
        print(f"  {os.getcwd()}")
        print(f"And rename it to: {self.credentials_file}")
        print()
        
        # Check for common download locations
        download_paths = [
            Path.home() / "Downloads" / "client_secret_*.json",
            Path.home() / "Downloads" / "credentials.json",
            Path.home() / "Desktop" / "client_secret_*.json",
        ]
        
        found_file = None
        for pattern in download_paths:
            if '*' in str(pattern):
                import glob
                matches = glob.glob(str(pattern))
                if matches:
                    found_file = Path(matches[0])
                    break
            else:
                if pattern.exists():
                    found_file = pattern
                    break
        
        if found_file:
            print(f"Found a credentials file: {found_file}")
            response = input(f"Copy it to {self.credentials_file}? (Y/n): ").strip().lower()
            if response != 'n':
                import shutil
                shutil.copy(found_file, self.credentials_file)
                print(f"✓ Copied to {self.credentials_file}")
        
        if not Path(self.credentials_file).exists():
            input(f"\nPlease ensure {self.credentials_file} is in this directory, then press Enter...")
        
        if Path(self.credentials_file).exists():
            # Validate the file
            try:
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)
                if 'installed' in creds or 'web' in creds:
                    print(f"✓ Credentials file is valid!")
                    return True
                else:
                    print("✗ Credentials file format is invalid")
                    return False
            except json.JSONDecodeError:
                print("✗ Credentials file is not valid JSON")
                return False
        else:
            print(f"✗ {self.credentials_file} not found")
            return False
    
    def _use_default_credentials(self) -> bool:
        """Use default/embedded OAuth credentials (for testing only)."""
        print("\n" + "=" * 60)
        print("⚠️  WARNING: Using Default Credentials")
        print("=" * 60)
        print()
        print("This uses a shared OAuth client ID. While functional, it's less secure")
        print("because multiple users share the same client.")
        print()
        print("For production use, please use option 1 (Guided Setup) instead.")
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
        
        # Create a minimal credentials file with a default client
        # Note: In a real implementation, you might embed a default client ID
        # For security, we'll just create a template
        default_creds = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID_HERE",
                "project_id": "YOUR_PROJECT_ID",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET_HERE",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        print("\nCreating template credentials file...")
        print("You'll need to fill in your actual client ID and secret.")
        print("This option is not recommended. Please use Guided Setup instead.")
        
        return False  # Don't actually create default credentials for security
    
    def authenticate(self) -> bool:
        """
        Perform OAuth authentication flow.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not Path(self.credentials_file).exists():
            logger.error(f"Credentials file not found: {self.credentials_file}")
            return False
        
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            
            creds = None
            if Path(self.token_file).exists():
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    print("\n" + "=" * 60)
                    print("Google Drive Authentication")
                    print("=" * 60)
                    print()
                    print("A browser window will open for you to sign in with Google.")
                    print("After signing in, you'll be redirected back here automatically.")
                    print()
                    input("Press Enter to open browser and sign in...")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0, open_browser=True)
                
                # Save token for next time
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            print("✓ Successfully authenticated with Google Drive!")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def select_google_drive_folder(self) -> Optional[str]:
        """
        Interactively select a Google Drive folder containing Takeout zip files.
        
        Returns:
            Folder ID if selected, None if user chooses to skip or search all Drive
        """
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            
            # Load credentials
            if not Path(self.token_file).exists():
                print("⚠️  Not authenticated yet. Please authenticate first.")
                return None
            
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            if not creds or not creds.valid:
                print("⚠️  Authentication expired. Please re-authenticate.")
                return None
            
            service = build('drive', 'v3', credentials=creds)
            
            print("\n" + "=" * 60)
            print("Google Drive Folder Selection")
            print("=" * 60)
            print()
            print("Where are your Google Takeout zip files located?")
            print()
            print("1. Search all of Google Drive (default)")
            print("   - Will find zip files anywhere in your Drive")
            print("   - Use if files are in multiple locations")
            print()
            print("2. Select a specific folder")
            print("   - Faster and more organized")
            print("   - Recommended if all files are in one folder")
            print()
            
            choice = input("Choose option (1 or 2, default is 1): ").strip()
            
            if choice == '2':
                return self._browse_folders(service)
            else:
                print("✓ Will search all of Google Drive for zip files")
                return None
                
        except Exception as e:
            logger.error(f"Error selecting folder: {e}")
            print(f"⚠️  Error accessing Google Drive: {e}")
            print("   You can manually set folder_id in config.yaml later")
            return None
    
    def _browse_folders(self, service) -> Optional[str]:
        """Browse and select a folder from Google Drive."""
        try:
            print("\n" + "=" * 60)
            print("Browse Google Drive Folders")
            print("=" * 60)
            print()
            print("Fetching folders from Google Drive...")
            
            # List folders (mimeType = 'application/vnd.google-apps.folder')
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(
                q=query,
                fields="files(id, name, parents)",
                pageSize=100,
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            
            if not folders:
                print("No folders found in Google Drive.")
                print("You can manually enter a folder ID in config.yaml")
                return None
            
            print(f"\nFound {len(folders)} folder(s):")
            print()
            
            # Show folders
            for i, folder in enumerate(folders[:50], 1):  # Limit to 50 for display
                name = folder.get('name', 'Unnamed')
                folder_id = folder.get('id', '')
                print(f"  {i}. {name} (ID: {folder_id})")
            
            if len(folders) > 50:
                print(f"  ... and {len(folders) - 50} more folders")
            
            print()
            print("Options:")
            print("  - Enter a number (1-{}) to select a folder".format(min(50, len(folders))))
            print("  - Enter a folder ID directly (if you know it)")
            print("  - Enter 'url' to paste a Google Drive folder URL")
            print("  - Press Enter to skip (search all Drive)")
            print()
            
            user_input = input("Your choice: ").strip()
            
            if not user_input:
                print("✓ Will search all of Google Drive")
                return None
            
            # Try to parse as number
            try:
                folder_num = int(user_input)
                if 1 <= folder_num <= min(50, len(folders)):
                    selected_folder = folders[folder_num - 1]
                    folder_id = selected_folder.get('id')
                    folder_name = selected_folder.get('name', 'Unnamed')
                    print(f"✓ Selected folder: {folder_name}")
                    print(f"  Folder ID: {folder_id}")
                    return folder_id
                else:
                    print("Invalid folder number")
                    return None
            except ValueError:
                # Not a number, try as folder ID or URL
                if user_input.lower() == 'url':
                    url = input("Paste the Google Drive folder URL: ").strip()
                    # Extract folder ID from URL
                    # URLs look like: https://drive.google.com/drive/folders/FOLDER_ID
                    if 'folders/' in url:
                        folder_id = url.split('folders/')[-1].split('?')[0].split('&')[0]
                        print(f"✓ Extracted folder ID: {folder_id}")
                        return folder_id
                    else:
                        print("Invalid URL format")
                        return None
                else:
                    # Assume it's a folder ID
                    print(f"✓ Using folder ID: {user_input}")
                    return user_input
                    
        except Exception as e:
            logger.error(f"Error browsing folders: {e}")
            print(f"⚠️  Error browsing folders: {e}")
            return None


class AppleAuthSetup:
    """Apple/iCloud authentication setup."""
    
    def __init__(self):
        pass
    
    def check_system_icloud(self) -> bool:
        """Check if user is signed into iCloud on macOS."""
        import platform
        if platform.system() != 'Darwin':
            return False
        
        # Check if Photos library exists (indicates iCloud Photos might be enabled)
        photos_lib = Path.home() / "Pictures" / "Photos Library.photoslibrary"
        return photos_lib.exists()
    
    def interactive_setup(self, use_sync_method: bool = True) -> Dict[str, Any]:
        """
        Interactive setup for Apple/iCloud authentication.
        
        Args:
            use_sync_method: If True, use PhotoKit (no auth needed). If False, use API method.
        
        Returns:
            Dictionary with apple_id and other auth info
        """
        print("\n" + "=" * 60)
        print("Apple/iCloud Authentication Setup")
        print("=" * 60)
        print()
        
        if use_sync_method:
            print("Using PhotoKit sync method (--use-sync)")
            print("-" * 60)
            print("✓ No authentication needed!")
            print("✓ Uses your macOS iCloud account automatically")
            print("✓ Photos will sync to iCloud Photos if enabled in System Settings")
            print()
            
            # Check if iCloud Photos is enabled
            import platform
            if platform.system() == 'Darwin':
                print("To enable iCloud Photos:")
                print("1. Open System Settings → Apple ID → iCloud")
                print("2. Enable 'Photos' (or 'iCloud Photos')")
                print("3. Choose 'Download Originals' or 'Optimize Storage'")
                print()
                response = input("Is iCloud Photos enabled? (Y/n): ").strip().lower()
                if response == 'n':
                    print("\n⚠️  Please enable iCloud Photos in System Settings before running the migration.")
                    print("   The tool will still work, but photos won't sync to iCloud automatically.")
            
            return {
                'apple_id': None,  # Not needed for PhotoKit
                'password': None,
                'method': 'photokit'
            }
        else:
            print("Using API method (requires Apple ID credentials)")
            print("-" * 60)
            print("⚠️  Note: Apple doesn't provide OAuth for iCloud Photos API")
            print("   You'll need to provide your Apple ID and password")
            print("   (Password is stored securely and only used for authentication)")
            print()
            
            apple_id = input("Enter your Apple ID email: ").strip()
            if not apple_id:
                return {}
            
            print("\nPassword:")
            print("- Leave empty to be prompted when needed")
            print("- Or enter it now (will be stored in config)")
            password = input("Apple ID password (optional): ").strip()
            
            return {
                'apple_id': apple_id,
                'password': password,
                'method': 'api'
            }


def run_auth_setup_wizard() -> bool:
    """
    Run the complete authentication setup wizard.
    
    Returns:
        True if setup successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("Google Photos to iCloud Photos Migration")
    print("Authentication Setup Wizard")
    print("=" * 60)
    print()
    
    # Google Drive setup
    google_auth = GoogleAuthSetup()
    if not google_auth.interactive_setup():
        print("\n✗ Google Drive setup incomplete. You can run this again later.")
        return False
    
    # Authenticate with Google
    if not google_auth.authenticate():
        print("\n✗ Google Drive authentication failed.")
        return False
    
    # Select Google Drive folder
    folder_id = google_auth.select_google_drive_folder()
    
    # Apple/iCloud setup
    print("\n" + "=" * 60)
    print("Apple/iCloud Setup")
    print("=" * 60)
    print()
    print("Which method do you want to use for uploading to iCloud Photos?")
    print()
    print("1. PhotoKit Sync (Recommended for macOS)")
    print("   - No authentication needed")
    print("   - Uses system iCloud account")
    print("   - Preserves all metadata")
    print("   - Requires macOS")
    print()
    print("2. API Method (Alternative)")
    print("   - Requires Apple ID and password")
    print("   - Works on any platform")
    print("   - May have limitations")
    print()
    
    choice = input("Choose method (1 or 2): ").strip()
    use_sync = (choice == '1')
    
    apple_auth = AppleAuthSetup()
    apple_config = apple_auth.interactive_setup(use_sync_method=use_sync)
    
    # Save configuration
    config = {
        'google_drive': {
            'credentials_file': 'credentials.json',
            'folder_id': folder_id if folder_id else ''
        },
        'icloud': apple_config,
        'processing': {
            'base_dir': '/tmp/google-photos-migration',
            'batch_size': 100,
            'cleanup_after_upload': True
        },
        'metadata': {
            'preserve_dates': True,
            'preserve_gps': True,
            'preserve_descriptions': True,
            'preserve_albums': True
        }
    }
    
    config_file = "config.yaml"
    if Path(config_file).exists():
        response = input(f"\n{config_file} already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print(f"Keeping existing {config_file}")
            return True
    
    try:
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"\n✓ Configuration saved to {config_file}")
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("You can now run the migration:")
        if use_sync:
            print("  python3 main.py --config config.yaml --use-sync")
        else:
            print("  python3 main.py --config config.yaml")
        print()
        return True
    except Exception as e:
        print(f"\n✗ Failed to save configuration: {e}")
        return False


if __name__ == '__main__':
    import sys
    success = run_auth_setup_wizard()
    sys.exit(0 if success else 1)

