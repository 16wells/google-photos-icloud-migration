#!/bin/bash
# Script to split icloud_uploader.py into smaller pasteable chunks for VM

FILE="icloud_uploader.py"
CHUNK_SIZE=80  # Lines per chunk
OUTPUT_DIR="vm_chunks"

if [ ! -f "$FILE" ]; then
    echo "Error: $FILE not found"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*

# Get total lines
TOTAL_LINES=$(wc -l < "$FILE")
CHUNKS=$(( (TOTAL_LINES + CHUNK_SIZE - 1) / CHUNK_SIZE ))

echo "Splitting $FILE into chunks..."
echo "Total lines: $TOTAL_LINES"
echo "Chunk size: $CHUNK_SIZE lines"
echo "Number of chunks: $CHUNKS"
echo ""

# Split the file
split -l "$CHUNK_SIZE" "$FILE" "$OUTPUT_DIR/chunk_"

# Rename chunks to have .txt extension
for f in "$OUTPUT_DIR"/chunk_*; do
    mv "$f" "${f}.txt"
done

# Create reassembly script for VM
cat > "$OUTPUT_DIR/reassemble.sh" << 'SCRIPTEOF'
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
SCRIPTEOF

chmod +x "$OUTPUT_DIR/reassemble.sh"

# Create instructions file
cat > "$OUTPUT_DIR/INSTRUCTIONS.txt" << 'INSTEOF'
HOW TO UPDATE icloud_uploader.py ON VM
======================================

Method: Copy chunks and reassemble

STEP 1: Copy reassemble.sh to VM
---------------------------------
In Browser SSH, run:
  cat > reassemble.sh << 'REASSEMBLEEOF'
[Then paste the contents of reassemble.sh from this directory]
[Type REASSEMBLEEOF and press Enter]
  chmod +x reassemble.sh

STEP 2: Copy each chunk file
-----------------------------
For each chunk_*.txt file in this directory:

In Browser SSH, run:
  cat > chunk_XX.txt << 'CHUNKEOF'
[Paste the chunk content]
[Type CHUNKEOF and press Enter]

Do this for ALL chunks in order:
  - chunk_aa.txt
  - chunk_ab.txt
  - chunk_ac.txt
  ... (continue until all chunks are copied)

STEP 3: Reassemble the file
-----------------------------
Run:
  ./reassemble.sh

This will create icloud_uploader.py with all the fixes.

STEP 4: Verify
--------------
Run:
  wc -l icloud_uploader.py  # Should show ~454 lines
  grep -c "No trusted devices found" icloud_uploader.py  # Should show 2

INSTEOF

# Create a quick copy script
cat > "$OUTPUT_DIR/copy-chunks.sh" << 'COPYEOF'
#!/bin/bash
# Helper script to show commands for copying each chunk

echo "=== Commands to copy chunks to VM ==="
echo ""
echo "Run these commands in Browser SSH, one at a time:"
echo ""

for chunk in chunk_*.txt; do
    if [ -f "$chunk" ]; then
        echo "echo 'Copying $chunk...'"
        echo "cat > $chunk << 'CHUNKEOF'"
        echo "# [Paste content of $chunk here]"
        echo "CHUNKEOF"
        echo ""
    fi
done

echo "# After copying all chunks, run:"
echo "./reassemble.sh"
COPYEOF

chmod +x "$OUTPUT_DIR/copy-chunks.sh"

echo "✓ Done! Files created in $OUTPUT_DIR/"
echo ""
echo "Chunks created:"
ls -lh "$OUTPUT_DIR"/chunk_*.txt | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Next steps:"
echo "1. Review $OUTPUT_DIR/INSTRUCTIONS.txt"
echo "2. Copy chunks to VM using Browser SSH"
echo "3. Run reassemble.sh on the VM"


