#!/bin/bash
# Clear PhotoKit permission cache (if needed)
# Note: PhotoKit doesn't use cookies like the old API method did.
# This script is kept for reference but may not be needed anymore.

echo "PhotoKit Permission Cache Cleanup"
echo "=================================="
echo ""
echo "Note: PhotoKit doesn't use authentication cookies."
echo "      This tool uses your macOS iCloud account automatically."
echo ""
echo "If you're having permission issues, try:"
echo "  1. Run: python3 request_photos_permission.py"
echo "  2. Or manually grant permission in:"
echo "     System Settings > Privacy & Security > Photos"
echo ""

# The old .pyicloud cookie directory is no longer used
COOKIE_DIR="$HOME/.pyicloud"

if [ -d "$COOKIE_DIR" ]; then
    echo "⚠️  Found old .pyicloud directory: $COOKIE_DIR"
    echo "   This directory is no longer used by this tool."
    echo "   It was used by the old API upload method (now removed)."
    echo ""
    read -p "Do you want to delete it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$COOKIE_DIR"
        echo "✓ Deleted $COOKIE_DIR"
    else
        echo "Skipped deletion."
    fi
else
    echo "✓ No old cookie directory found"
fi

echo ""
echo "PhotoKit permission is managed through macOS System Settings."
echo "To reset Photos permission, revoke and re-grant in:"
echo "  System Settings > Privacy & Security > Photos"
