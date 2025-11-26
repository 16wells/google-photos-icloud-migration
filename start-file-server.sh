#!/bin/bash
# Start a simple HTTP server to share files with VM
# Run this on your Mac

echo "Starting file server on port 8000..."
echo "Files will be available at: http://YOUR_MAC_IP:8000/"
echo ""
echo "To find your Mac's IP address, run:"
echo "  ifconfig | grep 'inet ' | grep -v 127.0.0.1"
echo ""
echo "Then on your VM, run:"
echo "  curl http://YOUR_MAC_IP:8000/main.py -o main.py"
echo "  curl http://YOUR_MAC_IP:8000/drive_downloader.py -o drive_downloader.py"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
python3 -m http.server 8000

