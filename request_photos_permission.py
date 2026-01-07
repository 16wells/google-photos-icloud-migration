#!/usr/bin/env python3
"""
Helper script to request Photos library permission.
This script triggers the macOS permission dialog for Photos access.

Run this script first to grant permission before running the migration.
"""

import sys
import platform

if platform.system() != 'Darwin':
    print("❌ This script requires macOS")
    sys.exit(1)

try:
    from AppKit import NSWorkspace
    from Photos import (
        PHPhotoLibrary, PHAuthorizationStatus,
        PHAuthorizationStatusAuthorized, PHAuthorizationStatusLimited,
        PHAuthorizationStatusDenied, PHAuthorizationStatusNotDetermined
    )
except ImportError as e:
    print(f"❌ Error importing PhotoKit: {e}")
    print("Please install: pip install pyobjc-framework-Photos")
    sys.exit(1)

def request_permission():
    """Request Photos library permission and provide instructions."""
    print("=" * 60)
    print("Requesting Photos Library Permission")
    print("=" * 60)
    print()
    
    # Check current status
    current_status = PHPhotoLibrary.authorizationStatus()
    
    if current_status == PHAuthorizationStatusAuthorized:
        print("✓ Photo library permission already granted!")
        return True
    elif current_status == PHAuthorizationStatusLimited:
        print("✓ Photo library has limited access (sufficient for adding photos)")
        return True
    elif current_status == PHAuthorizationStatusDenied:
        print("❌ Photo library permission was previously denied")
        print()
        print("To fix this:")
        print("1. Open System Settings")
        print("2. Go to Privacy & Security > Photos")
        print("3. Find 'Terminal' or 'Python' in the list")
        print("4. Enable 'Add Photos Only' or 'Read and Write' permission")
        print()
        print("Alternatively, you can reset permissions:")
        print("  tccutil reset Photos")
        print()
        # Try to open System Settings
        try:
            NSWorkspace.sharedWorkspace().openURL_(
                NSWorkspace.sharedWorkspace().URLForApplicationWithBundleIdentifier_(
                    "com.apple.systempreferences"
                )
            )
            print("Opening System Settings...")
        except:
            pass
        return False
    elif current_status == PHAuthorizationStatusNotDetermined:
        print("Requesting permission...")
        print("You should see a permission dialog. Please click 'OK' or 'Allow'")
        print()
        
        # Request permission
        from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSDate
        import time
        
        auth_status = [None]
        callback_called = [False]
        
        def request_callback(status):
            auth_status[0] = status
            callback_called[0] = True
        
        PHPhotoLibrary.requestAuthorization_(request_callback)
        
        # Wait for callback
        timeout = 60  # Give user time to respond
        start_time = time.time()
        print("Waiting for permission response (up to 60 seconds)...")
        
        while not callback_called[0] and (time.time() - start_time) < timeout:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                NSDefaultRunLoopMode,
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
            time.sleep(0.1)
        
        if not callback_called[0]:
            print("⚠️  Permission request timed out")
            print()
            print("The permission dialog may not have appeared.")
            print("Please manually grant permission:")
            print("1. Open System Settings > Privacy & Security > Photos")
            print("2. Add Terminal or Python to the list")
            print("3. Enable 'Add Photos Only' permission")
            return False
        
        status = auth_status[0]
        if status == PHAuthorizationStatusAuthorized or status == PHAuthorizationStatusLimited:
            print("✓ Photo library permission granted!")
            return True
        else:
            print("❌ Photo library permission denied")
            print()
            print("To grant permission manually:")
            print("1. Open System Settings > Privacy & Security > Photos")
            print("2. Find 'Terminal' or 'Python' in the list")
            print("3. Enable 'Add Photos Only' or 'Read and Write' permission")
            return False
    else:
        print(f"⚠️  Unknown authorization status: {current_status}")
        return False

if __name__ == "__main__":
    success = request_permission()
    print()
    if success:
        print("✓ You can now run the migration script!")
        sys.exit(0)
    else:
        print("❌ Please grant permission and try again")
        sys.exit(1)

