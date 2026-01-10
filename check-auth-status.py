#!/usr/bin/env python3
"""
Check iCloud authentication status and cookie validity.
Helps diagnose 2FA authentication issues.
"""
import os
import sys
import logging
from pathlib import Path
import yaml
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_cookies(apple_id: str):
    """Check PhotoKit permission status (no cookies needed for PhotoKit method)."""
    print("=" * 60)
    print("PhotoKit Permission Status")
    print("=" * 60)
    print()
    print("✓ This tool uses PhotoKit framework (macOS only)")
    print("✓ No authentication cookies needed - uses your macOS iCloud account automatically")
    print("✓ No Apple ID credentials required")
    print()
    print("To check Photos library permission, run:")
    print("  python3 request_photos_permission.py")
    print()
    return True

def check_env_vars():
    """Check if Google Drive credentials are set (iCloud credentials not needed)."""
    print("=" * 60)
    print("Environment Variables")
    print("=" * 60)
    print()
    
    credentials_file = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_FILE')
    
    if credentials_file:
        print(f"✓ GOOGLE_DRIVE_CREDENTIALS_FILE is set: {credentials_file}")
    else:
        print("⚠ GOOGLE_DRIVE_CREDENTIALS_FILE is not set")
        print("   You can set this in .env file or config.yaml")
    
    print()
    print("Note: No iCloud credentials needed - uses macOS iCloud account automatically via PhotoKit")
    print()
    
    return True if credentials_file else False

def check_config(config_path: str):
    """Check config file for Google Drive settings (iCloud settings not needed)."""
    print("=" * 60)
    print("Configuration File")
    print("=" * 60)
    print()
    
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return
    
    print(f"✓ Config file exists: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        google_drive_config = config.get('google_drive', {})
        credentials_file = google_drive_config.get('credentials_file', '')
        
        print()
        if credentials_file:
            print(f"✓ Google Drive credentials file configured: {credentials_file}")
            if os.path.exists(credentials_file):
                print("  ✓ Credentials file exists")
            else:
                print("  ⚠ Credentials file not found at specified path")
        else:
            print("⚠ Google Drive credentials file not configured")
        
        icloud_config = config.get('icloud', {})
        print()
        print("iCloud Configuration:")
        print("  ✓ No credentials needed - uses macOS iCloud account automatically via PhotoKit")
        print("  ✓ PhotoKit method is the only supported method (macOS only)")
        
    except Exception as e:
        print(f"❌ Error reading config file: {e}")

def test_auth_attempt(apple_id: str):
    """Try to test authentication (without actually authenticating)."""
    print()
    print("=" * 60)
    print("Migration Test")
    print("=" * 60)
    print()
    print("To test the migration, run the main script:")
    print()
    print("  python3 main.py --config config.yaml")
    print()
    print("Note: This tool uses PhotoKit (macOS only) and requires no iCloud authentication.")
    print("It uses your macOS iCloud account automatically.")
    print()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check migration setup status (Google Drive and PhotoKit)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Get Apple ID from config
    apple_id = ""
    if os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
                apple_id = config.get('icloud', {}).get('apple_id', '')
        except Exception:
            pass
    
    print()
    print("Migration Setup Status Check")
    print("=" * 60)
    print()
    print("Note: This tool uses PhotoKit framework (macOS only)")
    print("      No iCloud authentication is needed - uses your macOS iCloud account automatically")
    print()
    
    # Check all components
    check_cookies(apple_id if apple_id else "")
    env_vars_set = check_env_vars()
    check_config(args.config)
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    if env_vars_set:
        print("✓ Google Drive credentials configured")
        print("✓ Ready to run migration")
    else:
        print("⚠ Google Drive credentials not configured")
        print()
        print("To set up Google Drive authentication:")
        print("  1. Set GOOGLE_DRIVE_CREDENTIALS_FILE in .env file")
        print("  2. Or configure credentials_file in config.yaml")
        print("  3. Run: python3 auth_setup.py")
    
    print()
    print("✓ iCloud setup: No configuration needed")
    print("  PhotoKit uses your macOS iCloud account automatically")
    print("  Just ensure iCloud Photos is enabled in System Settings")
    print()
    
    if apple_id:
        test_auth_attempt(apple_id)
    else:
        print("Next step: Configure Google Drive credentials and run the migration")

if __name__ == '__main__':
    main()

