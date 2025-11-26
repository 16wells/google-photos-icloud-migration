#!/usr/bin/env python3
"""
Check iCloud authentication status and cookie validity.
Helps diagnose 2FA issues on VMs.
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
    """Check if authentication cookies exist and are recent."""
    cookie_dir = Path.home() / ".pyicloud"
    
    print("=" * 60)
    print("Authentication Cookie Status")
    print("=" * 60)
    print()
    
    if not cookie_dir.exists():
        print("❌ No cookie directory found")
        print(f"   Location: {cookie_dir}")
        print()
        print("Cookies are created after successful authentication.")
        return False
    
    print(f"✓ Cookie directory exists: {cookie_dir}")
    
    # Check for cookie files
    cookie_files = list(cookie_dir.glob("*"))
    if not cookie_files:
        print("❌ Cookie directory is empty")
        print("   Authentication cookies not found.")
        return False
    
    print(f"✓ Found {len(cookie_files)} file(s) in cookie directory")
    
    # Check file ages
    print()
    print("Cookie file ages:")
    now = datetime.now()
    for cookie_file in cookie_files[:10]:  # Show first 10 files
        if cookie_file.is_file():
            mtime = datetime.fromtimestamp(cookie_file.stat().st_mtime)
            age = now - mtime
            age_hours = age.total_seconds() / 3600
            age_days = age.days
            
            status = "✓" if age_days < 7 else "⚠"
            if age_days == 0:
                age_str = f"{age_hours:.1f} hours ago"
            else:
                age_str = f"{age_days} day(s) ago"
            
            print(f"  {status} {cookie_file.name}: {age_str}")
    
    if len(cookie_files) > 10:
        print(f"  ... and {len(cookie_files) - 10} more file(s)")
    
    print()
    
    # Check if cookies are recent (less than 7 days old)
    recent_cookies = any(
        cookie_file.is_file() and 
        (datetime.now() - datetime.fromtimestamp(cookie_file.stat().st_mtime)).days < 7
        for cookie_file in cookie_files
    )
    
    if recent_cookies:
        print("✓ Recent cookies found (less than 7 days old)")
        print("   These cookies may still be valid for authentication.")
        print("   Try running the script - it may skip 2FA if cookies are valid.")
        return True
    else:
        print("⚠ Cookies are older than 7 days")
        print("   They may have expired. You may need to re-authenticate.")
        return False

def check_env_vars():
    """Check if 2FA environment variables are set."""
    print("=" * 60)
    print("Environment Variables")
    print("=" * 60)
    print()
    
    device_id = os.environ.get('ICLOUD_2FA_DEVICE_ID')
    code = os.environ.get('ICLOUD_2FA_CODE')
    
    if device_id:
        print(f"✓ ICLOUD_2FA_DEVICE_ID is set: {device_id}")
    else:
        print("❌ ICLOUD_2FA_DEVICE_ID is not set")
    
    if code:
        print(f"✓ ICLOUD_2FA_CODE is set: {'*' * len(code)} (hidden)")
    else:
        print("❌ ICLOUD_2FA_CODE is not set")
    
    print()
    
    if device_id and code:
        print("✓ Both environment variables are set")
        print("   The script can use these for non-interactive 2FA.")
        return True
    else:
        print("⚠ Not all environment variables are set")
        print("   For non-interactive mode, set both:")
        print("     export ICLOUD_2FA_DEVICE_ID=<device_number>")
        print("     export ICLOUD_2FA_CODE=<verification_code>")
        return False

def check_config(config_path: str):
    """Check config file for 2FA settings."""
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
        
        icloud_config = config.get('icloud', {})
        apple_id = icloud_config.get('apple_id', '')
        trusted_device_id = icloud_config.get('trusted_device_id', '')
        two_fa_code = icloud_config.get('two_fa_code', '')
        
        print()
        if apple_id:
            print(f"✓ Apple ID configured: {apple_id}")
        else:
            print("❌ Apple ID not configured")
        
        if trusted_device_id:
            print(f"✓ Trusted device ID configured: {trusted_device_id}")
        else:
            print("⚠ Trusted device ID not configured")
            print("   Set this for non-interactive 2FA support.")
        
        if two_fa_code:
            print(f"✓ 2FA code configured: {'*' * len(two_fa_code)} (hidden)")
            print("   Note: Codes expire quickly. This may be outdated.")
        else:
            print("⚠ 2FA code not configured")
            print("   Use environment variables instead (ICLOUD_2FA_CODE)")
        
    except Exception as e:
        print(f"❌ Error reading config file: {e}")

def test_auth_attempt(apple_id: str):
    """Try to test authentication (without actually authenticating)."""
    print()
    print("=" * 60)
    print("Authentication Test")
    print("=" * 60)
    print()
    print("To test authentication, run:")
    print()
    print(f"  python3 authenticate_icloud.py {apple_id}")
    print()
    print("Or run the main script:")
    print()
    print("  python3 main.py --config config.yaml")
    print()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check iCloud authentication status for VM use'
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
    print("iCloud Authentication Status Check")
    print("=" * 60)
    print()
    
    # Check all components
    cookie_valid = check_cookies(apple_id) if apple_id else False
    env_vars_set = check_env_vars()
    check_config(args.config)
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    
    if cookie_valid:
        print("✓ Authentication cookies found")
        print("   You may be able to authenticate without 2FA.")
    elif env_vars_set:
        print("✓ Environment variables are set")
        print("   Ready for non-interactive 2FA authentication.")
    else:
        print("⚠ Authentication setup incomplete")
        print()
        print("To set up 2FA for VM use:")
        print("  1. Run: bash setup-vm-2fa.sh")
        print("  2. Or manually set environment variables")
        print("  3. See VM_2FA_SETUP.md for details")
    
    print()
    
    if apple_id:
        test_auth_attempt(apple_id)
    else:
        print("⚠ Apple ID not found in config")
        print("   Update config.yaml with your Apple ID")

if __name__ == '__main__':
    main()

