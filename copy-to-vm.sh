#!/bin/bash
# Simple script to copy updated files to VM
# Run this from your Mac terminal

echo "Copying updated files to VM..."
echo "Make sure you're running this from your Mac, not from the VM!"
echo ""

# Replace with your VM's IP address if hostname doesn't work
VM_HOST="${1:-skipshean@34.56.47.252}"

echo "Copying to: $VM_HOST"
scp main.py drive_downloader.py "$VM_HOST:~/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Files copied successfully!"
    echo ""
    echo "Now SSH into your VM and verify:"
    echo "  ssh $VM_HOST"
    echo "  grep -n '_find_existing_zips' main.py"
    echo "  python3 main.py --config config.yaml"
else
    echo ""
    echo "✗ Copy failed. Make sure:"
    echo "  1. You're running this from your Mac (not the VM)"
    echo "  2. You have SSH access to the VM"
    echo "  3. The IP address is correct"
fi

