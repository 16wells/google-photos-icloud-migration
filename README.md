# Google Photos to iCloud Photos Migration Tool

A macOS tool to migrate photos and videos from Google Photos (exported via Google Takeout) to iCloud Photos, preserving metadata and album structures.

## Why this tool?

I have a legacy free Google Workspace account for my family's use.  These accounts are limited to a pretty tight amount of storage to share across what (for us) is a couple dozen users. One of the family ended up with close to 400 gb of photos, and Google started sending warnings / nastygrams about shutting the account off unless the space got cleared up.

The transfer direct from Google Photos to iCloud Photos that was talked about on the web when I was doing this was not available in these old free Google Workspace accounts, so I had to come up with something.

It was such a huge task that I decided to throw it at Cursor to build me a tool that would do the transfer from Google Photos to Apple iCloud Photos for my family member. Along the way I realized that Apple doesn't have a public API for Photos, so you have to do this transfer on a Mac that can log into that iCloud account.  This allows it to use PhotoKit locally on the machine to do the transfer.

Disk space is managed as well as it can be - I did this on a MacBook Air with 512GB hard drive.  But it really takes a long time doing it this way.  What sped it up to an acceptable experience was attaching a 2 TB SSD hard drive and moving the default Photos library to that drive.  Then it had enough room to move through things pretty quickly.  (Note you also want to locate the files for this program on that external drive also.)

**Important:** This tool runs **locally on macOS only**. It requires direct access to your macOS iCloud account via PhotoKit framework. It cannot be run on virtual machines or cloud servers.

It *does* run in the terminal only. Apologies if that's not your jam. But in the build, I had initially built a web-based tool and it was unreliable as hell because of the extended time to download the zip files timing out the webserver.  The terminal might not be everything you'd want, but it's stable and the sucker just keeps running.

## Features

- Downloads Google Takeout zip files from Google Drive
- Extracts and processes media files (HEIC, JPG, AVI, MOV, MP4)
- Merges JSON metadata into media files using ExifTool
- Preserves album structures from Google Takeout
- Uploads to iCloud Photos using PhotoKit (macOS native integration)

## Prerequisites
- **macOS** (required for PhotoKit framework)
- Python 3.11+
- ExifTool (install via `brew install exiftool`)
- Google Drive API credentials
- `pyobjc-framework-Photos` (installed automatically via requirements.txt)

## Installation

> **Quick Start?** If you already have Python and ExifTool installed, see [docs/QUICKSTART.md](docs/QUICKSTART.md) for a 5-minute setup guide.

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. **Run the Authentication Setup Wizard (Recommended)**:
```bash
python3 scripts/auth_setup.py
```
This interactive wizard will:
- Guide you through Google Drive OAuth setup step-by-step
- Open browser windows for you to sign in
- Automatically handle authentication flows
- Create your `config.yaml` file
- No manual file downloads or complex setup needed!

**OR** set up manually:

3a. Set up Google Drive API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials JSON file and save as `credentials.json`

3b. Configure the tool:
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
```

## Configuration

Edit `config.yaml` with your settings:

- **Google Drive**: Credentials file path, folder ID (optional), zip file pattern
- **iCloud**: No credentials needed - uses your macOS iCloud account automatically (PhotoKit sync method)
- **Processing**: Base directory, batch sizes, cleanup options, disk space limits
- **Metadata**: Options for preserving dates, GPS, descriptions, albums

### Environment Variables (.env File)

For better security, store sensitive credentials in a `.env` file (automatically gitignored):

```bash
cp .env.example .env
# Edit .env and add your credentials
```

The `.env` file supports:
- `GOOGLE_DRIVE_CREDENTIALS_FILE`
- `GITHUB_TOKEN` (for repository management scripts)

**Note:** iCloud credentials are not needed as the tool uses your macOS iCloud account automatically via PhotoKit.

Environment variables take precedence over `config.yaml` values. See the "Authentication" section above for details.

### Disk Space Management

The migration tool includes a **Disk Space Limit** feature to control how much disk space the migration process can use. This is especially useful if you have limited disk space or want to ensure other applications have enough room.

**Configuration:**

```yaml
processing:
  max_disk_space_gb: 100  # Limit to 100 GB (or null/unlimited)
  cleanup_after_upload: true  # Automatically free space after upload
