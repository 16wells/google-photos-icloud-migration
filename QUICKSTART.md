# Quick Start Guide

Get started with the Google Photos to iCloud migration in 5 minutes.

## Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] ExifTool installed (`brew install exiftool` on macOS)
- [ ] Google Drive API credentials (`credentials.json`)
- [ ] Apple ID credentials
- [ ] 62 Google Takeout zip files in Google Drive

## Local Setup (5 minutes)

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure:**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
```

3. **Run:**
```bash
python main.py --config config.yaml
```

## GCP VM Setup (15 minutes)

1. **Follow GCP_SETUP.md** to create VM and upload files

2. **On VM, run:**
```bash
chmod +x setup.sh
./setup.sh
cp config.yaml.example config.yaml
# Edit config.yaml
python3 main.py --config config.yaml
```

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

## First Run

1. **Download phase**: Authenticate with Google Drive (browser opens)
2. **Extraction phase**: Automatically extracts all zip files
3. **Metadata phase**: Merges JSON metadata into files
4. **Upload phase**: Authenticate with iCloud (may need 2FA code)

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
- Read **GCP_SETUP.md** for cloud setup
- Read **TESTING.md** to test before full migration

## Support

Check logs: `tail -f migration.log`

For detailed error messages, set logging level to DEBUG in config.yaml.

