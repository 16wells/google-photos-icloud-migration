# Google Photos to iCloud Photos Migration Tool

A cloud-based tool to migrate photos and videos from Google Photos (exported via Google Takeout) to iCloud Photos, preserving metadata and album structures.

## Features

- Downloads Google Takeout zip files from Google Drive
- Extracts and processes media files (HEIC, JPG, AVI, MOV, MP4)
- Merges JSON metadata into media files using ExifTool
- Preserves album structures from Google Takeout
- Uploads to iCloud Photos (via API or Photos library sync)
- Runs entirely in the cloud (Google Cloud Platform)

## Prerequisites

### Local Development
- Python 3.8+
- ExifTool (install via `brew install exiftool` on macOS or `apt-get install libimage-exiftool-perl` on Linux)
- Google Drive API credentials

### GCP VM Setup
- Google Cloud Platform account
- VM instance with sufficient storage
- Python 3.8+ and ExifTool installed

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Drive API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials JSON file and save as `credentials.json`

4. Configure the tool:
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

## Usage

### Basic Usage

```bash
python main.py --config config.yaml
```

### Using Photos Library Sync Method

If direct API upload doesn't work, you can use the Photos library sync method (macOS only):

```bash
python main.py --config config.yaml --use-sync
```

This method copies files to your Photos library, which then syncs to iCloud Photos automatically.

### Retrying Failed Uploads

If some files fail to upload, they are automatically saved to `failed_uploads.json`. To retry only the failed uploads (skipping download/extract/process steps):

```bash
python main.py --config config.yaml --retry-failed
```

You can also combine with `--use-sync`:

```bash
python main.py --config config.yaml --retry-failed --use-sync
```

### Running on GCP VM

1. Set up the VM:
```bash
chmod +x setup.sh
./setup.sh
```

2. Upload your configuration files:
   - `credentials.json` (Google Drive API credentials)
   - `config.yaml` (configuration file)

3. Run the migration:
```bash
python3 main.py --config config.yaml
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
Uses `pyicloud` library to upload directly. Note: Apple doesn't provide a public API for iCloud Photos, so this method may have limitations.

### Method 2: Photos Library Sync (macOS)
Copies files to Photos library directory, which syncs to iCloud Photos automatically. This is more reliable but requires macOS.

## Troubleshooting

### ExifTool Not Found
Install ExifTool:
- macOS: `brew install exiftool`
- Linux: `apt-get install libimage-exiftool-perl` or `yum install perl-Image-ExifTool`

### 2FA Authentication Issues
- Use a trusted device ID in config.yaml
- Or run interactively and enter code when prompted

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
  - Try using `--use-sync` flag for Photos library sync method
  - Check iCloud storage space
  - Verify Apple ID credentials
  - Check network connectivity
  - Review error messages in the log file

### Large File Processing
- Adjust `batch_size` in config.yaml
- Ensure VM has sufficient disk space
- Process in smaller batches if needed

## Limitations

- **Album Creation**: iCloud Photos API doesn't support programmatic album creation. Albums may need to be created manually.
- **Upload Method**: Direct API uploads may not be fully supported. Photos library sync method is more reliable.
- **2FA**: Requires interactive input or trusted device configuration.

## Cost Estimation

- **GCP VM**: ~$50-200 depending on instance size and runtime
- **Storage**: Minimal if processing in batches
- **Network**: Minimal (uploading to iCloud, not downloading)

## License

This tool is provided as-is for personal use.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `migration.log`
3. Ensure all prerequisites are installed

## Notes

- The tool processes files in batches to manage memory and disk space
- Extracted files are kept until upload completes (unless cleanup is enabled)
- Metadata merging preserves original files (creates processed copies)
- Album structures are extracted but may need manual recreation in iCloud Photos