```

**How It Works:**
- Downloads pause when disk usage reaches the limit
- Already-downloaded files continue processing
- Uploads continue normally
- After cleanup frees space, downloads automatically resume

**Recommendations by Library Size:**

| Library Size | Recommended Limit | Notes |
|-------------|-------------------|-------|
| Small (<10 GB) | 50 GB | Plenty of headroom |
| Medium (10-50 GB) | 100 GB | 2x library size |
| Large (50-200 GB) | 200-300 GB | Allows multiple ZIPs |
| Very Large (200+ GB) | Unlimited or 500 GB | Batch processing |

**Best Practices:**
1. Leave headroom: Set limit to 2-3x your largest ZIP file
2. Enable cleanup: Turn on `cleanup_after_upload` to free space automatically
3. Monitor: Watch terminal logs for disk space messages

For more details, see the "Disk Space" section under Troubleshooting.

## Usage

The tool provides two main entry points depending on where your Google Takeout zip files are located:

### Option 1: Process Local Zip Files (Recommended if you already have the zips)

If you've already downloaded Google Takeout zip files to your Mac, use `process_local_zips.py`:

```bash
python3 scripts/process_local_zips.py --takeout-dir "/path/to/your/zips"
```

**Key features:**
- ✅ Processes zip files from local directory (no Google Drive download needed)
- ✅ Supports `--skip-processed` to skip already-processed zips
- ✅ Supports `--retry-failed` to retry previously failed zips
- ✅ Faster (no download step)
- ✅ Works offline after initial download

**Example:**
```bash
# Process all zips, skipping already-processed ones
python3 scripts/process_local_zips.py --skip-processed --retry-failed

