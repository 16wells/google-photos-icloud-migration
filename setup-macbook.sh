#!/bin/bash

# Setup script for preparing new MacBook for Google Photos to iCloud migration
# Run this after copying the repository to the new MacBook

set -e  # Exit on error

echo "=========================================="
echo "MacBook Setup for Photos Migration"
echo "=========================================="
echo ""

# Check if Xcode Command Line Tools are installed
echo "Checking for Xcode Command Line Tools..."
if ! xcode-select -p &> /dev/null; then
    echo "⚠️  Xcode Command Line Tools not found. Installing..."
    echo "   (This will show a popup window - click 'Install' and wait for it to finish)"
    xcode-select --install || true  # Don't fail if already installing or other error
    echo ""
    echo "⏳ Please wait for the installation to complete..."
    echo "   A popup window should appear. Click 'Install' and wait for it to finish."
    echo "   This typically takes 5-10 minutes."
    echo ""
    echo "   Press Enter once the installation is complete..."
    read -r
    # Verify installation completed
    if ! xcode-select -p &> /dev/null; then
        echo "⚠️  Installation may not have completed. Please run 'xcode-select --install' manually if needed."
    else
        echo "✓ Xcode Command Line Tools installation verified"
    fi
else
    echo "✓ Xcode Command Line Tools already installed"
fi

echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew not found. Installing Homebrew..."
    echo "   (This will prompt for your password)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✓ Homebrew already installed"
fi

echo ""
echo "Installing system dependencies..."

# Install ExifTool
if ! command -v exiftool &> /dev/null; then
    echo "Installing ExifTool..."
    brew install exiftool
else
    echo "✓ ExifTool already installed"
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    brew install python3
else
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python 3 found: $PYTHON_VERSION"
fi

echo ""
echo "Installing Python dependencies..."

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "✗ ERROR: requirements.txt not found!"
    echo "   Make sure you're running this from the repository root directory"
    exit 1
fi

# Install Python packages
echo "Installing Python packages from requirements.txt..."
pip3 install -r requirements.txt

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy credentials.json and config.yaml to this directory"
echo "2. Verify setup by checking the files exist:"
echo "   ls -la credentials.json config.yaml"
echo "3. Tomorrow: Sign into iCloud and run:"
echo "   python3 main.py --config config.yaml --use-sync"
echo ""

