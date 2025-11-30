# Google Photos to iCloud Photos Migration Tool

A macOS tool to migrate photos and videos from Google Photos (exported via Google Takeout) to iCloud Photos, preserving metadata and album structures.

## Features

- Downloads Google Takeout zip files from Google Drive
- Extracts and processes media files (HEIC, JPG, AVI, MOV, MP4)
- Merges JSON metadata into media files using ExifTool
- Preserves album structures from Google Takeout
- Uploads to iCloud Photos using PhotoKit (macOS native integration)
- **Modern Web UI** with real-time progress tracking (NEW!)

## Prerequisites

### Prerequisites
- **macOS** (required for PhotoKit framework)
- Python 3.11+
- ExifTool (install via `brew install exiftool`)
- Google Drive API credentials
- `pyobjc-framework-Photos` (installed automatically via requirements.txt)

## Installation

> **Quick Start?** If you already have Python and ExifTool installed, see [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide.

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. **Run the Authentication Setup Wizard (Recommended)**:
```bash
python3 auth_setup.py
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
- **iCloud**: Apple ID, password (optional - will prompt), trusted device ID for 2FA
- **Processing**: Base directory, batch sizes, cleanup options
- **Metadata**: Options for preserving dates, GPS, descriptions, albums

### Environment Variables (.env File)

For better security, store sensitive credentials in a `.env` file (automatically gitignored):

```bash
cp .env.example .env
# Edit .env and add your credentials
```

The `.env` file supports:
- `ICLOUD_APPLE_ID`, `ICLOUD_PASSWORD`, `ICLOUD_2FA_CODE`, `ICLOUD_2FA_DEVICE_ID`
- `GOOGLE_DRIVE_CREDENTIALS_FILE`
- `GITHUB_TOKEN` (for repository management scripts)

Environment variables take precedence over `config.yaml` values. See [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) for details.

## Usage

### Web UI (Recommended)

Start the modern web interface for an intuitive, visual migration experience:

```bash
python3 web_server.py
```

Then open your browser to `http://localhost:5001`

> **Note:** The web UI provides real-time progress tracking, live statistics, and activity logs - perfect for monitoring long-running migrations.

See [WEB_UI.md](WEB_UI.md) for detailed web UI documentation.

### Command Line Usage

```bash
python main.py --config config.yaml
```

### Using Photos Library Sync Method (Recommended - Default in Web UI)

For the most reliable uploads with full EXIF metadata preservation, use the PhotoKit-based sync method (macOS only). **This is now the default in the Web UI.**

**Web UI**: PhotoKit sync is enabled by default - just start the migration.

**Command Line**:
```bash
python main.py --config config.yaml --use-sync
```

This method uses Apple's PhotoKit framework to save photos directly to your Photos library, which then automatically syncs to iCloud Photos. This approach:
- Preserves all EXIF metadata (GPS, dates, camera info)
- Supports album organization
- Is more reliable than API-based methods
- Requires macOS and photo library write permission

### Retrying Failed Uploads

If some files fail to upload, they are automatically saved to `failed_uploads.json`. To retry only the failed uploads (skipping download/extract/process steps):

```bash
python main.py --config config.yaml --retry-failed
```

You can also combine with `--use-sync`:

```bash
python main.py --config config.yaml --retry-failed --use-sync
```


## How It Works

1. **Download**: Downloads all Google Takeout zip files from Google Drive
2. **Extract**: Extracts zip files maintaining directory structure
3. **Process Metadata**: Merges JSON metadata into media files using ExifTool
4. **Parse Albums**: Extracts album structure from directory hierarchy and JSON metadata
5. **Upload**: Uploads processed files to iCloud Photos
6. **Cleanup**: Removes temporary files (if configured)

## Metadata Preservation

The tool preserves:
- **Dates**: Photo taken time from `PhotoTakenTimeTimestamp`
- **GPS Coordinates**: Latitude/longitude from `geoData`
- **Descriptions**: Captions and descriptions from JSON metadata
- **Album Structure**: Album organization from directory structure and JSON

## iCloud Photos Upload Methods

### Method 1: API Upload (Default)
Uses `pyicloud` library to attempt direct upload. **Note:** Apple doesn't provide a public REST API for iCloud Photos, so this method has significant limitations and may not work reliably.

### Method 2: PhotoKit Library Sync (macOS - Recommended)
Uses Apple's PhotoKit framework (via `pyobjc-framework-Photos`) to save photos directly to the Photos library using `PHPhotoLibrary` and `PHAssetChangeRequest`. Photos then automatically syncs to iCloud Photos if iCloud Photos is enabled. This method:
- **Preserves EXIF metadata** by using file URLs instead of image objects
- **Supports albums** via PhotoKit's album management
- **Requires macOS** and photo library write permission
- **Automatically syncs** to iCloud Photos when enabled in System Settings

**Prerequisites:**
- macOS (required for PhotoKit)
- `pyobjc-framework-Photos` package (installed via requirements.txt)
- Photo library write permission (granted on first use)

## Authentication

For detailed authentication setup, see [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md).

**Quick Setup:** Run the interactive authentication wizard:
```bash
python3 auth_setup.py
```

This will guide you through:
- Google Drive OAuth setup (opens browser automatically)
- Apple/iCloud configuration (no auth needed for PhotoKit method)
- Creating your `config.yaml` file

## Troubleshooting

### ExifTool Not Found
Install ExifTool:
- macOS: `brew install exiftool`
- Linux: `apt-get install libimage-exiftool-perl` or `yum install perl-Image-ExifTool`

### 2FA Authentication Issues (API method only)
- **Note**: The PhotoKit sync method (`--use-sync`) doesn't require authentication - it uses your macOS iCloud account automatically
- **For API method**: 
  - Check status: Run `python3 check-auth-status.py` to see authentication status
  - Use environment variables: `ICLOUD_2FA_DEVICE_ID` and `ICLOUD_2FA_CODE`
  - Or use trusted device ID in config.yaml and run interactively

### PhotoKit Permission Issues (--use-sync method)
- If you see "Photo library write permission denied":
  - Grant permission in **System Settings > Privacy & Security > Photos**
  - Ensure the app has "Add Photos Only" or "Read and Write" permission
  - Restart the migration after granting permission
- If `pyobjc-framework-Photos` is not found:
  - Install it: `pip install pyobjc-framework-Photos`
  - Or reinstall all dependencies: `pip install -r requirements.txt`
- If you're not on macOS:
  - PhotoKit method requires macOS. Use the API method instead (without `--use-sync`)

### Upload Failures
- Failed uploads are automatically saved to `failed_uploads.json` in the base directory
- To retry failed uploads, run:
  ```bash
  python main.py --config config.yaml --retry-failed
  ```
- The retry command will:
  - Load the list of previously failed files
  - Attempt to upload them again
  - Update the failed uploads file (removing successful ones)
  - Show progress and final results
- If uploads continue to fail:
  - Try using `--use-sync` flag for PhotoKit sync method (macOS only, recommended)
  - Check iCloud storage space
  - Verify Apple ID credentials (for API method)
  - Check network connectivity
  - Review error messages in the log file

### Large File Processing
- Adjust `batch_size` in config.yaml
- Ensure your Mac has sufficient disk space (at least 2x your Google Photos data size)
- Process in smaller batches if needed

## Limitations

- **Album Creation**: PhotoKit supports album creation, but it requires proper permissions. Albums are created automatically when using the `--use-sync` method.
- **Upload Method**: Direct API uploads via `pyicloud` may not be fully supported as Apple doesn't provide a public REST API. The PhotoKit sync method (`--use-sync`) is recommended for reliability and metadata preservation.
- **Platform**: PhotoKit sync method requires macOS. API method can be used on other platforms but has limitations.
- **2FA**: Requires interactive input or trusted device configuration for API method.
- **Permissions**: PhotoKit method requires photo library write permission, which is requested automatically on first use.

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

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes (for users with prerequisites installed)
- **[WEB_UI.md](WEB_UI.md)** - Modern web interface guide with real-time progress tracking
- **[COMPLETE_INSTALLATION_GUIDE.md](COMPLETE_INSTALLATION_GUIDE.md)** - Step-by-step setup on a new MacBook
- **[AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md)** - Detailed authentication setup guide
- **[TESTING.md](TESTING.md)** - Test the migration before running the full process

## Notes

- The tool processes files in batches to manage memory and disk space
- Extracted files are kept until upload completes (unless cleanup is enabled)
- Metadata merging preserves original files (creates processed copies)
- Album structures are extracted but may need manual recreation in iCloud Photos