# Process specific directory (e.g., on external drive)
python3 scripts/process_local_zips.py --takeout-dir "/Volumes/ExternalDrive/Takeout"
```

### Option 2: Download from Google Drive and Process

If your zip files are still in Google Drive, use `main.py` to download and process them:

```bash
python3 scripts/main.py --config config.yaml
```

This method:
1. Downloads zip files from Google Drive (requires authentication)
2. Extracts and processes them
3. Uploads to iCloud Photos

**When to use this method:**
- You haven't downloaded the zip files yet
- You want everything automated in one command
- You prefer keeping zips in Google Drive

**Note:** You can also use `process_local_zips.py` after manually downloading zips from Google Drive.

### PhotoKit Sync Method (macOS Only)

This tool uses Apple's PhotoKit framework to save photos directly to your Photos library, which then automatically syncs to iCloud Photos. This approach:
- Preserves all EXIF metadata (GPS, dates, camera info)
- Supports album organization
- Requires macOS and photo library write permission
- No authentication needed - uses your macOS iCloud account automatically

### Retrying Failed Uploads

**For local zip processing:**
```bash
python3 scripts/process_local_zips.py --retry-failed
```

**For Google Drive processing:**
```bash
python3 scripts/main.py --config config.yaml --retry-failed
```

Failed uploads are automatically tracked and can be retried without re-processing the entire zip file.


## How It Works

**For local zip processing (`process_local_zips.py`):**
1. **Find Zips**: Scans directory for Google Takeout zip files
2. **Extract**: Extracts zip files maintaining directory structure
3. **Process Metadata**: Merges JSON metadata into media files using ExifTool
4. **Parse Albums**: Extracts album structure from directory hierarchy and JSON metadata
5. **Upload**: Uploads processed files to iCloud Photos using PhotoKit
6. **Cleanup**: Removes temporary files (if configured)

**For Google Drive download (`main.py`):**
1. **Download**: Downloads all Google Takeout zip files from Google Drive
2. **Extract**: Extracts zip files maintaining directory structure
3. **Process Metadata**: Merges JSON metadata into media files using ExifTool
4. **Parse Albums**: Extracts album structure from directory hierarchy and JSON metadata
5. **Upload**: Uploads processed files to iCloud Photos using PhotoKit (macOS only)
6. **Cleanup**: Removes temporary files (if configured)

## Metadata Preservation

The tool preserves:
- **Dates**: Photo taken time from `PhotoTakenTimeTimestamp`
- **GPS Coordinates**: Latitude/longitude from `geoData`
- **Descriptions**: Captions and descriptions from JSON metadata
- **Album Structure**: Album organization from directory structure and JSON

## iCloud Photos Upload Method

This tool uses Apple's PhotoKit framework (via `pyobjc-framework-Photos`) to save photos directly to the Photos library using `PHPhotoLibrary` and `PHAssetChangeRequest`. Photos then automatically syncs to iCloud Photos if iCloud Photos is enabled. This method:
- **Preserves EXIF metadata** by using file URLs instead of image objects
- **Supports albums** via PhotoKit's album management
- **Requires macOS** and photo library write permission
- **Automatically syncs** to iCloud Photos when enabled in System Settings
- **No authentication needed** - uses your macOS iCloud account automatically

**Prerequisites:**
- macOS (required for PhotoKit)
- `pyobjc-framework-Photos` package (installed via requirements.txt)
- Photo library write permission (granted on first use)
- iCloud Photos enabled in System Settings

## Authentication

**Quick Setup:** Run the interactive authentication wizard:
```bash
python3 scripts/auth_setup.py
```

This will guide you through:
- Google Drive OAuth setup (opens browser automatically)
- Creating your `config.yaml` file

**Note:** No iCloud authentication is needed - the tool uses your macOS iCloud account automatically via PhotoKit.

### Google Drive OAuth Setup

The tool uses **OAuth 2.0** to authenticate with Google Drive. This is a secure, industry-standard method that:
- Never stores your Google password
- Uses temporary access tokens
- Automatically refreshes tokens when they expire
- Requires one-time setup

**Quick Setup (Recommended):**
Run the setup wizard:
```bash
python3 scripts/auth_setup.py
```

The wizard will:
1. Guide you through creating Google Cloud credentials
2. Open browser windows for you to sign in
3. Automatically handle the OAuth flow
4. Save credentials securely

**Manual Setup:**
If you prefer to set up manually:

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable Google Drive API**
   - Go to **APIs & Services → Library**
   - Search for "Google Drive API"
   - Click **"Enable"**

3. **Create OAuth Credentials**
   - Go to **APIs & Services → Credentials**
   - Click **"+ CREATE CREDENTIALS" → "OAuth client ID"**
   - Configure OAuth consent screen (if prompted):
     - Choose "External"
     - Fill in app name and your email
     - Add your email as a test user
   - Create OAuth client ID:
     - Application type: **"Desktop app"**
     - Name: "Photos Migration Desktop Client"
     - Click **"Create"**
   - Download the JSON file and save as `credentials.json`

4. **Authenticate**
   - Run `python3 scripts/auth_setup.py` or `python3 scripts/main.py --config config.yaml`
   - The tool will automatically open a browser
   - Sign in with your Google account
   - Grant permission to access Google Drive
   - You'll be redirected back automatically

### What Gets Stored

- **`credentials.json`**: OAuth client ID **and client secret** (one-time setup). **Treat this as sensitive** - don't commit to git, don't share publicly.
- **`token.json`**: Your access token (auto-generated, don't share). Allows the tool to access Google Drive without asking for your password every time.

### Apple/iCloud Authentication

**No authentication needed!**

The tool uses your macOS system's iCloud account automatically via PhotoKit. It:
- Uses the Apple ID you're signed into on your Mac
- Requires no passwords or credentials
- Works seamlessly with iCloud Photos
- Preserves all metadata

**Requirements:**
- macOS (required for PhotoKit)
- Signed into iCloud on your Mac
- iCloud Photos enabled in System Settings (optional, but recommended)

**To enable iCloud Photos:**
1. System Settings → Apple ID → iCloud
2. Enable "Photos" (or "iCloud Photos")
3. Choose "Download Originals" or "Optimize Storage"

**Note:** This tool requires macOS and uses PhotoKit. It cannot be run on Linux, Windows, or in virtual machines/cloud servers.

### Environment Variables (.env File)

For better security, you can store sensitive credentials in a `.env` file instead of `config.yaml`. The `.env` file is automatically ignored by git (already in `.gitignore`).

**Setup:**
```bash
cp .env.example .env
# Edit .env and add your credentials
```

**Supported Environment Variables:**
- `GOOGLE_DRIVE_CREDENTIALS_FILE` - Path to credentials.json (optional)
- `GITHUB_TOKEN` - GitHub personal access token (for repository management scripts, optional)

**Note:** iCloud credentials are not needed - the tool uses your macOS iCloud account automatically via PhotoKit.

Environment variables take precedence over `config.yaml` values, providing an extra layer of security. The tool automatically loads `.env` files using `python-dotenv` (already included in `requirements.txt`).

### Security Considerations

**Google Drive:**
- ✅ OAuth 2.0 is secure and industry-standard
- ✅ Your Google password is never stored
- ✅ Tokens can be revoked at any time
- ✅ Access is limited to Google Drive read-only
- ⚠️ `credentials.json` contains an OAuth **client secret**. **Keep it private** and **never commit it** (even in private repos, unless you absolutely must).
- ⚠️ `token.json` contains your access token (keep private)

**Apple/iCloud:**
- ✅ Uses system authentication (most secure)
- ✅ No passwords stored
- ✅ Uses macOS security features

### Verifying Authentication Setup

Check your current setup status:
```bash
python3 scripts/verify-oauth-setup.py --test-connection
```

This will show you:
- ✅ Whether your credentials file is valid
- ✅ Whether you've authenticated (token.json exists)
- ✅ Whether you can connect to Google Drive API

### Revoking Access

**Google Drive:**
To revoke access:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Click "Third-party apps with account access"
3. Find "Photos Migration Tool" (or your app name)
4. Click "Remove access"

Or delete `token.json` to force re-authentication.

**Apple/iCloud:**
PhotoKit method requires no cleanup - it uses your macOS iCloud account automatically. No credentials are stored.

## Troubleshooting

### ExifTool Not Found
Install ExifTool:
- macOS: `brew install exiftool`
- Linux: `apt-get install libimage-exiftool-perl` or `yum install perl-Image-ExifTool`

### iCloud Authentication Issues
- **Note**: The PhotoKit sync method doesn't require authentication - it uses your macOS iCloud account automatically
- Make sure you're signed into iCloud on your Mac and iCloud Photos is enabled in System Settings
- If you have issues, check:
  - You're signed into iCloud on your Mac
  - iCloud Photos is enabled in System Settings
  - Photo library write permission is granted

### PhotoKit Permission Issues

macOS sometimes doesn't show permission dialogs when running Python scripts from Terminal. This is a known limitation of macOS's TCC (Transparency, Consent, and Control) system.

**Important:** macOS treats different terminal applications as separate apps. You need to grant permission to:
- **Terminal.app** (native macOS Terminal) - grant permission to "Terminal"
- **Cursor's integrated terminal** - grant permission to "Cursor"
- **VS Code's integrated terminal** - grant permission to "Visual Studio Code"
- **iTerm2** - grant permission to "iTerm2"

**Solution 1: Request Permission via Script (Recommended)**
The easiest way is to use the permission helper script:
```bash
python3 scripts/request_photos_permission.py
```
This will trigger the macOS permission dialog automatically.

**Solution 2: Manual Grant Permission**
If the script doesn't trigger a dialog:
1. Open **System Settings** → **Privacy & Security** → **Photos**
2. Look for your terminal app (Terminal/Cursor/VS Code/iTerm2) in the list
3. If not listed, click the **"+"** button to add your terminal app
4. Enable permission: Check the box and select **"Add Photos Only"** (sufficient) or **"Read and Write"**

**Solution 3: Reset Permissions**
If your terminal app doesn't appear in the list:
```bash
# Reset Photos permissions (requires password)
sudo tccutil reset Photos

