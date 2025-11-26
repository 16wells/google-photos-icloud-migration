#!/bin/bash
#
# Safe VM transfer script - ensures files go to correct location
# Usage: ./vm-transfer-safe.sh [files...]
#

set -e

VM_NAME="photos-migration-vm"
ZONE="us-central1-c"
VM_USER="skipshean"
VM_HOME="/home/skipshean"

if [ $# -eq 0 ]; then
    echo "Usage: $0 [file1] [file2] ..."
    echo ""
    echo "Example:"
    echo "  $0 main.py icloud_uploader.py"
    echo ""
    echo "Files will be transferred to: $VM_HOME/"
    exit 1
fi

echo "Transferring files to VM..."
echo "  VM: $VM_NAME"
echo "  Zone: $ZONE"
echo "  Destination: $VM_HOME/"
echo "  Files: $@"
echo ""

# Transfer files
gcloud compute scp "$@" "$VM_NAME:$VM_HOME/" --zone="$ZONE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Files transferred successfully!"
    echo ""
    echo "To verify on VM, run:"
    echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='cd $VM_HOME && ls -lh $*'"
else
    echo ""
    echo "✗ Transfer failed"
    exit 1
fi
