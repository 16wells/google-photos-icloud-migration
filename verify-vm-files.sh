#!/bin/bash
#
# Quick verification script for VM files
# Run this on your VM to check if files match expected versions
#

echo "=========================================="
echo "VM File Verification"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "icloud_uploader.py" ]; then
    echo "Error: icloud_uploader.py not found in current directory"
    echo "Current directory: $(pwd)"
    echo "Please run this script from the directory containing the files"
    exit 1
fi

echo "Checking icloud_uploader.py..."
echo ""

# Key patterns that should exist in the updated version
CHECKS_PASSED=0
CHECKS_FAILED=0

check_pattern() {
    local pattern="$1"
    local description="$2"
    
    if grep -q "$pattern" icloud_uploader.py 2>/dev/null; then
        echo "✓ $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo "✗ $description - NOT FOUND"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Check for key changes
check_pattern "manual_service_creation = False" \
    "manual_service_creation initialized at method level"

check_pattern "# If 2FA was detected in exception handler, handle it now" \
    "2FA handling after exception handlers"

check_pattern "if needs_2fa and hasattr(self, 'api') and self.api is not None:" \
    "2FA check after exception handlers"

check_pattern "if manual_service_creation:" \
    "Check for manual service creation flag"

check_pattern "self.api._authenticate()" \
    "Trigger authentication to populate devices"

check_pattern "Available trusted devices:" \
    "Device selection prompt"

check_pattern "Enter 2FA code (attempt" \
    "2FA code entry prompt"

check_pattern "if not is_2fa and (\"PyiCloud2FARequiredException\" in tb_str" \
    "2FA detection from traceback"

echo ""
echo "=========================================="
echo "Verification Results"
echo "=========================================="
echo "Passed: $CHECKS_PASSED"
echo "Failed: $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✓ All checks passed! Files are up to date."
    exit 0
else
    echo "✗ Some checks failed. Files may need to be updated."
    echo ""
    echo "To update files, run from your local machine:"
    echo "  ./sync-to-vm.sh photos-migration-vm"
    echo ""
    echo "Or use gcloud:"
    echo "  gcloud compute scp icloud_uploader.py main.py photos-migration-vm:~/"
    exit 1
fi

