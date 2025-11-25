#!/bin/bash
# Script to verify VM setup and diagnose issues

set -e

VM_NAME="${1:-photos-migration-vm}"
ZONE="${2}"

echo "=== Google Cloud VM Setup Verification ==="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed"
    echo "   Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✓ gcloud CLI found"

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud"
    echo "   Run: gcloud auth login"
    exit 1
fi

echo "✓ Authenticated with gcloud"

# Get current project
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
    echo "❌ No project set"
    echo "   Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "✓ Project: $PROJECT"

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

echo "✓ Zone: $ZONE"

# Check VM status
STATUS=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format="value(status)" 2>/dev/null)
if [ -z "$STATUS" ]; then
    echo "❌ Cannot access VM: $VM_NAME"
    exit 1
fi

echo "✓ VM Status: $STATUS"

if [ "$STATUS" != "RUNNING" ]; then
    echo "⚠️  VM is not running. Starting VM..."
    gcloud compute instances start $VM_NAME --zone=$ZONE
    echo "Waiting for VM to start..."
    sleep 10
fi

echo ""
echo "=== Checking Files on VM ==="
echo ""

# Check if files exist
echo "Checking home directory..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="ls -la ~/" 2>&1 | head -20

echo ""
echo "Checking for project files..."
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    if [ -d ~/Sites/google-photos-to-icloud-migration ]; then
        echo 'Found in ~/Sites/google-photos-to-icloud-migration:'
        ls -la ~/Sites/google-photos-to-icloud-migration/
    elif [ -d ~/google-photos-to-icloud-migration ]; then
        echo 'Found in ~/google-photos-to-icloud-migration:'
        ls -la ~/google-photos-to-icloud-migration/
    else
        echo 'Project directory not found'
        echo 'Current directory contents:'
        ls -la ~/
    fi
" 2>&1

echo ""
echo "=== Checking Required Files ==="
echo ""

gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    echo 'Checking for credentials.json...'
    [ -f ~/credentials.json ] && echo '✓ credentials.json found' || echo '❌ credentials.json NOT found'
    [ -f ~/Sites/google-photos-to-icloud-migration/credentials.json ] && echo '✓ credentials.json found in Sites' || true
    
    echo 'Checking for config.yaml...'
    [ -f ~/config.yaml ] && echo '✓ config.yaml found' || echo '❌ config.yaml NOT found'
    [ -f ~/Sites/google-photos-to-icloud-migration/config.yaml ] && echo '✓ config.yaml found in Sites' || true
    
    echo 'Checking for main.py...'
    [ -f ~/main.py ] && echo '✓ main.py found' || echo '❌ main.py NOT found'
    [ -f ~/Sites/google-photos-to-icloud-migration/main.py ] && echo '✓ main.py found in Sites' || true
    
    echo 'Checking Python...'
    python3 --version 2>/dev/null && echo '✓ Python3 installed' || echo '❌ Python3 NOT installed'
    
    echo 'Checking ExifTool...'
    exiftool -ver 2>/dev/null && echo '✓ ExifTool installed' || echo '❌ ExifTool NOT installed'
" 2>&1

echo ""
echo "=== Summary ==="
echo "VM Name: $VM_NAME"
echo "Zone: $ZONE"
echo "Project: $PROJECT"
echo "Status: $STATUS"
echo ""
echo "To SSH into the VM:"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE"
echo ""
echo "Or use the browser SSH button in Google Cloud Console"