# Then run the permission helper
python3 scripts/request_photos_permission.py
```

**Solution 4: Grant Permission to Python Directly**
1. Find your Python path: `which python3`
2. In **System Settings > Privacy & Security > Photos**, look for "Python" (may show as full path)
3. Enable "Add Photos Only" permission
4. Run migration with full Python path: `/usr/bin/python3 scripts/process_local_zips.py ...`

**Verification:**
```bash
python3 scripts/request_photos_permission.py
```
You should see: "✓ Photo library write permission already granted!"

**Helper Scripts:**
- `scripts/request_photos_permission.py` - Interactive permission request (recommended)
- `scripts/fix_photos_permission.sh` - Comprehensive diagnostic and fix script (advanced)
- `scripts/grant_photos_permission.sh` - Creates temporary macOS app to request permission (alternative method)

**Common Issues:**
- **"Works in Terminal.app but not in Cursor/VS Code"**: Each terminal app needs its own permission. Grant permission to the specific terminal app you're using.
- **"No apps listed in Photos privacy settings"**: Run `python3 scripts/request_photos_permission.py` first. If no dialog appears, use Solution 3 (reset permissions).
- **"Permission dialog never appears"**: This is common with Terminal scripts. Use Solution 2 (manual grant) or try `scripts/fix_photos_permission.sh` for advanced troubleshooting.

**Other PhotoKit Issues:**
- If `pyobjc-framework-Photos` is not found:
  - Install it: `pip install pyobjc-framework-Photos`
  - Or reinstall all dependencies: `pip install -r requirements.txt`
- If you're not on macOS:
  - This tool requires macOS for PhotoKit framework. It cannot run on Linux, Windows, or in virtual machines/cloud servers.

### Upload Failures
- Failed uploads are automatically saved to `failed_uploads.json` in the base directory
- To retry failed uploads, run:
  ```bash
  python scripts/main.py --config config.yaml --retry-failed
  ```
- The retry command will:
  - Load the list of previously failed files
  - Attempt to upload them again
  - Update the failed uploads file (removing successful ones)
  - Show progress and final results
- If uploads continue to fail:
  - Check iCloud storage space
  - Verify you're signed into iCloud on your Mac
  - Ensure iCloud Photos is enabled in System Settings
  - Check network connectivity
  - Review error messages in the log file

### Large File Processing
- Adjust `batch_size` in config.yaml
- Ensure your Mac has sufficient disk space (at least 2x your Google Photos data size)
- Process in smaller batches if needed

### Disk Space Issues

**Downloads Keep Pausing:**
- Increase the disk space limit in `config.yaml`: `max_disk_space_gb: 200`
- Enable cleanup: `cleanup_after_upload: true`
- Manually delete processed ZIPs if needed
- Check if other apps are using disk space

**Limit Not Working:**
- Limit set after download started - stop migration, set limit, restart
- Extracted files count toward total - they're included in the limit
- Other processes writing to disk - check system usage with `df -h`

**Performance Impact:**
- Frequent pauses slow migration - increase limit to allow more parallel downloads
- Use faster cleanup (SSD recommended)
- Set limit to 2-3x your largest ZIP file size

**Monitoring Disk Usage:**
```bash
# Check disk usage
df -h

