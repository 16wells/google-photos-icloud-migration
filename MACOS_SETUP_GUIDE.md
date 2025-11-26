# macOS Setup Guide for iCloud Photos Migration

This guide explains how to set up and run the migration on a macOS system using the Photos library sync method (`--use-sync`). This approach is **much more reliable** than using the API method on a Linux VM.

## Why Use macOS Instead of VM?

1. **Native Photos App Integration**: macOS Photos app has built-in iCloud Photos sync
2. **Album Support**: Can properly organize photos into albums using AppleScript
3. **No API Limitations**: Avoids pyicloud API limitations and authentication issues
4. **Automatic Sync**: Photos automatically sync to iCloud Photos once imported
5. **Better Reliability**: Uses Apple's native tools instead of reverse-engineered APIs

## Prerequisites

1. **MacBook with sufficient storage**:
   - Enough space for all Google Photos zip files
   - Enough space for extracted photos
   - Enough space for Photos library (if using default location)
   - Recommended: At least 2x the size of your Google Photos data

2. **New User Account** (recommended):
   - Create a new macOS user account
   - Use the same Apple ID as your iCloud Photos account (e.g., `katie@shean.com`)
   - This keeps the migration isolated and prevents conflicts

3. **iCloud Photos Enabled**:
   - Sign into iCloud with the target account
   - Enable iCloud Photos in System Settings → Apple ID → iCloud → Photos
   - Ensure "Download Originals" or "Optimize Storage" is set as desired

## Setup Steps

### 1. Create New User Account

1. System Settings → Users & Groups
2. Click "+" to add new user
3. Create account with:
   - Full Name: (your choice)
   - Account Name: (your choice, e.g., "photos-migration")
   - Password: (secure password)
   - Allow user to administer this computer: ✅ (for script permissions)

### 2. Sign Into iCloud

1. Log in as the new user
2. System Settings → Apple ID
3. Sign in with `katie@shean.com` (or your target iCloud account)
4. Enable iCloud Photos:
   - System Settings → Apple ID → iCloud → Photos
   - Toggle "Sync this Mac" to ON
   - Choose "Download Originals" or "Optimize Storage" based on your needs

### 3. Install Dependencies

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install exiftool python3

# Install Python dependencies
pip3 install -r requirements.txt
```

### 4. Configure the Script

1. Copy your `config.yaml` and `credentials.json` to the MacBook
2. Update `config.yaml` if needed:
   ```yaml
   icloud:
     apple_id: katie@shean.com
     # photos_library_path is optional - defaults to ~/Pictures/Photos Library.photoslibrary
     # photos_library_path: ~/Pictures/Photos Library.photoslibrary
   ```

### 5. Grant Permissions

The script will need to:
- Access Photos library (System Settings → Privacy & Security → Photos)
- Access files (System Settings → Privacy & Security → Files and Folders)

You may be prompted for these permissions when the script runs.

## Running the Migration

### Basic Usage

```bash
python3 main.py --config config.yaml --use-sync
```

### What Happens

1. **Download**: Downloads Google Takeout zip files from Google Drive
2. **Extract**: Extracts zip files maintaining directory structure
3. **Process Metadata**: Merges JSON metadata into media files using ExifTool
4. **Parse Albums**: Extracts album structure from directory hierarchy and JSON
5. **Import to Photos**: 
   - Imports photos into Photos app using AppleScript
   - Creates albums if they don't exist
   - Adds photos to appropriate albums
   - Reuses existing albums (case-insensitive matching)
6. **Sync to iCloud**: Photos app automatically syncs to iCloud Photos
7. **Cleanup**: Removes temporary files (if configured)

### Monitoring Progress

- The script will show progress for each zip file
- Photos app will show import progress in the background
- iCloud Photos sync happens automatically (check iCloud Photos on another device)

### Pause and Check

After each zip file, you'll be prompted:
- **(C) Continue** - Process next zip
- **(A) Continue All** - Process all remaining without prompts
- **(S) Stop** - Stop and exit

## Album Preservation

The enhanced sync method:
- ✅ Creates albums in Photos app if they don't exist
- ✅ Reuses existing albums (case-insensitive matching)
- ✅ Organizes photos into correct albums
- ✅ Preserves album structure from Google Photos

## Troubleshooting

### Photos App Not Responding

If Photos app becomes unresponsive during import:
1. Wait - large imports can take time
2. Check Activity Monitor for Photos process
3. If truly stuck, force quit and restart Photos app
4. Re-run script with `--retry-failed` to retry failed uploads

### Storage Issues

If running out of space:
1. Use "Optimize Storage" in iCloud Photos settings
2. Process zip files in smaller batches
3. Clean up extracted files after each zip (script does this automatically)

### Permission Errors

If you see permission errors:
1. System Settings → Privacy & Security → Photos → Add Terminal/Python
2. System Settings → Privacy & Security → Files and Folders → Add access

### iCloud Sync Not Working

1. Check System Settings → Apple ID → iCloud → Photos is enabled
2. Check internet connection
3. Wait - initial sync can take hours for large libraries
4. Check iCloud storage space (Settings → Apple ID → iCloud)

## Advantages Over VM Method

| Feature | macOS Sync Method | VM API Method |
|---------|------------------|---------------|
| Album Support | ✅ Full support | ⚠️ Limited/experimental |
| Reliability | ✅ Very reliable | ⚠️ API limitations |
| Authentication | ✅ Native iCloud | ⚠️ 2FA challenges |
| Speed | ✅ Fast (local) | ⚠️ Network dependent |
| Monitoring | ✅ Photos app UI | ⚠️ Logs only |

## Next Steps

After migration completes:
1. Verify photos in Photos app
2. Check iCloud Photos on another device
3. Verify albums are correct
4. Once confirmed, you can delete the temporary user account (optional)

