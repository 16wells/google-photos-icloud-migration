#!/bin/bash
# Script to help recover config.yaml

echo "=== Config Recovery Helper ==="
echo ""

# Check if config.yaml.example exists
if [ -f config.yaml.example ]; then
    echo "✓ Found config.yaml.example"
    echo ""
    echo "To recreate config.yaml:"
    echo "  cp config.yaml.example config.yaml"
    echo "  nano config.yaml"
    echo ""
    echo "Then update these settings:"
    echo "  - google_drive.folder_id: Your Google Drive folder ID"
    echo "  - google_drive.zip_file_pattern: 'takeout-*.zip'"
    echo "  - icloud.apple_id: Your Apple ID email"
    echo "  - icloud.password: '' (empty to be prompted)"
    echo "  - processing.base_dir: '/tmp/google-photos-migration'"
else
    echo "✗ config.yaml.example not found"
fi

echo ""
echo "=== Important Notes ==="
echo "1. The zip files are still in Google Drive - we only deleted local copies"
echo "2. They will be re-downloaded when you run the migration again"
echo "3. Make sure your folder_id in config.yaml points to the correct folder"

