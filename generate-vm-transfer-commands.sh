#!/bin/bash
#
# Generate ready-to-paste commands for Browser SSH
# This creates commands you can copy and paste into Browser SSH to create the files
#

set -e

HELPER_FILES=(
    "setup-vm-2fa.sh"
    "check-auth-status.py"
    "request-2fa-code.py"
    "VM_2FA_SETUP.md"
)

echo "=========================================="
echo "Browser SSH Transfer Commands"
echo "=========================================="
echo ""
echo "Copy these commands and paste them into Browser SSH one at a time:"
echo ""
echo ""

for file in "${HELPER_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "# ERROR: $file not found, skipping..."
        continue
    fi
    
    echo "##################################################"
    echo "# Transfer $file"
    echo "##################################################"
    echo "cat > $file << 'ENDOFFILE'"
    cat "$file"
    echo "ENDOFFILE"
    echo ""
    echo ""
done

echo "##################################################"
echo "# Make scripts executable"
echo "##################################################"
echo "chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py"
echo ""
echo ""
echo "##################################################"
echo "# Verify files were created"
echo "##################################################"
echo "ls -lh setup-vm-2fa.sh check-auth-status.py request-2fa-code.py VM_2FA_SETUP.md"
echo ""
echo ""

