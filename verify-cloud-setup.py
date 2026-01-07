#!/usr/bin/env python3
"""
Verify Google Cloud OAuth credentials setup.
Helps diagnose authentication issues with Google Drive API.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_credentials_file(credentials_file: str = "credentials.json") -> Dict[str, Any]:
    """Check if credentials.json exists and is valid."""
    print("=" * 60)
    print("Google Cloud Credentials Check")
    print("=" * 60)
    print()
    
    creds_path = Path(credentials_file)
    
    if not creds_path.exists():
        print(f"❌ Credentials file not found: {credentials_file}")
        print()
        print("To create credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable Google Drive API:")
        print("   - Go to APIs & Services → Library")
        print("   - Search for 'Google Drive API'")
        print("   - Click 'Enable'")
        print("4. Create OAuth 2.0 credentials:")
        print("   - Go to APIs & Services → Credentials")
        print("   - Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
        print("   - Configure OAuth consent screen (if prompted)")
        print("   - Application type: 'Desktop app'")
        print("   - Download the JSON file")
        print("5. Save the downloaded file as 'credentials.json' in this directory")
        print()
        return {'exists': False, 'valid': False}
    
    print(f"✓ Credentials file exists: {credentials_file}")
    
    # Validate JSON structure
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        # Check for required fields
        if 'installed' in creds_data:
            client_id = creds_data['installed'].get('client_id', '')
            client_secret = creds_data['installed'].get('client_secret', '')
            project_id = creds_data['installed'].get('project_id', '')
            
            print(f"✓ Valid JSON structure (Desktop app type)")
            print(f"  Project ID: {project_id}")
            print(f"  Client ID: {client_id[:20]}..." if client_id else "  Client ID: (missing)")
            print(f"  Client Secret: {'*' * 20}..." if client_secret else "  Client Secret: (missing)")
            
            if not client_id or not client_secret:
                print()
                print("⚠️  Missing required fields in credentials file")
                print("   Make sure you downloaded the complete credentials file")
                return {'exists': True, 'valid': False, 'data': creds_data}
            
            return {'exists': True, 'valid': True, 'data': creds_data}
            
        elif 'web' in creds_data:
            print("⚠️  Credentials file is for 'Web application' type")
            print("   This tool requires 'Desktop app' type credentials")
            print("   Please create new OAuth credentials with type 'Desktop app'")
            return {'exists': True, 'valid': False, 'data': creds_data}
        else:
            print("❌ Invalid credentials file structure")
            print("   Expected 'installed' or 'web' key")
            return {'exists': True, 'valid': False, 'data': creds_data}
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in credentials file: {e}")
        return {'exists': True, 'valid': False}
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return {'exists': True, 'valid': False}


def check_token_file(token_file: str = "token.json") -> Dict[str, Any]:
    """Check if token.json exists and is valid."""
    print()
    print("=" * 60)
    print("Authentication Token Check")
    print("=" * 60)
    print()
    
    # Backward compatibility: if legacy token.json exists in CWD, prefer it
    legacy = Path(token_file)
    if legacy.exists():
        token_path = legacy
    else:
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        base_dir = Path(xdg_config_home) if xdg_config_home else (Path.home() / '.config')
        token_path = base_dir / 'google-photos-icloud-migration' / token_file
    
    if not token_path.exists():
        print(f"⚠️  Token file not found: {token_file}")
        print("   This is normal if you haven't authenticated yet.")
        print("   The token will be created automatically on first authentication.")
        print(f"   Expected location: {token_path}")
        print()
        return {'exists': False, 'valid': False}
    
    print(f"✓ Token file exists: {token_file}")
    
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        # Check for required fields
        if 'token' in token_data or 'access_token' in token_data:
            print("✓ Token file contains access token")
            
            # Check expiration if available
            if 'expiry' in token_data:
                from datetime import datetime
                try:
                    expiry_str = token_data['expiry']
                    if expiry_str:
                        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                        now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()
                        if expiry > now:
                            print(f"✓ Token is valid (expires: {expiry_str})")
                        else:
                            print(f"⚠️  Token has expired (expired: {expiry_str})")
                            print("   It will be refreshed automatically on next use")
                except Exception:
                    print("⚠️  Could not parse token expiry")
            
            return {'exists': True, 'valid': True, 'data': token_data}
        else:
            print("⚠️  Token file structure may be invalid")
            return {'exists': True, 'valid': False, 'data': token_data}
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in token file: {e}")
        return {'exists': True, 'valid': False}
    except Exception as e:
        print(f"❌ Error reading token file: {e}")
        return {'exists': True, 'valid': False}


def test_google_drive_connection(credentials_file: str = "credentials.json") -> bool:
    """Test connection to Google Drive API."""
    print()
    print("=" * 60)
    print("Google Drive API Connection Test")
    print("=" * 60)
    print()
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        creds = None
        token_file = 'token.json'
        
        # Load existing token if available
        if Path(token_file).exists():
            try:
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except Exception as e:
                print(f"⚠️  Could not load existing token: {e}")
        
        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                try:
                    creds.refresh(Request())
                    print("✓ Token refreshed successfully")
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    print("   You may need to re-authenticate")
                    return False
            else:
                print("⚠️  No valid token found")
                print("   You need to authenticate first")
                print()
                print("To authenticate:")
                print("  1. Run: python3 auth_setup.py")
                print("  2. Or run the main script - it will prompt for authentication")
                return False
        
        # Test API connection
        print("Testing Google Drive API connection...")
        service = build('drive', 'v3', credentials=creds)
        
        # Try to list files (limited to 1 result for testing)
        try:
            results = service.files().list(pageSize=1, fields="files(id, name)").execute()
            files = results.get('files', [])
            print("✓ Successfully connected to Google Drive API")
            if files:
                print(f"  Found {len(files)} file(s) (showing first result)")
            else:
                print("  (No files found, but connection is working)")
            return True
        except HttpError as e:
            print(f"❌ Google Drive API error: {e}")
            if e.resp.status == 403:
                print("   This might be a permissions issue")
                print("   Make sure Google Drive API is enabled in your project")
            return False
            
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("   Install dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_google_drive_api_enabled() -> None:
    """Provide instructions for enabling Google Drive API."""
    print()
    print("=" * 60)
    print("Google Drive API Status")
    print("=" * 60)
    print()
    print("To verify Google Drive API is enabled:")
    print("1. Go to https://console.cloud.google.com/apis/library")
    print("2. Search for 'Google Drive API'")
    print("3. Check if it shows 'API enabled'")
    print("4. If not enabled, click 'Enable'")
    print()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify Google Cloud OAuth credentials setup'
    )
    parser.add_argument(
        '--credentials',
        default='credentials.json',
        help='Path to credentials file (default: credentials.json)'
    )
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test actual connection to Google Drive API'
    )
    
    args = parser.parse_args()
    
    print()
    print("Google Cloud OAuth Credentials Verification")
    print("=" * 60)
    print()
    
    # Check credentials file
    creds_status = check_credentials_file(args.credentials)
    
    # Check token file
    token_status = check_token_file()
    
    # Test connection if requested
    connection_ok = False
    if args.test_connection:
        if not creds_status.get('valid'):
            print()
            print("⚠️  Cannot test connection: credentials file is invalid")
        else:
            connection_ok = test_google_drive_connection(args.credentials)
    else:
        print()
        print("=" * 60)
        print("Connection Test")
        print("=" * 60)
        print()
        print("To test the actual connection to Google Drive API, run:")
        print("  python3 verify-cloud-setup.py --test-connection")
        print()
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    if creds_status.get('valid'):
        print("✓ Credentials file is valid")
    else:
        print("❌ Credentials file is missing or invalid")
        print("   See instructions above to create credentials")
    
    if token_status.get('exists'):
        print("✓ Authentication token exists")
    else:
        print("⚠️  Authentication token not found")
        print("   This is normal if you haven't authenticated yet")
    
    if args.test_connection:
        if connection_ok:
            print("✓ Google Drive API connection successful")
            print()
            print("🎉 Your Google Cloud setup is working correctly!")
        else:
            print("❌ Google Drive API connection failed")
            print("   Check the error messages above")
            check_google_drive_api_enabled()
    else:
        print()
        print("Next steps:")
        if not creds_status.get('valid'):
            print("  1. Set up Google Cloud credentials (see instructions above)")
        if not token_status.get('exists'):
            print("  2. Authenticate: python3 auth_setup.py")
        print("  3. Test connection: python3 verify-cloud-setup.py --test-connection")
        print("  4. Run migration: python3 main.py --config config.yaml")
    
    print()


if __name__ == '__main__':
    main()





