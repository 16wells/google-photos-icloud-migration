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
