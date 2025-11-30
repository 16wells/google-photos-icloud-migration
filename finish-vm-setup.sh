#!/bin/bash
# Script to finish VM setup - install ExifTool and set up config.yaml

set -e

VM_NAME="${1:-photos-migration-vm}"
ZONE="${2}"

echo "=== Finishing VM Setup ==="
echo ""

# Find zone if not provided
if [ -z "$ZONE" ]; then
    ZONE=$(gcloud compute instances list --filter="name:$VM_NAME" --format="value(zone)" | head -1)
    if [ -z "$ZONE" ]; then
        echo "❌ Could not find VM: $VM_NAME"
        exit 1
    fi
fi

echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo ""

# Install ExifTool
echo "=== Installing ExifTool ==="
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    if command -v exiftool &> /dev/null; then
        echo '✓ ExifTool already installed'
        exiftool -ver
    else
        echo 'Installing ExifTool...'
        sudo apt-get update
        sudo apt-get install -y libimage-exiftool-perl
        echo '✓ ExifTool installed'
        exiftool -ver
    fi
" 2>&1

echo ""

# Set up config.yaml
echo "=== Setting up config.yaml ==="
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    cd ~
    
    if [ -f config.yaml ]; then
        echo '✓ config.yaml already exists'
    elif [ -f config.yaml.example ]; then
        echo 'Copying config.yaml.example to config.yaml...'
        cp config.yaml.example config.yaml
        echo '✓ config.yaml created'
        echo ''
        echo '⚠️  IMPORTANT: You need to edit config.yaml with your settings:'
        echo '   - Google Drive credentials file path'
        echo '   - Apple ID and password'
        echo '   - Processing directories'
        echo ''
        echo 'To edit: nano config.yaml'
    else
        echo '❌ config.yaml.example not found'
        echo 'Available files:'
        ls -la *.yaml *.example 2>/dev/null || ls -la
    fi
" 2>&1

echo ""

# Final verification
echo "=== Final Verification ==="
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    echo 'Checking setup...'
    echo ''
    
    # Check ExifTool
    if command -v exiftool &> /dev/null; then
        echo '✓ ExifTool: $(exiftool -ver)'
    else
        echo '❌ ExifTool: NOT installed'
    fi
    
    # Check config.yaml
    if [ -f config.yaml ]; then
        echo '✓ config.yaml: Found'
    else
        echo '❌ config.yaml: NOT found'
    fi
    
    # Check Python dependencies
    if python3 -c 'import yaml, google' 2>/dev/null; then
        echo '✓ Python dependencies: Installed'
    else
        echo '⚠️  Python dependencies: May need installation'
        echo '   Run: pip3 install -r requirements.txt --user'
    fi
    
    # Check main files
    [ -f main.py ] && echo '✓ main.py: Found' || echo '❌ main.py: NOT found'
    [ -f credentials.json ] && echo '✓ credentials.json: Found' || echo '❌ credentials.json: NOT found'
    
    echo ''
    echo '=== Next Steps ==='
    echo '1. SSH into VM: gcloud compute ssh $VM_NAME --zone=$ZONE'
    echo '2. Edit config.yaml: nano config.yaml'
    echo '3. Update these settings:'
    echo '   - google_drive.credentials_file: \"credentials.json\"'
    echo '   - icloud.apple_id: \"your-apple-id@example.com\"'
    echo '   - icloud.password: \"\" (leave empty to be prompted)'
    echo '   - processing.base_dir: \"/tmp/google-photos-migration\"'
    echo '4. Run migration: python3 main.py --config config.yaml'
" 2>&1

echo ""
echo "✓ Setup complete!"
echo ""
echo "To SSH into VM and configure:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"

