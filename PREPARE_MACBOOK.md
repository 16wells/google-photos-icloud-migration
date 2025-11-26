# Preparing New MacBook for Migration

This guide helps you prepare the new MacBook today so you can run the migration tomorrow after validating the iCloud account.

## Step 1: Copy Repository to MacBook

### Option A: Using Git (Recommended if repo is on GitHub/GitLab)

```bash
# On new MacBook
cd ~
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration
```

**See `CLONE_FROM_GITHUB.md` for detailed instructions.**

### Option B: Using USB Drive or Network Share

1. Copy the entire `google-photos-icloud-migration` folder to the MacBook
2. Place it in a convenient location (e.g., `~/Documents/` or `~/Sites/`)

### Option C: Using rsync/scp (if both machines on same network)

```bash
# From your current machine
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.log' \
  ~/Sites/google-photos-icloud-migration/ \
  user@new-macbook.local:~/google-photos-icloud-migration/
```

## Step 2: Install System Dependencies

On the new MacBook, open Terminal and run:

### First: Install Xcode Command Line Tools

```bash
# Check if already installed
xcode-select -p

# If not installed, run this (will show a popup to install):
xcode-select --install
```

**Note:** This will show a popup window. Click "Install" and wait for it to complete (may take 5-10 minutes). This is required for Homebrew and many other tools.

### Then: Install Homebrew and Tools

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install exiftool python3
```

**Or use the automated setup script** (which handles all of this):
```bash
./setup-macbook.sh
```

## Step 3: Install Python Dependencies

```bash
cd ~/google-photos-icloud-migration  # or wherever you placed it

# Install Python packages
pip3 install -r requirements.txt
```

## Step 4: Copy Configuration Files

You'll need to copy these files from your current machine (they're in `.gitignore` so won't be in git):

### Required Files:
- `credentials.json` - Google Drive API credentials
- `config.yaml` - Configuration file

### Copy Methods:

**Option A: USB Drive**
- Copy files to USB drive
- Copy from USB to MacBook

**Option B: AirDrop**
- Select files on current Mac
- AirDrop to new MacBook

**Option C: Cloud Storage**
- Upload to iCloud Drive, Dropbox, etc.
- Download on new MacBook

**Option D: scp/rsync**
```bash
# From current machine
scp credentials.json config.yaml user@new-macbook.local:~/google-photos-icloud-migration/
```

Place both files in the repository root directory.

## Step 5: Verify Setup

Run this verification script:

```bash
cd ~/google-photos-icloud-migration
python3 -c "
import sys
print('Python version:', sys.version)

try:
    import google.auth
    print('✓ Google API libraries installed')
except ImportError:
    print('✗ Google API libraries missing')

try:
    import pyicloud
    print('✓ pyicloud installed')
except ImportError:
    print('✗ pyicloud missing')

try:
    from PIL import Image
    print('✓ Pillow installed')
except ImportError:
    print('✗ Pillow missing')

try:
    import yaml
    print('✓ PyYAML installed')
except ImportError:
    print('✗ PyYAML missing')

try:
    import tqdm
    print('✓ tqdm installed')
except ImportError:
    print('✗ tqdm missing')

import subprocess
result = subprocess.run(['which', 'exiftool'], capture_output=True)
if result.returncode == 0:
    print('✓ ExifTool installed')
else:
    print('✗ ExifTool not found in PATH')

import os
if os.path.exists('credentials.json'):
    print('✓ credentials.json found')
else:
    print('✗ credentials.json missing')

if os.path.exists('config.yaml'):
    print('✓ config.yaml found')
else:
    print('✗ config.yaml missing')
"
```

All items should show ✓.

## Step 6: Update config.yaml (if needed)

Edit `config.yaml` and verify:
- `icloud.apple_id` is set to `katie@shean.com` (or your target account)
- `icloud.photos_library_path` is commented out or set correctly (defaults to `~/Pictures/Photos Library.photoslibrary`)

## Step 7: Test Google Drive Connection (Optional)

You can test the Google Drive connection before iCloud is set up:

```bash
python3 -c "
from drive_downloader import GoogleDriveDownloader
from pathlib import Path
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

downloader = GoogleDriveDownloader(config)
print('Testing Google Drive connection...')
try:
    files = downloader.list_zip_files()
    print(f'✓ Found {len(files)} zip files in Google Drive')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

## Tomorrow: Final Steps

Once you've validated the iCloud account:

1. **Sign into iCloud**:
   - System Settings → Apple ID
   - Sign in with `katie@shean.com`
   - Enable iCloud Photos: System Settings → Apple ID → iCloud → Photos → ON

2. **Grant Permissions** (when prompted):
   - System Settings → Privacy & Security → Photos → Allow Terminal/Python
   - System Settings → Privacy & Security → Files and Folders → Allow access

3. **Run the migration**:
   ```bash
   cd ~/google-photos-icloud-migration
   python3 main.py --config config.yaml --use-sync
   ```

## Quick Setup Script

I've created `setup-macbook.sh` that automates steps 2-3. Run it after copying the repo:

```bash
chmod +x setup-macbook.sh
./setup-macbook.sh
```

## Troubleshooting

### "command not found: brew"
- Install Homebrew first (see Step 2)

### "pip3: command not found"
- Install Python 3: `brew install python3`

### Permission Errors
- You may need to grant Terminal "Full Disk Access" in System Settings → Privacy & Security

### Python Version Issues
- Ensure you're using Python 3.8+: `python3 --version`
- If needed: `brew install python@3.11`

