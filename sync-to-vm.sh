#!/bin/bash
#
# Sync updated files to GCP VM
# This script helps update the migration tool files on your VM
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Google Photos Migration - VM Sync Script${NC}"
echo "=========================================="
echo ""

# Check if VM connection details are provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage:${NC}"
    echo "  ./sync-to-vm.sh [vm-instance-name] [vm-path]"
    echo ""
    echo "Examples:"
    echo "  ./sync-to-vm.sh photos-migration-vm"
    echo "  ./sync-to-vm.sh photos-migration-vm /home/skipshean"
    echo ""
    echo "For GCP VMs, use the instance name (not IP or hostname)"
    echo "The script will automatically detect it's a GCP VM and use gcloud"
    echo ""
    echo -e "${YELLOW}Alternative: Manual sync instructions${NC}"
    echo "If you prefer to copy files manually:"
    echo ""
    echo "1. Files to update:"
    echo "   - main.py"
    echo "   - icloud_uploader.py"
    echo ""
    echo "2. Copy using scp:"
    echo "   scp main.py icloud_uploader.py [user@]hostname:~/"
    echo ""
    echo "3. Or use rsync:"
    echo "   rsync -avz main.py icloud_uploader.py [user@]hostname:~/"
    echo ""
    exit 1
fi

VM_HOST="$1"
VM_PATH="${2:-~}"

# Files to sync (only the updated ones)
FILES=(
    "main.py"
    "icloud_uploader.py"
)

echo -e "${GREEN}Syncing files to VM...${NC}"
echo "VM: $VM_HOST"
echo "Path: $VM_PATH"
echo ""

# Check if files exist
MISSING_FILES=()
for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing files:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    exit 1
fi

# Extract VM name (remove user@ if present)
VM_NAME=$(echo "$VM_HOST" | sed 's/.*@//')

# Check if gcloud is available and try GCP first
USE_GCLOUD=false
if command -v gcloud &> /dev/null; then
    # Check if VM exists in GCP
    if gcloud compute instances describe "$VM_NAME" &>/dev/null 2>&1; then
        USE_GCLOUD=true
    fi
fi

if [ "$USE_GCLOUD" = true ]; then
    echo -e "${GREEN}Detected GCP VM. Using gcloud compute scp...${NC}"
    # Get zone
    ZONE=$(gcloud compute instances list --filter="name:$VM_NAME" --format="value(zone)" 2>/dev/null | head -1)
    if [ -n "$ZONE" ]; then
        echo "Zone: $ZONE"
        if gcloud compute scp "${FILES[@]}" "$VM_NAME:$VM_PATH/" --zone="$ZONE"; then
            echo ""
            echo -e "${GREEN}✓ Files synced successfully!${NC}"
            exit 0
        else
            echo -e "${YELLOW}gcloud scp failed. Trying alternative methods...${NC}"
        fi
    else
        echo -e "${YELLOW}Could not determine zone. Trying without zone...${NC}"
        if gcloud compute scp "${FILES[@]}" "$VM_NAME:$VM_PATH/"; then
            echo ""
            echo -e "${GREEN}✓ Files synced successfully!${NC}"
            exit 0
        else
            echo -e "${YELLOW}gcloud scp failed. Trying alternative methods...${NC}"
        fi
    fi
fi

# Fall back to standard methods
if command -v rsync &> /dev/null; then
    echo -e "${GREEN}Using rsync...${NC}"
    if rsync -avz --progress "${FILES[@]}" "$VM_HOST:$VM_PATH/"; then
        echo ""
        echo -e "${GREEN}✓ Files synced successfully!${NC}"
        exit 0
    fi
fi

if command -v scp &> /dev/null; then
    echo -e "${GREEN}Using scp...${NC}"
    if scp "${FILES[@]}" "$VM_HOST:$VM_PATH/"; then
        echo ""
        echo -e "${GREEN}✓ Files synced successfully!${NC}"
        exit 0
    fi
fi

echo -e "${RED}Error: All sync methods failed.${NC}"
echo ""
echo -e "${YELLOW}Alternative: Manual copy instructions${NC}"
echo "Try one of these:"
echo ""
echo "1. Using gcloud directly:"
echo "   gcloud compute scp main.py icloud_uploader.py photos-migration-vm:~/ --zone=us-central1-c"
echo ""
echo "2. Using the VM's IP address:"
echo "   scp main.py icloud_uploader.py skipshean@34.56.47.252:~/"
echo ""
echo "3. SSH into VM and manually edit files"
exit 1

echo ""
echo -e "${YELLOW}Next steps on VM:${NC}"
echo "1. Verify files were updated:"
echo "   ls -lh main.py icloud_uploader.py"
echo ""
echo "2. Run the migration script:"
echo "   python3 main.py --config config.yaml"
echo ""
echo -e "${GREEN}The updated script will:${NC}"
echo "  - Verify each file upload to iCloud"
echo "  - Prompt user on verification failures (A/B/I options)"
echo "  - Track failed uploads for retry"
echo ""

