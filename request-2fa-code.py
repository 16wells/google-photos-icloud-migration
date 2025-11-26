#!/usr/bin/env python3
"""
Request a 2FA verification code and prepare for non-interactive use.
This script requests a code and then pauses, allowing you to set it as an environment variable.
"""
import sys
import os
import logging
import yaml
from pathlib import Path
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloud2FARequiredException, PyiCloudFailedLoginException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def request_code(apple_id: str, password: str = None, device_id: str = None):
    """Request a 2FA verification code."""
    import getpass
    
    if not password:
        password = getpass.getpass(f"Enter password for {apple_id}: ")
    
    cookie_dir = os.path.expanduser("~/.pyicloud")
    
    logger.info(f"Attempting to authenticate with Apple ID: {apple_id}")
    
    try:
        api = PyiCloudService(apple_id, password, cookie_directory=cookie_dir)
        
        # Check if 2FA is required
        if not (hasattr(api, 'requires_2fa') and api.requires_2fa):
            logger.info("✓ Authentication successful - 2FA not required")
            logger.info("Cookies saved. You can run the main script without 2FA.")
            return True
        
        logger.info("2FA authentication required")
        
        # Get trusted devices
        import time
        time.sleep(1)  # Give devices time to populate
        
        devices = api.trusted_devices
        
        # Ensure devices is a list
        if devices is None:
            devices = []
        elif not isinstance(devices, list):
            devices = list(devices) if hasattr(devices, '__iter__') else []
        
        if len(devices) == 0:
            logger.error("No trusted devices found.")
            logger.error("Please set up trusted devices at https://appleid.apple.com")
            return False
        
        # Select device
        device = None
        
        if device_id:
            try:
                device_idx = int(device_id)
                if 0 <= device_idx < len(devices):
                    device = devices[device_idx]
                    logger.info(f"Using device ID: {device_idx}")
                else:
                    logger.error(f"Invalid device ID: {device_id}. Valid range: 0-{len(devices)-1}")
                    device = None
            except ValueError:
                logger.error(f"Invalid device ID format: {device_id}")
                device = None
        
        # List devices if not selected
        if device is None:
            logger.info("Available trusted devices:")
            for i, d in enumerate(devices):
                name = d.get('deviceName', 'Unknown') if isinstance(d, dict) else getattr(d, 'deviceName', 'Unknown')
                logger.info(f"  {i}: {name}")
            
            if not sys.stdin.isatty():
                logger.error("Non-interactive mode: Cannot select device")
                logger.error("Set device ID via: export ICLOUD_2FA_DEVICE_ID=<number>")
                return False
            
            while True:
                try:
                    idx_str = input(f"Select device (0-{len(devices)-1}): ").strip()
                    idx = int(idx_str)
                    if 0 <= idx < len(devices):
                        device = devices[idx]
                        break
                    else:
                        logger.warning(f"Invalid selection. Enter a number between 0 and {len(devices)-1}")
                except ValueError:
                    logger.warning("Invalid input. Please enter a number.")
                except (EOFError, KeyboardInterrupt):
                    logger.error("Cancelled")
                    return False
        
        # Send verification code
        device_name = device.get('deviceName', 'Unknown') if isinstance(device, dict) else getattr(device, 'deviceName', 'Unknown')
        logger.info(f"Requesting verification code for: {device_name}")
        
        if not api.send_verification_code(device):
            logger.error("Failed to send verification code")
            return False
        
        logger.info(f"✓ Verification code sent to {device_name}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("NEXT STEPS FOR NON-INTERACTIVE USE:")
        logger.info("=" * 60)
        logger.info("")
        logger.info("1. Check your device for the verification code")
        logger.info("2. Set the code as an environment variable:")
        logger.info(f"   export ICLOUD_2FA_CODE=<code>")
        logger.info("")
        logger.info("3. Set the device ID (if not already set):")
        device_idx = devices.index(device) if device in devices else 0
        logger.info(f"   export ICLOUD_2FA_DEVICE_ID={device_idx}")
        logger.info("")
        logger.info("4. Run your migration script:")
        logger.info("   python3 main.py --config config.yaml")
        logger.info("")
        logger.info("=" * 60)
        logger.info("")
        logger.info("The verification code will expire in about 10 minutes.")
        logger.info("If it expires, run this script again to request a new code.")
        logger.info("")
        
        return True
        
    except PyiCloud2FARequiredException:
        logger.error("2FA required but devices couldn't be retrieved")
        return False
    except PyiCloudFailedLoginException as e:
        logger.error(f"Login failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Request a 2FA verification code for non-interactive use'
    )
    parser.add_argument('apple_id', nargs='?', help='Apple ID email')
    parser.add_argument('--config', '-c', default='config.yaml', help='Path to config file')
    parser.add_argument('--device-id', '-d', help='Trusted device ID (number)')
    parser.add_argument('--password', '-p', help='Password (will prompt if not provided)')
    
    args = parser.parse_args()
    
    apple_id = args.apple_id
    
    # Try to get from config if not provided
    if not apple_id:
        if os.path.exists(args.config):
            try:
                with open(args.config, 'r') as f:
                    config = yaml.safe_load(f)
                    apple_id = config.get('icloud', {}).get('apple_id', '')
            except Exception:
                pass
    
    if not apple_id:
        logger.error("Apple ID required. Provide as argument or in config file.")
        parser.print_help()
        sys.exit(1)
    
    # Try to get device ID from env or config
    device_id = args.device_id or os.environ.get('ICLOUD_2FA_DEVICE_ID')
    if not device_id and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
                device_id = config.get('icloud', {}).get('trusted_device_id', '')
        except Exception:
            pass
    
    password = args.password
    if not password and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
                password = config.get('icloud', {}).get('password', '').strip()
        except Exception:
            pass
    
    success = request_code(apple_id, password, device_id)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

