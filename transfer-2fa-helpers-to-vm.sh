#!/bin/bash
#
# Transfer 2FA helper scripts to VM
# This script transfers the new helper files needed for VM 2FA setup
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Transfer 2FA Helper Scripts to VM${NC}"
echo "========================================"
echo ""

# New helper files to transfer
HELPER_FILES=(
    "setup-vm-2fa.sh"
    "check-auth-status.py"
    "request-2fa-code.py"
    "VM_2FA_SETUP.md"
)

# Check if files exist
MISSING_FILES=()
for file in "${HELPER_FILES[@]}"; do
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

echo -e "${BLUE}Files to transfer:${NC}"
for file in "${HELPER_FILES[@]}"; do
    echo "  ✓ $file"
done
echo ""

# Get VM details
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 [vm-instance-name] [zone]"
    echo ""
    echo "Examples:"
    echo "  $0 photos-migration-vm us-central1-c"
    echo ""
    echo -e "${YELLOW}Or use Browser SSH method (recommended if gcloud doesn't work):${NC}"
    echo "  See instructions below"
    echo ""
    exit 1
fi

VM_NAME="$1"
ZONE="${2:-us-central1-c}"

echo -e "${BLUE}VM Details:${NC}"
echo "  Name: $VM_NAME"
echo "  Zone: $ZONE"
echo ""

# Try gcloud compute scp first
if command -v gcloud &> /dev/null; then
    echo -e "${GREEN}Attempting transfer via gcloud compute scp...${NC}"
    if gcloud compute scp "${HELPER_FILES[@]}" "$VM_NAME:~/ --zone=$ZONE" 2>&1; then
        echo ""
        echo -e "${GREEN}✓ Successfully transferred all files!${NC}"
        echo ""
        echo "To use on the VM:"
        echo "  bash setup-vm-2fa.sh"
        echo "  python3 check-auth-status.py"
        echo "  python3 request-2fa-code.py"
        exit 0
    else
        echo -e "${YELLOW}gcloud scp failed. Trying alternative methods...${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}gcloud not found. Using alternative methods...${NC}"
    echo ""
fi

# If gcloud failed, provide manual instructions
echo -e "${CYAN}Alternative Transfer Methods:${NC}"
echo "========================================"
echo ""
echo -e "${GREEN}Method 1: GCP Console Browser SSH (Recommended)${NC}"
echo "--------------------------------------------------------"
echo "1. Open: https://console.cloud.google.com/compute/instances"
echo "2. Find '$VM_NAME' and click the 'SSH' button"
echo "3. In the browser terminal, run these commands:"
echo ""
for file in "${HELPER_FILES[@]}"; do
    echo -e "${YELLOW}   # Transfer $file${NC}"
    echo "   cat > $file << 'ENDOFFILE'"
    echo "   # [Paste file contents here]"
    echo "   ENDOFFILE"
    echo ""
done
echo "   chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py"
echo ""

echo -e "${GREEN}Method 2: Copy file contents individually${NC}"
echo "--------------------------------------------------------"
echo "For each file, you can:"
echo ""
echo "1. Display the file contents on your local machine:"
echo "   cat setup-vm-2fa.sh"
echo ""
echo "2. Copy the output and paste into Browser SSH:"
echo "   cat > setup-vm-2fa.sh << 'ENDOFFILE'"
echo "   [paste contents]"
echo "   ENDOFFILE"
echo ""
echo "3. Make scripts executable:"
echo "   chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py"
echo ""

echo -e "${GREEN}Method 3: Create transfer script${NC}"
echo "--------------------------------------------------------"
echo "I can create a Python script that you can paste into Browser SSH."
echo "Run this command to generate it:"
echo ""
echo "   cat > create-file-transfer.py << 'ENDOFFILE'"
echo ""
echo -e "${YELLOW}Then paste this Python script (see below)...${NC}"
echo ""

# Create a Python script that can be pasted
cat > /tmp/transfer_helpers.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""
Transfer helper files to VM by pasting this script into Browser SSH
"""
import base64
from pathlib import Path

# File contents will be base64 encoded here
# This is just a template - the actual files need to be encoded

files = {
    "setup-vm-2fa.sh": "BASE64_ENCODED_CONTENT_HERE",
    "check-auth-status.py": "BASE64_ENCODED_CONTENT_HERE", 
    "request-2fa-code.py": "BASE64_ENCODED_CONTENT_HERE",
    "VM_2FA_SETUP.md": "BASE64_ENCODED_CONTENT_HERE",
}

for filename, content_b64 in files.items():
    if content_b64 == "BASE64_ENCODED_CONTENT_HERE":
        print(f"⚠ {filename}: Not encoded yet")
    else:
        try:
            content = base64.b64decode(content_b64).decode('utf-8')
            Path(filename).write_text(content)
            print(f"✓ Created {filename}")
        except Exception as e:
            print(f"✗ Error creating {filename}: {e}")

print("\nMaking scripts executable...")
import os
os.chmod("setup-vm-2fa.sh", 0o755)
os.chmod("check-auth-status.py", 0o755) 
os.chmod("request-2fa-code.py", 0o755)
print("✓ Done!")
PYTHON_SCRIPT

echo "Python transfer template created at: /tmp/transfer_helpers.py"
echo ""
echo -e "${GREEN}Quick Copy Commands (for Browser SSH):${NC}"
echo "--------------------------------------------------------"
echo ""
echo "Copy and paste these commands one at a time into Browser SSH:"
echo ""

for file in "${HELPER_FILES[@]}"; do
    echo -e "${YELLOW}# Transfer $file${NC}"
    echo "cat > $file << 'ENDOFFILE'"
    echo "# [Run 'cat $file' locally and paste contents here]"
    echo "ENDOFFILE"
    echo ""
done

echo "chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py"
echo ""

echo -e "${BLUE}Tip:${NC} You can also use the existing sync script:"
echo "  ./sync-to-vm.sh $VM_NAME"
echo "  (But you'll need to add these files to it first)"
echo ""

