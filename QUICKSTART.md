# Quick Start Guide

Get started with the Google Photos to iCloud migration in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] ExifTool installed (`brew install exiftool` on macOS)
- [ ] Google Drive API credentials (`credentials.json`)
- [ ] Apple ID credentials
- [ ] Google Takeout zip files in Google Drive

## Setup (5 minutes)

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the Authentication Setup Wizard (Recommended):**
```bash
python3 auth_setup.py
```
This will guide you through Google Drive OAuth setup and create your `config.yaml` file automatically.

**OR** configure manually:
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
```

3. **Run the migration:**

   **Option A: Process local zip files (if you already have Google Takeout zips):**
   ```bash
   python3 process_local_zips.py --use-sync --takeout-dir "/path/to/your/zips"
   ```
   
   **Option B: Download from Google Drive and process:**
   ```bash
   python3 main.py --config config.yaml --use-sync
   ```
   
   Both methods use Apple's PhotoKit framework to save photos directly to your Photos library, which then syncs to iCloud Photos automatically.

## Configuration Essentials

Minimum required settings in `config.yaml`:

```yaml
google_drive:
  credentials_file: "credentials.json"
  zip_file_pattern: "takeout-*.zip"

icloud:
  apple_id: "your-email@example.com"
  password: ""  # Leave empty to be prompted

processing:
  base_dir: "/tmp/google-photos-migration"
```

**Optional:** For better security, store sensitive credentials (passwords, API tokens) in a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your credentials
```
Environment variables in `.env` take precedence over `config.yaml`. See [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) for details.

## First Run

1. **Download phase**: Authenticate with Google Drive (browser opens automatically)
2. **Extraction phase**: Automatically extracts all zip files
3. **Metadata phase**: Merges JSON metadata into files
4. **Upload phase**: Photos are saved to your Photos library using PhotoKit (no authentication needed - uses your macOS iCloud account)
5. **Sync phase**: Photos automatically sync to iCloud Photos if enabled in System Settings

## Expected Timeline

- **Small library** (<10GB): 1-2 hours
- **Medium library** (10-100GB): 4-8 hours  
- **Large library** (100GB+): 1-3 days

## Troubleshooting

**Problem**: "ExifTool not found"
- **Solution**: Install ExifTool (see README.md)

**Problem**: "Google Drive authentication failed"
- **Solution**: Check credentials.json path and OAuth setup

**Problem**: "iCloud upload not working"
- **Solution**: Try `--use-sync` flag (macOS only)

**Problem**: "Out of disk space"
- **Solution**: Process in smaller batches, enable cleanup

## Next Steps

- Read **README.md** for detailed documentation
- Read **COMPLETE_INSTALLATION_GUIDE.md** for step-by-step setup on a new MacBook
- Read **AUTHENTICATION_GUIDE.md** for authentication details
- Read **TESTING.md** to test before full migration

## Support

Check logs: `tail -f migration.log`

For detailed error messages, set logging level to DEBUG in config.yaml.

