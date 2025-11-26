#!/bin/bash
#
# Update script to run ON the VM
# This script downloads the latest files from GitHub or allows manual update
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Google Photos Migration - VM Update Script${NC}"
echo "=========================================="
echo ""

# Check if we're in a git repository
if [ -d ".git" ]; then
    echo -e "${BLUE}Detected git repository. Pulling latest changes...${NC}"
    git pull origin main
    echo -e "${GREEN}✓ Updated from git repository${NC}"
    exit 0
fi

# If not a git repo, provide manual update instructions
echo -e "${YELLOW}Not a git repository. Manual update required.${NC}"
echo ""
echo -e "${BLUE}Option 1: Update from GitHub (if repository exists)${NC}"
echo "  git clone https://github.com/16wells/google-photos-icloud-migration.git"
echo "  # Then copy main.py and drive_downloader.py to your working directory"
echo ""
echo -e "${BLUE}Option 2: Copy files manually using scp from your local machine${NC}"
echo "  From your local machine, run:"
echo "  scp main.py drive_downloader.py [user@]vm-hostname:~/"
echo ""
echo -e "${BLUE}Option 3: Download files directly (if accessible via URL)${NC}"
echo "  # You would need to upload files to a temporary location first"
echo ""
echo -e "${YELLOW}Files that need to be updated:${NC}"
echo "  - main.py (updated to process files one at a time)"
echo "  - drive_downloader.py (updated with disk space checking)"
echo ""
echo -e "${GREEN}After updating, verify the changes:${NC}"
echo "  grep -n 'Phase 1: Listing zip files' main.py"
echo "  grep -n '_find_existing_zips' main.py"
echo "  grep -n '_check_disk_space' drive_downloader.py"
echo ""

