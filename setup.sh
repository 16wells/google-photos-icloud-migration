#!/bin/bash
# Setup script for GCP VM environment

set -e

echo "Setting up Google Photos to iCloud Migration environment..."

# Update package lists
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip unzip libimage-exiftool-perl
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y python3 python3-pip unzip perl-Image-ExifTool
elif command -v brew &> /dev/null; then
    # macOS
    brew install python3 exiftool
else
    echo "Warning: Unknown package manager. Please install Python 3, pip, unzip, and ExifTool manually."
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p /tmp/google-photos-migration/{zips,extracted,processed}

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Download Google Drive API credentials and save as 'credentials.json'"
echo "2. Copy config.yaml.example to config.yaml and update with your settings"
echo "3. Activate the virtual environment: source venv/bin/activate"
echo "4. Run: python main.py --config config.yaml"

