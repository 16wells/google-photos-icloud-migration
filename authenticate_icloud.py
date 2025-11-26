#!/usr/bin/env python3
"""
Helper script to manually authenticate with iCloud and handle 2FA.
This can be run separately to establish authentication, then the main script
can use the saved cookies.
"""
import sys
import logging
import os
import yaml
from pathlib import Path
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloud2FARequiredException, PyiCloudFailedLoginException
import getpass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def authenticate_icloud(apple_id: str, password: str = None, cookie_dir: str = None):
    """
    Authenticate with iCloud and handle 2FA if needed.
    
    Args:
        apple_id: Apple ID email
        password: Apple ID password (will prompt if not provided)
        cookie_dir: Directory for cookies (defaults to ~/.pyicloud)
    
    Returns:
        PyiCloudService object if successful, None otherwise
    """
    if not password:
        password = getpass.getpass(f"Enter password for {apple_id}: ")
    
    if cookie_dir is None:
        import os
        cookie_dir = os.path.expanduser("~/.pyicloud")
    
    logger.info(f"Attempting to authenticate with Apple ID: {apple_id}")
    logger.info(f"Using cookie directory: {cookie_dir}")
    
    try:
        api = PyiCloudService(apple_id, password, cookie_directory=cookie_dir)
        
        # Check if 2FA is required
        if hasattr(api, 'requires_2fa') and api.requires_2fa:
            logger.info("2FA authentication required")
            
            # Wait a moment for trusted devices to populate
            import time
            time.sleep(1)
            
            # Try multiple ways to get trusted devices
            devices = None
            
            # Method 1: Direct property access
            try:
                devices = api.trusted_devices
                logger.info(f"Got trusted_devices via direct property: {type(devices)}")
            except Exception as e:
                logger.debug(f"Direct property access failed: {e}")
            
            # Method 2: Try accessing via authentication object
            if (not devices or (hasattr(devices, '__len__') and len(devices) == 0)) and hasattr(api, 'authentication'):
                try:
                    if hasattr(api.authentication, 'trusted_devices'):
                        devices = api.authentication.trusted_devices
                        logger.info(f"Got trusted_devices via authentication object: {type(devices)}")
                except Exception as e:
                    logger.debug(f"Authentication object access failed: {e}")
            
            # Method 3: Try private attribute
            if (not devices or (hasattr(devices, '__len__') and len(devices) == 0)) and hasattr(api, '_trusted_devices'):
                try:
                    devices = api._trusted_devices
                    logger.info(f"Got trusted_devices via private attribute: {type(devices)}")
                except Exception as e:
                    logger.debug(f"Private attribute access failed: {e}")
            
            # Convert to list if needed
            if devices is not None and not isinstance(devices, list):
                try:
                    if hasattr(devices, '__iter__'):
                        devices = list(devices)
                        logger.info(f"Converted devices to list, length: {len(devices)}")
                    else:
                        devices = []
                except Exception as e:
                    logger.warning(f"Error converting devices to list: {e}")
                    devices = []
            
            if not devices or len(devices) == 0:
                logger.error("=" * 60)
                logger.error("No trusted devices found")
                logger.error("=" * 60)
                logger.error("")
                logger.error("This could mean:")
                logger.error("  1. You don't have trusted devices set up")
                logger.error("  2. The devices haven't been populated yet")
                logger.error("  3. pyicloud can't access them due to internal exception handling")
                logger.error("")
                logger.error("To set up trusted devices:")
                logger.error("  1. Go to https://appleid.apple.com")
                logger.error("  2. Sign in with your Apple ID")
                logger.error("  3. Go to 'Sign-In and Security' → 'Two-Factor Authentication'")
                logger.error("  4. Make sure you have at least one trusted device listed")
                logger.error("")
                logger.error("Trusted devices are typically:")
                logger.error("  - Your iPhone, iPad, or Mac")
                logger.error("  - Any device you've previously used to sign in")
                logger.error("")
                logger.error("If you have trusted devices but they're not showing up,")
                logger.error("this is likely due to pyicloud's internal exception handling")
                logger.error("preventing proper 2FA flow.")
                logger.error("")
                return None
            
            # List devices
            logger.info("Available trusted devices:")
            for i, device in enumerate(devices):
                device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
                logger.info(f"  {i}: {device_name}")
            
            # Select device
            while True:
                try:
                    device_idx = input(f"Select device (enter number 0-{len(devices)-1}): ").strip()
                    idx = int(device_idx)
                    if 0 <= idx < len(devices):
                        device = devices[idx]
                        break
                    else:
                        logger.warning(f"Invalid selection. Please enter a number between 0 and {len(devices)-1}")
                except ValueError:
                    logger.warning("Invalid input. Please enter a number.")
                except KeyboardInterrupt:
                    logger.error("Cancelled by user")
                    return None
            
            device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
            
            # Send verification code
            if not api.send_verification_code(device):
                logger.error("Failed to send verification code")
                return None
            
            logger.info(f"Verification code sent to {device_name}")
            
            # Get verification code
            max_attempts = 3
            for attempt in range(max_attempts):
                code = input(f"Enter 2FA code (attempt {attempt + 1}/{max_attempts}): ").strip()
                code = code.replace(' ', '').replace('-', '')
                
                if api.validate_verification_code(device, code):
                    logger.info("✓ Verification code accepted")
                    logger.info("✓ Authentication successful!")
                    return api
                else:
                    if attempt < max_attempts - 1:
                        logger.warning("Invalid verification code. Please try again.")
                        retry = input("Request new code? (y/n): ").strip().lower()
                        if retry == 'y':
                            if not api.send_verification_code(device):
                                logger.error("Failed to send new verification code")
                                return None
                            logger.info("New verification code sent")
                    else:
                        logger.error("Invalid verification code after multiple attempts")
                        return None
        
        logger.info("✓ Authentication successful!")
        return api
        
    except PyiCloud2FARequiredException as e:
        logger.error("=" * 60)
        logger.error("2FA Exception Caught (but pyicloud will handle it internally)")
        logger.error("=" * 60)
        logger.error("")
        logger.error("pyicloud raised a 2FA exception, but it will catch it internally")
        logger.error("and try SRP authentication, which will fail.")
        logger.error("")
        logger.error("This script cannot work around pyicloud's internal exception handling.")
        logger.error("")
        logger.error("SOLUTIONS:")
        logger.error("")
        logger.error("1. Try using an app-specific password:")
        logger.error("   - Go to https://appleid.apple.com")
        logger.error("   - Sign-In and Security → App-Specific Passwords")
        logger.error("   - Generate a password and use it in config.yaml")
        logger.error("")
        logger.error("2. Check if your account has trusted devices set up:")
        logger.error("   - Go to https://appleid.apple.com")
        logger.error("   - Sign-In and Security → Two-Factor Authentication")
        logger.error("   - Verify trusted devices are listed")
        logger.error("")
        logger.error("3. The issue is that pyicloud's internal code prevents proper 2FA handling.")
        logger.error("   This may require a pyicloud library update or a different approach.")
        logger.error("")
        return None
    except PyiCloudFailedLoginException as e:
        logger.error(f"Login failed: {e}")
        # Check if it's actually a 2FA issue
        import traceback
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        if "HSA2" in tb_str or "PyiCloud2FARequiredException" in tb_str:
            logger.error("=" * 60)
            logger.error("This is a 2FA Issue")
            logger.error("=" * 60)
            logger.error("")
            logger.error("The login failure was caused by a 2FA requirement.")
            logger.error("pyicloud's internal exception handling prevents proper 2FA flow.")
            logger.error("")
            logger.error("SOLUTIONS:")
            logger.error("")
            logger.error("1. Try an app-specific password (most likely to work):")
            logger.error("   - Go to https://appleid.apple.com")
            logger.error("   - Sign-In and Security → App-Specific Passwords")
            logger.error("   - Generate a password")
            logger.error("   - Update config.yaml with the app-specific password")
            logger.error("")
            logger.error("2. Check pyicloud version and update:")
            logger.error("   pip install --upgrade pyicloud")
            logger.error("")
            logger.error("3. Check pyicloud GitHub for 2FA handling improvements:")
            logger.error("   https://github.com/picklepete/pyicloud")
            logger.error("")
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Authenticate with iCloud')
    parser.add_argument('apple_id', help='Apple ID email address')
    parser.add_argument('--password', '-p', help='Password (or use --config to read from config.yaml)')
    parser.add_argument('--config', '-c', default='config.yaml', help='Path to config.yaml file (default: config.yaml)')
    parser.add_argument('--cookie-dir', help='Directory for cookies (default: ~/.pyicloud)')
    
    args = parser.parse_args()
    
    apple_id = args.apple_id
    password = args.password
    cookie_dir = args.cookie_dir  # This will be None if not provided, which is correct
    
    # Try to read password from config.yaml if not provided via command line
    if not password:
        # Try the specified config file, or default to config.yaml
        config_path = Path(args.config) if args.config else Path('config.yaml')
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        password = config.get('icloud', {}).get('password', '').strip()
                        if password:
                            logger.info(f"✓ Read password from {config_path}")
                        else:
                            logger.info(f"Password field is empty in {config_path}")
                    else:
                        logger.warning(f"Config file {config_path} is empty")
            except Exception as e:
                logger.warning(f"Could not read {config_path}: {e}")
        else:
            logger.info(f"Config file {config_path} not found, will prompt for password")
    
    api = authenticate_icloud(apple_id, password=password, cookie_dir=cookie_dir)
    
    if api:
        print("\n✓ Authentication successful!")
        print("Cookies have been saved. You can now run the main migration script.")
        print("The main script should be able to use the saved authentication.")
    else:
        print("\n✗ Authentication failed")
        sys.exit(1)

