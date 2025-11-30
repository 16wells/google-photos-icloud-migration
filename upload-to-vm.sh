#!/bin/bash
# Script to upload all necessary files to GCP VM

set -e

VM_NAME="${1:-photos-migration-vm}"
ZONE="${2}"
PROJECT_DIR="${3:-$HOME/Sites/google-photos-to-icloud-migration}"

echo "=== Uploading Files to GCP VM ==="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated. Running: gcloud auth login"
    gcloud auth login
fi

# Get project
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    echo "❌ No project set. Please set it:"
    echo "   gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Project: $PROJECT"

# Find zone if not provided
if [ -z "$ZONE" ]; then
    echo "Finding VM zone..."
    ZONE=$(gcloud compute instances list --filter="name:$VM_NAME" --format="value(zone)" | head -1)
    if [ -z "$ZONE" ]; then
        echo "❌ Could not find VM: $VM_NAME"
        echo "   Available VMs:"
        gcloud compute instances list --format="table(name,zone,status)"
        exit 1
    fi
fi

echo "VM: $VM_NAME"
echo "Zone: $ZONE"
echo ""

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Check if VM is running
STATUS=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="value(status)" 2>/dev/null)
if [ "$STATUS" != "RUNNING" ]; then
    echo "Starting VM..."
    gcloud compute instances start $VM_NAME --zone=$ZONE
    echo "Waiting for VM to start..."
    sleep 15
fi

echo "Uploading files..."
echo ""

# Upload files one by one with progress
FILES=(
    "main.py"
    "drive_downloader.py"
    "extractor.py"
    "metadata_merger.py"
    "album_parser.py"
    "icloud_uploader.py"
    "requirements.txt"
    "setup.sh"
    "config.yaml.example"
    "README.md"
    "GCP_SETUP.md"
    "TESTING.md"
    "QUICKSTART.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Uploading $file..."
        gcloud compute scp "$file" ${VM_NAME}:~/ --zone=$ZONE || echo "⚠️  Failed to upload $file"
    else
        echo "⚠️  File not found: $file"
    fi
done

# Upload credentials.json if it exists (but don't fail if it doesn't)
if [ -f "credentials.json" ]; then
    echo "Uploading credentials.json..."
    gcloud compute scp credentials.json ${VM_NAME}:~/ --zone=$ZONE
else
    echo "⚠️  credentials.json not found (you'll need to upload this separately)"
fi

# Upload config.yaml if it exists
if [ -f "config.yaml" ]; then
    echo "Uploading config.yaml..."
    gcloud compute scp config.yaml ${VM_NAME}:~/ --zone=$ZONE
else
    echo "⚠️  config.yaml not found (copy from config.yaml.example on VM)"
fi

echo ""
echo "=== Setting up on VM ==="
echo ""

# Run setup commands on VM
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    echo 'Making setup.sh executable...'
    chmod +x ~/setup.sh 2>/dev/null || true
    
    echo 'Checking Python dependencies...'
    if ! python3 -c 'import yaml' 2>/dev/null; then
        echo 'Installing Python dependencies...'
        pip3 install -r ~/requirements.txt --user
    else
        echo 'Python dependencies already installed'
    fi
    
    echo ''
    echo 'Files uploaded to: ~/'
    echo 'To verify, run: ls -la ~/'
" 2>&1

echo ""
echo "✓ Upload complete!"
echo ""
echo "Next steps:"
echo "1. SSH into VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "2. Copy config.yaml.example to config.yaml and edit it"
echo "3. Run: python3 main.py --config config.yaml"
echo ""
echo "Or run verification: ./verify-vm-setup.sh $VM_NAME $ZONE"

