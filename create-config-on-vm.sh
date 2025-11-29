#!/bin/bash
# Script to create config.yaml on VM with basic settings

set -e

VM_NAME="${1:-photos-migration-vm}"
ZONE="${2}"
APPLE_ID="${3}"

echo "=== Creating config.yaml on VM ==="
echo ""

# Find zone if not provided
if [ -z "$ZONE" ]; then
    ZONE=$(gcloud compute instances list --filter="name:$VM_NAME" --format="value(zone)" | head -1)
    if [ -z "$ZONE" ]; then
        echo "❌ Could not find VM: $VM_NAME"
        exit 1
    fi
fi

# Create config.yaml on VM
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    cd ~
    
    if [ -f config.yaml.example ]; then
        cp config.yaml.example config.yaml
        
        # Update basic settings
        sed -i 's|your-apple-id@example.com|${APPLE_ID:-your-apple-id@example.com}|g' config.yaml
        sed -i 's|credentials_file: \".*\"|credentials_file: \"credentials.json\"|g' config.yaml
        sed -i 's|base_dir: \".*\"|base_dir: \"/tmp/google-photos-migration\"|g' config.yaml
        
        echo '✓ config.yaml created from template'
        echo ''
        echo 'Current settings:'
        grep -E '(apple_id|credentials_file|base_dir)' config.yaml | head -5
        echo ''
        echo '⚠️  Please review and edit config.yaml:'
        echo '   nano config.yaml'
    else
        echo '❌ config.yaml.example not found'
        exit 1
    fi
" 2>&1

echo ""
echo "✓ Config file created!"
echo ""
echo "To edit it:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "  nano config.yaml"