# Check migration directory size
du -sh /path/to/migration/base_dir
```

The tool logs disk space status:
```
INFO: Current usage: 45.2 GB / 100.0 GB limit (45%)
WARNING: Disk space limit approaching (95.8 GB / 100.0 GB)
INFO: Pausing downloads until space is freed
```

## Limitations

- **Platform**: Requires macOS (PhotoKit framework is macOS-only)
- **Permissions**: Requires photo library write permission, which is requested automatically on first use
- **iCloud Photos**: Requires iCloud Photos to be enabled in System Settings for automatic syncing
- **Album Creation**: Albums are created automatically via PhotoKit

## System Requirements

- **macOS**: Required for PhotoKit framework
- **Disk Space**: At least 2x the size of your Google Photos data
- **Internet**: Required for downloading from Google Drive and syncing to iCloud Photos

## License

This tool is provided as-is for personal use.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `migration.log`
3. Ensure all prerequisites are installed

## Documentation

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Get started in 5 minutes (for users with prerequisites installed)
- **[docs/COMPLETE_INSTALLATION_GUIDE.md](docs/COMPLETE_INSTALLATION_GUIDE.md)** - Step-by-step setup guide for a brand new MacBook (includes Xcode, Homebrew, Python setup)
- **[docs/TESTING.md](docs/TESTING.md)** - Test the migration before running the full process
- **[docs/MACBOOK_CHECKLIST.md](docs/MACBOOK_CHECKLIST.md)** - Pre-migration checklist for MacBook setup
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development guide (testing, linting, documentation)
- **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** - Contribution guidelines
- **[docs/SECURITY.md](docs/SECURITY.md)** - Security best practices
- **[docs/CHANGELOG.md](docs/CHANGELOG.md)** - Version history
- **[docs/](docs/)** - Sphinx API documentation (run `make docs` to generate)

## Understanding Migration Reports

The migration tool generates comprehensive reports at the end of each migration run. These reports provide detailed statistics, error summaries, and actionable recommendations.

### Report Files Generated

When the migration completes, the following files are created in your base directory:

1. **`migration_report.txt`** - Human-readable text report with complete migration summary
2. **`migration_statistics.json`** - Machine-readable JSON file with all statistics
3. **`migration.log`** - Detailed log file with all operations and errors
4. **`failed_uploads.json`** - List of files that failed to upload (if any)
5. **`corrupted_zips.json`** - List of corrupted zip files (if any)

### Report Contents

**Executive Summary:**
- Start and end times, total duration
- Overall success rate
- High-level statistics (files processed, uploaded, failed)

**Phase-by-Phase Breakdown:**
- **Phase 1: Download** - Total zip files, downloaded, skipped, failed, corrupted
- **Phase 2: Extraction** - Successfully extracted, extraction failures
- **Phase 3: Metadata Processing** - Media files found, with metadata, processed, failures
- **Phase 4: Album Parsing** - Albums identified (from directory structure and JSON)
- **Phase 5: Upload** - Successfully uploaded, upload failures, verification failures, upload success rate

**Error Summary:**
- Count of errors by category
- References to detailed error logs
- Specific error messages for key failures

**Recommendations & Next Steps:**
- How to retry failed uploads
- How to handle corrupted zip files
- What to review if verification failures occurred
- Next steps for troubleshooting

### Using the Reports

**After Successful Migration:**
- Review the executive summary to confirm all files were processed
- Check upload success rate
- Verify album counts match expectations

**After Migration with Errors:**
1. Review Error Summary - See which phases had issues
2. Check Failed Uploads - Review `failed_uploads.json` for specific files
3. Review Log File - Search for specific error messages in `migration.log`
4. Follow Recommendations - Use the recommendations section for next steps

**Retrying Failed Uploads:**
```bash
# For Google Drive processing
python3 scripts/main.py --config config.yaml --retry-failed

