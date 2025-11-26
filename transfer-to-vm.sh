#!/bin/bash
# Transfer file to VM using gcloud compute ssh with base64 encoding
# This works around SSH key authentication issues

VM_NAME="photos-migration-vm"
ZONE="us-central1-c"
FILE="icloud_uploader.py"

if [ ! -f "$FILE" ]; then
    echo "Error: $FILE not found"
    exit 1
fi

echo "Transferring $FILE to VM using base64 encoding..."
echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo ""

# Encode file to base64 and transfer via SSH command
gcloud compute ssh $VM_NAME --zone=$ZONE --command="cat > $FILE << 'EOF'
$(cat $FILE)
EOF
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Successfully transferred $FILE to VM!"
    echo ""
    echo "To verify on the VM, run:"
    echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo "  grep -n 'No trusted devices found' $FILE"
else
    echo ""
    echo "✗ Transfer failed. Alternative methods:"
    echo ""
    echo "1. Use GCP Console Browser SSH:"
    echo "   - Go to: https://console.cloud.google.com/compute/instances"
    echo "   - Click 'SSH' next to $VM_NAME"
    echo "   - Copy/paste the file contents"
    echo ""
    echo "2. Manual copy via gcloud compute ssh:"
    echo "   gcloud compute ssh $VM_NAME --zone=$ZONE"
    echo "   # Then manually edit the file"
fi

