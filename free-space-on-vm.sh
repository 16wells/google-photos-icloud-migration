#!/bin/bash
# Script to free up disk space on VM
# Run this ON the VM to clean up before updating files

echo "Checking disk space..."
df -h /

echo ""
echo "Finding large files..."
echo "Top 10 largest files/directories:"
du -h /home/skipshean 2>/dev/null | sort -rh | head -10

echo ""
echo "Checking for zip files..."
find /home/skipshean -name "*.zip" -type f -exec ls -lh {} \; 2>/dev/null | head -10

echo ""
echo "Checking for extracted directories..."
find /home/skipshean -type d -name "extracted" -exec du -sh {} \; 2>/dev/null

echo ""
echo "Checking for log files..."
find /home/skipshean -name "*.log" -type f -exec ls -lh {} \; 2>/dev/null | head -5

echo ""
echo "To free up space, you can:"
echo "1. Delete log files: rm -f *.log migration.log"
echo "2. Delete extracted directories (if processing failed): rm -rf extracted/ processed/"
echo "3. Delete one zip file at a time to make room for the update"
echo ""

