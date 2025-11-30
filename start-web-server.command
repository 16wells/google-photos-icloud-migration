#!/bin/bash

# Google Photos to iCloud Migration - Web Server Starter
# This script can be double-clicked on macOS to start the web server

echo "==========================================================="
echo "  Google Photos to iCloud Migration - Starting Web Server"
echo "==========================================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Project directory: $SCRIPT_DIR"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3 and try again"
    echo ""
    read -p "Press any key to exit..."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if web_server.py exists
if [ ! -f "web_server.py" ]; then
    echo "❌ Error: web_server.py not found in $SCRIPT_DIR"
    echo ""
    read -p "Press any key to exit..."
    exit 1
fi

echo "✅ web_server.py found"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found, activating..."
    source venv/bin/activate
    echo ""
fi

# Check if required packages are installed
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Flask not installed. Installing dependencies..."
    pip3 install -r requirements-web.txt
    echo ""
fi

echo "🚀 Starting web server..."
echo ""
echo "==========================================================="
echo "  The web interface will open at: http://localhost:5001"
echo "==========================================================="
echo ""
echo "📖 Instructions:"
echo "  1. Keep this terminal window open"
echo "  2. Open http://localhost:5001 in your browser"
echo "  3. Use the web interface to run your migration"
echo "  4. Press Ctrl+C in this terminal to stop the server"
echo ""
echo "==========================================================="
echo ""

# Start the web server
python3 web_server.py

# If the server exits, keep the terminal open
echo ""
echo "Web server stopped."
read -p "Press any key to exit..."

