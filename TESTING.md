# Testing Guide

This guide explains how to test the Google Photos to iCloud migration tool before running it on your full library.

## Prerequisites for Testing

1. Have at least one Google Takeout zip file available (can be a small test export)
2. Set up Google Drive API credentials
3. Configure iCloud credentials
4. Have ExifTool installed

## Step 1: Create a Test Configuration

1. Copy the example config:
```bash
cp config.yaml.example config.yaml
```

2. Create a test-specific config:
```bash
cp config.yaml config.test.yaml
```

3. Edit `config.test.yaml`:
   - Set `processing.base_dir` to a test directory: `/tmp/test-migration`
   - Set `processing.batch_size` to a small number: `10`
   - Set `processing.cleanup_after_upload` to `false` (so you can inspect files)
   - Set `logging.level` to `DEBUG` for more detailed output

## Step 2: Test with a Single Zip File

### Option A: Test Download from Google Drive

1. Upload a small test zip file to Google Drive
2. Note the folder ID or file name pattern
3. Update `config.test.yaml` with the folder ID or pattern
4. Run:
```bash
python3 main.py --config config.test.yaml
```

### Option B: Test with Local Zip File

If you already have a zip file locally, you can test the extraction and processing:

1. Create a test script `test_local.py`:
```python
from pathlib import Path
from extractor import Extractor
from metadata_merger import MetadataMerger
from album_parser import AlbumParser

# Test extraction
extractor = Extractor(Path("/tmp/test-migration"))
extracted_dir = extractor.extract_zip(Path("test-takeout.zip"))

# Test metadata identification
pairs = extractor.identify_media_json_pairs(extracted_dir)
print(f"Found {len(pairs)} media files")

# Test metadata merging (on a few files)
merger = MetadataMerger()
test_files = list(pairs.items())[:5]  # Test first 5 files
for media_file, json_file in test_files:
    success = merger.merge_metadata(media_file, json_file)
    print(f"{media_file.name}: {'✓' if success else '✗'}")

# Test album parsing
parser = AlbumParser()
albums = parser.parse_from_directory_structure(extracted_dir)
print(f"Found {len(albums)} albums")
for album_name, files in list(albums.items())[:3]:
    print(f"  {album_name}: {len(files)} files")
```

2. Run the test:
```bash
python3 test_local.py
```

## Step 3: Verify Metadata Merging

After running the metadata merger, verify that metadata was correctly embedded:

```bash
# Check a processed file
exiftool processed/IMG_001.jpg

# Look for:
# - Date/Time: Should match PhotoTakenTimeTimestamp from JSON
# - GPS Coordinates: Should match geoData from JSON
# - Description: Should match description from JSON
```

Compare with the original JSON:
```bash
cat extracted/*/IMG_001.json
```

## Step 4: Test iCloud Upload (Small Batch)

Before uploading everything, test with a small batch:

1. Create a test upload script `test_upload.py`:
```python
from pathlib import Path
from icloud_uploader import iCloudUploader, iCloudPhotosSyncUploader
import yaml

# Load config
with open('config.test.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test with a few files
test_files = [
    Path("processed/IMG_001.jpg"),
    Path("processed/IMG_002.jpg"),
]

# Option 1: Try API upload
try:
    uploader = iCloudUploader(
        apple_id=config['icloud']['apple_id'],
        password=config['icloud'].get('password', ''),
        trusted_device_id=config['icloud'].get('trusted_device_id')
    )
    results = uploader.upload_photos_batch(test_files)
    print(f"Upload results: {results}")
except Exception as e:
    print(f"API upload failed: {e}")
    print("Try using --use-sync method instead")
```

2. Run:
```bash
python3 test_upload.py
```

## Step 5: Verify Upload Success

1. Check iCloud Photos web interface or Photos app
2. Verify:
   - Files appear in iCloud Photos
   - Dates are correct
   - GPS locations are preserved (if applicable)
   - Descriptions are present

## Step 6: Test Album Structure

1. After uploading test files, check if albums were created
2. Note: Albums may need to be created manually in iCloud Photos
3. Verify files can be organized into albums

## Common Test Scenarios

### Test 1: Small Export (1-10 files)
- Purpose: Verify basic functionality
- Expected time: 5-10 minutes
- What to check:
  - Download works
  - Extraction works
  - Metadata merging works
  - Upload works

### Test 2: Medium Export (100-1000 files)
- Purpose: Test batch processing and performance
- Expected time: 30-60 minutes
- What to check:
  - Batch processing works correctly
  - Memory usage is reasonable
  - No errors in processing
  - All files are processed

### Test 3: Full Migration (All 62 zip files)
- Purpose: Complete migration
- Expected time: Several hours to days
- What to check:
  - Progress logging
  - Error recovery
  - Disk space management
  - Final verification

## Troubleshooting Tests

### Issue: ExifTool not found
```bash
# Check if installed
exiftool -ver

# Install if needed
# macOS:
brew install exiftool

# Linux:
sudo apt-get install libimage-exiftool-perl
```

### Issue: Google Drive authentication fails
- Check credentials.json is in the correct location
- Verify OAuth consent screen is configured
- Check that Google Drive API is enabled

### Issue: iCloud authentication fails
- Verify Apple ID credentials
- Check 2FA is working (may need to enter code interactively)
- Try using Photos library sync method instead

### Issue: Metadata not merging
- Check JSON file exists and is valid
- Verify ExifTool can read/write the file format
- Check ExifTool version (should be 12.0+)

### Issue: Upload fails
- Check iCloud storage space
- Verify network connection
- Try smaller batch size
- Consider using Photos library sync method

## Performance Testing

To test performance with different batch sizes:

1. Create performance test script:
```python
import time
from pathlib import Path
from metadata_merger import MetadataMerger

merger = MetadataMerger()

# Test different batch sizes
for batch_size in [10, 50, 100, 500]:
    test_files = list(Path("extracted").rglob("*.jpg"))[:batch_size]
    
    start = time.time()
    for f in test_files:
        json_file = f.with_suffix('.json')
        merger.merge_metadata(f, json_file if json_file.exists() else None)
    elapsed = time.time() - start
    
    print(f"Batch size {batch_size}: {elapsed:.2f}s ({elapsed/batch_size:.3f}s per file)")
```

## Validation Checklist

Before running full migration, verify:

- [ ] Test download works
- [ ] Test extraction works
- [ ] Test metadata merging works (verify with exiftool)
- [ ] Test upload works (verify files appear in iCloud)
- [ ] Test album parsing works
- [ ] Test cleanup works (if enabled)
- [ ] Logging is working correctly
- [ ] Error handling works (test with invalid file)
- [ ] Disk space is sufficient
- [ ] Network connection is stable

## Next Steps

After successful testing:

1. Update `config.yaml` with production settings
2. Ensure sufficient disk space on your Mac (at least 2x your Google Photos data size)
3. Run full migration: `python3 main.py --config config.yaml --use-sync`
4. Monitor progress: `tail -f migration.log`
5. Verify results in iCloud Photos