# For local zip processing
python3 scripts/process_local_zips.py --retry-failed
```

**Example Report Structure:**
```
================================================================================
GOOGLE PHOTOS TO iCLOUD PHOTOS MIGRATION REPORT
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Start Time:     2024-01-15 10:00:00
End Time:       2024-01-15 12:30:00
Duration:       2h 30m 0s

Overall Results:
  Zip Files Processed:     45/50 successful
  Success Rate:            90.0%

Upload Results:
  Successfully Uploaded:    12,300
  Upload Failed:            45
  Upload Success Rate:      99.6%

RECOMMENDATIONS & NEXT STEPS
--------------------------------------------------------------------------------
• Retry failed uploads by running:
  python3 scripts/main.py --config config.yaml --retry-failed
```

## Notes

- The tool processes files in batches to manage memory and disk space
- Extracted files are kept until upload completes (unless cleanup is enabled)
- Metadata merging preserves original files (creates processed copies)
- Album structures are extracted and automatically recreated in iCloud Photos

## Security

For security best practices, see **[docs/SECURITY.md](docs/SECURITY.md)**.

**Key Security Notes:**
- ✅ Never commit `credentials.json`, `token.json`, or `config.yaml` to git (already in `.gitignore`)
- ✅ Use `.env` file for sensitive credentials (already in `.gitignore`)
- ✅ OAuth 2.0 tokens can be revoked at any time from Google Account settings
- ✅ PhotoKit uses your macOS system authentication (most secure method)
- ✅ No passwords are stored for iCloud (uses system authentication)

