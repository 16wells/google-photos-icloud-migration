#!/bin/bash
# Script to fix SSH authentication for GCP VM
# This script helps diagnose and fix SSH key issues

VM_NAME="photos-migration-vm"
ZONE="us-central1-c"
PROJECT="photos-migration-2025"

echo "=== GCP VM SSH Authentication Fix ==="
echo ""
echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo "Project: $PROJECT"
echo ""

# Check current SSH keys
echo "1. Checking local SSH keys..."
if [ -f ~/.ssh/id_rsa.pub ]; then
    echo "   ✓ Found: ~/.ssh/id_rsa.pub"
    LOCAL_KEY=$(cat ~/.ssh/id_rsa.pub)
    echo "   Key fingerprint: $(echo "$LOCAL_KEY" | cut -d' ' -f2 | base64 -d 2>/dev/null | md5 2>/dev/null | cut -d' ' -f1 || echo 'N/A')"
else
    echo "   ✗ No SSH key found at ~/.ssh/id_rsa.pub"
    echo "   Generating new SSH key..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "$(whoami)@$(hostname)"
    LOCAL_KEY=$(cat ~/.ssh/id_rsa.pub)
fi

echo ""
echo "2. Checking VM metadata..."
CURRENT_METADATA=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="get(metadata.items[1].value)" 2>/dev/null)
if [ -n "$CURRENT_METADATA" ]; then
    echo "   ✓ VM has SSH keys in metadata"
    USERNAME=$(echo "$CURRENT_METADATA" | head -1 | cut -d: -f1)
    echo "   Username in metadata: $USERNAME"
else
    echo "   ✗ No SSH keys found in VM metadata"
    USERNAME="skipshean"
fi

echo ""
echo "3. Adding SSH key to VM metadata..."
# Get the current metadata value
CURRENT_SSH_KEYS=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="get(metadata.items[1].value)" 2>/dev/null)

# Create temp file with updated SSH keys
TEMP_FILE=$(mktemp)
if [ -n "$CURRENT_SSH_KEYS" ]; then
    # Append to existing keys
    echo "$CURRENT_SSH_KEYS" > "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
fi
echo "${USERNAME}:${LOCAL_KEY}" >> "$TEMP_FILE"

# Update metadata
gcloud compute instances add-metadata $VM_NAME --zone=$ZONE --metadata-from-file ssh-keys="$TEMP_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "   ✓ SSH key added to VM metadata"
    rm "$TEMP_FILE"
else
    echo "   ✗ Failed to add SSH key"
    rm "$TEMP_FILE"
    exit 1
fi

echo ""
echo "4. Waiting 10 seconds for metadata to propagate..."
sleep 10

echo ""
echo "5. Testing SSH connection..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="echo 'SSH connection successful!'" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ SSH authentication is now working!"
    echo ""
    echo "You can now transfer files using:"
    echo "  gcloud compute scp icloud_uploader.py $VM_NAME:~/ --zone=$ZONE"
else
    echo ""
    echo "✗ SSH still not working. Try these alternatives:"
    echo ""
    echo "Option 1: Use GCP Console Browser SSH"
    echo "  - Go to: https://console.cloud.google.com/compute/instances?project=$PROJECT"
    echo "  - Click 'SSH' button next to $VM_NAME"
    echo "  - This opens a browser-based terminal (no SSH keys needed)"
    echo ""
    echo "Option 2: Manual file transfer via Browser SSH"
    echo "  1. Open Browser SSH (see Option 1)"
    echo "  2. Run: nano icloud_uploader.py"
    echo "  3. Copy/paste the file contents from your local machine"
    echo ""
    echo "Option 3: Check VM username"
    echo "  The VM might be using a different username. Check with:"
    echo "  gcloud compute instances describe $VM_NAME --zone=$ZONE --format='get(metadata.items[1].value)'"
fi

