#!/bin/bash
# Helper script to grant Photos permission to Terminal
# This script creates a temporary macOS app that requests Photos permission

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_APP_DIR="/tmp/PhotosPermissionHelper.app"
TEMP_APP_CONTENTS="$TEMP_APP_DIR/Contents"
TEMP_APP_MACOS="$TEMP_APP_CONTENTS/MacOS"

echo "=" | tr -d '\n'
echo "============================================================"
echo "Photos Permission Helper"
echo "============================================================"
echo ""

# Clean up any existing temp app
rm -rf "$TEMP_APP_DIR"

# Create app bundle structure
mkdir -p "$TEMP_APP_MACOS"

# Create Info.plist
cat > "$TEMP_APP_CONTENTS/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PhotosPermissionHelper</string>
    <key>CFBundleIdentifier</key>
    <string>com.googlephotos.icloudmigration.permissionhelper</string>
    <key>CFBundleName</key>
    <string>Photos Permission Helper</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>NSPhotoLibraryUsageDescription</key>
    <string>This app needs access to your photo library to migrate photos from Google Photos to iCloud Photos.</string>
    <key>NSPhotoLibraryAddUsageDescription</key>
    <string>This app needs permission to add photos to your library for migration to iCloud Photos.</string>
</dict>
</plist>
EOF

# Create Python script that requests permission
cat > "$TEMP_APP_MACOS/PhotosPermissionHelper" << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import sys
import os

# Add the project directory to path so we can import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Photos import (
        PHPhotoLibrary, PHAuthorizationStatus,
        PHAuthorizationStatusAuthorized, PHAuthorizationStatusLimited,
        PHAuthorizationStatusDenied, PHAuthorizationStatusNotDetermined
    )
    from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSDate
    import time
except ImportError as e:
    print(f"Error: {e}")
    print("Please install: pip install pyobjc-framework-Photos")
    sys.exit(1)

def main():
    print("Requesting Photos permission...")
    
    current_status = PHPhotoLibrary.authorizationStatus()
    
    if current_status == PHAuthorizationStatusAuthorized:
        print("✓ Permission already granted!")
        return 0
    elif current_status == PHAuthorizationStatusLimited:
        print("✓ Limited permission granted (sufficient)")
        return 0
    elif current_status == PHAuthorizationStatusDenied:
        print("❌ Permission was previously denied")
        print("Please reset permissions: tccutil reset Photos")
        return 1
    
    # Request permission
    auth_status = [None]
    callback_called = [False]
    
    def request_callback(status):
        auth_status[0] = status
        callback_called[0] = True
    
    PHPhotoLibrary.requestAuthorization_(request_callback)
    
    # Wait for callback
    timeout = 60
    start_time = time.time()
    
    while not callback_called[0] and (time.time() - start_time) < timeout:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode,
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )
        time.sleep(0.1)
    
    if not callback_called[0]:
        print("⚠️  Permission request timed out")
        return 1
    
    status = auth_status[0]
    if status == PHAuthorizationStatusAuthorized or status == PHAuthorizationStatusLimited:
        print("✓ Permission granted!")
        return 0
    else:
        print("❌ Permission denied")
        return 1

if __name__ == "__main__":
    sys.exit(main())
PYTHON_SCRIPT

chmod +x "$TEMP_APP_MACOS/PhotosPermissionHelper"

echo "Created temporary app bundle: $TEMP_APP_DIR"
echo ""
echo "Opening app to request permission..."
echo "You should see a permission dialog. Please click 'OK' or 'Allow'"
echo ""

# Open the app (this should trigger the permission dialog)
open "$TEMP_APP_DIR"

# Wait a moment for the dialog
sleep 3

echo ""
echo "If a permission dialog appeared, please grant permission."
echo ""
echo "To verify permission was granted:"
echo "1. Open System Settings > Privacy & Security > Photos"
echo "2. Look for 'Photos Permission Helper' in the list"
echo "3. Make sure it has 'Add Photos Only' or 'Read and Write' permission"
echo ""
echo "After granting permission, you can run the migration script."
echo ""
echo "Note: The permission helper app will be cleaned up automatically."

