#!/bin/bash
# Reassemble icloud_uploader.py from chunks
# Run this in Browser SSH on the VM

OUTPUT_FILE="icloud_uploader.py"
CHUNK_PREFIX="chunk_"

echo "=== Reassembling icloud_uploader.py ==="
echo ""

# Remove old file if exists
rm -f "$OUTPUT_FILE"

# Find all chunk files and sort them
CHUNKS=$(ls ${CHUNK_PREFIX}*.txt 2>/dev/null | sort -V)

if [ -z "$CHUNKS" ]; then
    echo "Error: No chunk files found!"
    echo "Make sure you've pasted all chunk files first."
    exit 1
fi

# Count chunks
CHUNK_COUNT=$(echo "$CHUNKS" | wc -l)
echo "Found $CHUNK_COUNT chunk(s)"
echo ""

# Reassemble
for chunk in $CHUNKS; do
    echo "Adding $chunk..."
    cat "$chunk" >> "$OUTPUT_FILE"
done

# Verify
if [ -f "$OUTPUT_FILE" ]; then
    LINES=$(wc -l < "$OUTPUT_FILE")
    SIZE=$(wc -c < "$OUTPUT_FILE")
    echo ""
    echo "✓ File reassembled successfully!"
    echo "  Lines: $LINES"
    echo "  Size: $SIZE bytes"
    echo ""
    echo "Verifying key fixes..."
    grep -q "No trusted devices found" "$OUTPUT_FILE" && echo "  ✓ Found: 'No trusted devices found'" || echo "  ✗ Missing: 'No trusted devices found'"
    grep -q "Ensure devices is a list" "$OUTPUT_FILE" && echo "  ✓ Found: Device list validation" || echo "  ✗ Missing: Device list validation"
    grep -q "while True:" "$OUTPUT_FILE" && echo "  ✓ Found: Input validation loop" || echo "  ✗ Missing: Input validation loop"
else
    echo "✗ Error: Failed to create file"
    exit 1
fi
