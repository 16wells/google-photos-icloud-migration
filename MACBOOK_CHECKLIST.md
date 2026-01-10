# MacBook Preparation Checklist

Quick checklist for preparing the new MacBook today.

## Today (Before iCloud Validation)

- [ ] **Copy repository to MacBook**
  - Option: Git clone, USB drive, AirDrop, or rsync
  - Location: `~/google-photos-icloud-migration` (or your preferred location)

- [ ] **Run setup script**
  ```bash
  cd ~/google-photos-icloud-migration
  chmod +x setup-macbook.sh
  ./setup-macbook.sh
  ```
  This installs: 
  - Xcode Command Line Tools (will show popup - click "Install" and wait)
  - Homebrew
  - ExifTool
  - Python 3
  - Python packages

- [ ] **Copy configuration files**
  - Copy `credentials.json` from current machine
  - Copy `config.yaml` from current machine
  - Place both in the repository root directory

- [ ] **Verify setup**
  ```bash
  python3 verify-setup.py
  ```
  All checks should pass ✓

- [ ] **Test Google Drive connection (optional)**
  ```bash
  python3 -c "from drive_downloader import GoogleDriveDownloader; import yaml; config = yaml.safe_load(open('config.yaml')); d = GoogleDriveDownloader(config); print(f'Found {len(d.list_zip_files())} zip files')"
  ```

## Tomorrow (After iCloud Validation)

- [ ] **Sign into iCloud**
  - System Settings → Apple ID
  - Sign in with your Apple ID

- [ ] **Enable iCloud Photos**
  - System Settings → Apple ID → iCloud → Photos
  - Toggle "Sync this Mac" to ON
  - Choose "Download Originals" or "Optimize Storage"

- [ ] **Grant permissions** (when prompted)
  - System Settings → Privacy & Security → Photos → Allow Terminal/Python
  - System Settings → Privacy & Security → Files and Folders → Allow access

- [ ] **Run migration**
  ```bash
  cd ~/google-photos-icloud-migration
  python3 main.py --config config.yaml
  ```

## Files to Copy

Make sure these files are on the new MacBook:

1. **credentials.json** - Google Drive API credentials
2. **config.yaml** - Configuration file

Both should be in the repository root directory.

## Quick Reference

- **Setup script**: `./setup-macbook.sh`
- **Verification**: `python3 verify-setup.py`
- **Full guide**: See [COMPLETE_INSTALLATION_GUIDE.md](COMPLETE_INSTALLATION_GUIDE.md)
- **Quick start**: See [QUICKSTART.md](QUICKSTART.md) (if you already have prerequisites)

