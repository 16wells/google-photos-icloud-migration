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
    
    # Add Homebrew to PATH (location differs on Intel vs Apple Silicon)
    if [ -f "/opt/homebrew/bin/brew" ]; then
        # Apple Silicon Mac
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo "✓ Added Homebrew to PATH (Apple Silicon)"
    elif [ -f "/usr/local/bin/brew" ]; then
        # Intel Mac
        eval "$(/usr/local/bin/brew shellenv)"
        echo "✓ Added Homebrew to PATH (Intel)"
    else
        # Try to find brew in common locations
        BREW_PATH=$(find /opt /usr/local -name brew -type f 2>/dev/null | head -1)
        if [ -n "$BREW_PATH" ]; then
            eval "$($BREW_PATH shellenv)"
            echo "✓ Added Homebrew to PATH (found at $BREW_PATH)"
        else
            echo "⚠️  Could not find Homebrew after installation."
            echo "   Please run this command and then re-run this script:"
            echo "   eval \"\$(/opt/homebrew/bin/brew shellenv)\"  # Apple Silicon"
            echo "   eval \"\$(/usr/local/bin/brew shellenv)\"     # Intel"
            exit 1
        fi
    fi
    
    # Verify brew is now available
    if ! command -v brew &> /dev/null; then
        echo "✗ ERROR: Homebrew installed but not in PATH"
        echo "   Please restart your terminal or run:"
        echo "   eval \"\$(/opt/homebrew/bin/brew shellenv)\"  # Apple Silicon"
        echo "   eval \"\$(/usr/local/bin/brew shellenv)\"     # Intel"
        exit 1
    fi
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

# Upgrade pip first
echo "Upgrading pip to latest version..."
python3 -m pip install --upgrade pip

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

