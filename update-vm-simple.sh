#!/bin/bash
# Simple script to update files on GCP VM using gcloud

VM_NAME="photos-migration-vm"
ZONE="us-central1-c"

echo "Updating files on GCP VM..."
echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo ""

# Update icloud_uploader.py (or both files if main.py also needs updating)
gcloud compute scp icloud_uploader.py ${VM_NAME}:~/ --zone=${ZONE}

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Successfully updated icloud_uploader.py on VM!"
    echo ""
    echo "To verify on the VM, run:"
    echo "  ssh ${VM_NAME}"
    echo "  grep -n 'No trusted devices found' icloud_uploader.py"
else
    echo ""
    echo "✗ Update failed. Try:"
    echo "  1. Check gcloud is configured: gcloud auth list"
    echo "  2. Use browser SSH in GCP Console to manually copy the file"
fi

