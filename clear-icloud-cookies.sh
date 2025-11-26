#!/bin/bash
# Script to clear iCloud authentication cookies
# This can help resolve authentication issues

echo "Clearing iCloud authentication cookies..."
echo ""

COOKIE_DIR="$HOME/.pyicloud"

if [ -d "$COOKIE_DIR" ]; then
    echo "Found cookie directory: $COOKIE_DIR"
    echo "Removing..."
    rm -rf "$COOKIE_DIR"
    echo "✓ Cookies cleared!"
else
    echo "No cookie directory found at $COOKIE_DIR"
fi

echo ""
echo "You can now try running the migration script again:"
echo "  python3 main.py --config config.yaml"
echo ""


