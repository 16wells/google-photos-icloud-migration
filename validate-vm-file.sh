#!/bin/bash
# Validation script to check if icloud_uploader.py on VM has the correct fixes
# Run this in Browser SSH on the VM

echo "=== Validating icloud_uploader.py on VM ==="
echo ""

FILE="icloud_uploader.py"

if [ ! -f "$FILE" ]; then
    echo "❌ ERROR: $FILE not found!"
    exit 1
fi

echo "✓ File exists: $FILE"
echo ""

# Check 1: Look for "No trusted devices found" error message
echo "Check 1: Looking for 'No trusted devices found' error message..."
if grep -q "No trusted devices found" "$FILE"; then
    echo "  ✓ Found: 'No trusted devices found' error message"
    COUNT=$(grep -c "No trusted devices found" "$FILE")
    echo "    Found $COUNT occurrence(s)"
else
    echo "  ❌ MISSING: 'No trusted devices found' error message"
fi
echo ""

# Check 2: Look for device list validation
echo "Check 2: Looking for device list validation..."
if grep -q "Ensure devices is a list" "$FILE"; then
    echo "  ✓ Found: Device list validation code"
else
    echo "  ❌ MISSING: Device list validation code"
fi
echo ""

# Check 3: Look for input validation loop
echo "Check 3: Looking for input validation loop..."
if grep -q "while True:" "$FILE" && grep -q "Select device (enter number" "$FILE"; then
    echo "  ✓ Found: Input validation loop for device selection"
else
    echo "  ❌ MISSING: Input validation loop"
fi
echo ""

# Check 4: Look for isinstance check
echo "Check 4: Looking for isinstance check..."
if grep -q "isinstance(devices, list)" "$FILE"; then
    echo "  ✓ Found: isinstance check for devices list"
else
    echo "  ❌ MISSING: isinstance check"
fi
echo ""

# Check 5: Look for empty list check
echo "Check 5: Looking for empty list check..."
if grep -q "if len(devices) == 0:" "$FILE"; then
    echo "  ✓ Found: Empty list check"
else
    echo "  ❌ MISSING: Empty list check"
fi
echo ""

# Check 6: Verify line count (should be around 455 lines)
LINE_COUNT=$(wc -l < "$FILE")
echo "Check 6: File line count..."
echo "  File has $LINE_COUNT lines"
if [ "$LINE_COUNT" -ge 450 ] && [ "$LINE_COUNT" -le 460 ]; then
    echo "  ✓ Line count looks correct (expected ~455 lines)"
else
    echo "  ⚠ Warning: Line count seems off (expected ~455 lines)"
fi
echo ""

# Check 7: Look for the specific fix around line 98-108
echo "Check 7: Looking for device selection validation code..."
if grep -A 5 "while True:" "$FILE" | grep -q "Select device (enter number"; then
    echo "  ✓ Found: Device selection validation with range check"
else
    echo "  ❌ MISSING: Device selection validation"
fi
echo ""

# Summary
echo "=== Summary ==="
echo ""
echo "Key fixes that should be present:"
echo "  1. ✓ Validation that devices list exists and is not empty"
echo "  2. ✓ Input validation loop for device selection"
echo "  3. ✓ Better error messages"
echo ""
echo "If all checks passed, the file should be correct!"
echo ""
echo "To test the fix, try running:"
echo "  python3 main.py --config config.yaml"
echo ""

