#!/bin/bash
# Comprehensive script to fix Photos permission issues on macOS

echo "============================================================"
echo "Photos Permission Fixer"
echo "============================================================"
echo ""

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ This script requires macOS"
    exit 1
fi

echo "This script will help you grant Photos permission to Terminal."
echo ""

# Step 1: Check current permission status
echo "Step 1: Checking current permission status..."
python3 << 'PYTHON_CHECK'
import sys
try:
    from Photos import PHPhotoLibrary, PHAuthorizationStatus
    from Photos import (
        PHAuthorizationStatusAuthorized, PHAuthorizationStatusLimited,
        PHAuthorizationStatusDenied, PHAuthorizationStatusNotDetermined
    )
    
    status = PHPhotoLibrary.authorizationStatus()
    
    if status == PHAuthorizationStatusAuthorized:
        print("✓ Permission already granted!")
        sys.exit(0)
    elif status == PHAuthorizationStatusLimited:
        print("✓ Limited permission granted (sufficient)")
        sys.exit(0)
    elif status == PHAuthorizationStatusDenied:
        print("❌ Permission was denied")
        sys.exit(1)
    elif status == PHAuthorizationStatusNotDetermined:
        print("⚠️  Permission not yet requested")
        sys.exit(2)
    else:
        print(f"⚠️  Unknown status: {status}")
        sys.exit(3)
except ImportError as e:
    print(f"❌ Error: {e}")
    print("Please install: pip install pyobjc-framework-Photos")
    sys.exit(4)
PYTHON_CHECK

CHECK_RESULT=$?

if [ $CHECK_RESULT -eq 0 ]; then
    echo ""
    echo "✓ Permission is already granted! You're all set."
    exit 0
fi

echo ""
echo "Step 2: Opening System Settings to Photos privacy section..."
echo ""

# Try to open System Settings directly to Photos privacy
# On macOS Ventura and later
if open "x-apple.systempreferences:com.apple.preference.security?Privacy_Photos" 2>/dev/null; then
    echo "✓ Opened System Settings to Photos privacy"
else
    # Fallback: open System Settings and navigate manually
    open "x-apple.systempreferences:com.apple.preference.security"
    echo "⚠️  Please navigate to: Privacy & Security > Photos"
fi

echo ""
echo "============================================================"
echo "MANUAL STEPS REQUIRED:"
echo "============================================================"
echo ""
echo "Since macOS doesn't always show permission dialogs for Terminal scripts,"
echo "you need to manually add Terminal to the Photos permission list:"
echo ""
echo "1. In System Settings, go to: Privacy & Security > Photos"
echo ""
echo "2. Look for 'Terminal' in the list of apps"
echo "   - If Terminal is NOT in the list, click the '+' button (if available)"
echo "   - Or try the workaround below"
echo ""
echo "3. Enable 'Add Photos Only' or 'Read and Write' permission for Terminal"
echo ""
echo "4. If Terminal is not listed and there's no '+' button, try this:"
echo "   a. Run this command to reset Photos permissions:"
echo "      sudo tccutil reset Photos"
echo "   b. Then run the migration script again"
echo "   c. When prompted, grant permission"
echo ""
echo "============================================================"
echo "WORKAROUND: Using Python directly"
echo "============================================================"
echo ""
echo "If Terminal permission doesn't work, try running Python directly:"
echo ""
echo "1. Find your Python executable:"
PYTHON_PATH=$(which python3)
echo "   $PYTHON_PATH"
echo ""
echo "2. Grant permission to Python instead:"
echo "   - In System Settings > Privacy & Security > Photos"
echo "   - Look for 'Python' in the list"
echo "   - Enable 'Add Photos Only' permission"
echo ""
echo "3. Then run the migration with the full Python path:"
echo "   $PYTHON_PATH process_local_zips.py --use-sync /path/to/zips"
echo ""
echo "============================================================"
echo "ALTERNATIVE: Reset and re-request permission"
echo "============================================================"
echo ""
echo "If nothing works, try resetting Photos permissions:"
echo ""
echo "1. Run: sudo tccutil reset Photos"
echo "2. Run: python3 request_photos_permission.py"
echo "3. Grant permission when prompted"
echo ""
echo "Note: You may need to enter your password for 'sudo'"
echo ""

