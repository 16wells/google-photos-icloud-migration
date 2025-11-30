# Logging and Resumption Analysis

## Current Logging Coverage

### ✅ What IS Currently Logged

1. **Zip Downloads**
   - Download start/completion logged via `logger.info()` in `drive_downloader.py`
   - Download errors logged via `logger.error()` and `logger.warning()`
   - Partial downloads detected and logged
   - All logged to `migration.log` with rotation

2. **Zip Extractions**
   - Extraction start/completion logged in `extractor.py`
   - Extraction errors logged (corrupted zip detection)
   - Progress bars shown during extraction
   - All logged to `migration.log`

3. **File Conversions (Metadata Merging)**
   - Metadata processing logged in `metadata_merger.py`
   - ExifTool operations logged (success/failure per file)
   - Batch processing progress logged
   - Errors logged with file names
   - All logged to `migration.log`

4. **Apple Photos Copying (PhotoKit Sync Method)**
   - File save attempts logged in `iCloudPhotosSyncUploader.upload_file()`
   - Success/failure logged per file
   - Album creation logged
   - Permission errors logged
   - **However**: Detailed copy attempt status (e.g., "attempting to copy", "copy in progress") is not extensively logged

5. **iCloud Uploads**
   - Upload start/completion logged in `icloud_uploader.py`
   - Batch upload progress logged
   - Verification results logged
   - Upload errors logged with file names
   - All logged to `migration.log`

### ⚠️ Logging Gaps

1. **Photos Library Copy Status**
   - Basic success/failure is logged, but intermediate states (e.g., "copying to Photos library", "waiting for Photos sync") are not detailed
   - No logging of Photos library sync status checks

2. **File Processing State**
   - No granular logging of which specific step a file is in (extracted → converted → copied to Photos → synced to iCloud)
   - If a file fails mid-process, it's not clear which step failed

## State Persistence and Resumption

### ✅ What IS Persisted

1. **Upload Tracking** (`uploaded_files.json`)
   - Tracks successfully uploaded files by file identifier (hash of path + size + mtime)
   - Includes: file path, name, size, album name, upload timestamp, asset identifier
   - Used to skip already-uploaded files on resume

2. **Failed Uploads** (`failed_uploads.json`)
   - Tracks files that failed to upload
   - Includes: file path, album name, error information
   - Used for retry functionality

3. **Corrupted Zips** (`corrupted_zips.json`)
   - Tracks corrupted zip files
   - Includes: file ID, name, size, error message, timestamp
   - Used to identify files that need re-downloading

4. **Existing Zip Files on Disk**
   - The program checks for existing zip files in the zip directory
   - If a zip file exists and appears complete, it skips re-downloading
   - Processes existing zips FIRST to free up disk space

### ❌ What is NOT Persisted

1. **Extraction State**
   - No tracking file for which zips have been extracted
   - Relies on zip file existence (if zip exists, it may or may not be extracted)
   - If a zip is extracted but processing fails, it will re-extract on resume

2. **Metadata Processing State**
   - No tracking file for which files have been converted/processed
   - Relies on processed files existing in `processed_dir`
   - If processing is interrupted, it will re-process files

3. **Photos Library Copy State**
   - Only tracked if upload succeeds (via `uploaded_files.json`)
   - If a file is copied to Photos but sync fails, it's not tracked
   - No way to know which files are in Photos but not yet synced to iCloud

4. **Partial Zip Processing State**
   - If a zip is partially processed (e.g., extracted but not uploaded), there's no state file
   - On resume, it will re-extract and re-process the entire zip

5. **Per-Zip Progress**
   - No checkpoint file tracking which zip is currently being processed
   - If interrupted mid-zip, it will restart that zip from the beginning

## How Resumption Currently Works

### When You Restart the Program

1. **Zip File Detection**
   - Lists all zip files from Google Drive
   - Checks for existing zip files on disk
   - Processes existing zips FIRST (to free up space)

2. **Upload Tracking Check**
   - Loads `uploaded_files.json` if it exists
   - Skips files that are already in the tracking file
   - Prompts user whether to continue existing migration or start fresh

3. **Processing Flow**
   - For each zip file:
     - If zip exists on disk → process it
     - If zip doesn't exist → download it, then process it
   - Processing includes: extract → convert → upload → cleanup

### ⚠️ Resumption Limitations

1. **No Granular Resume**
   - If a zip is partially processed, it will restart from extraction
   - Cannot resume from "conversion complete, upload in progress"

2. **No Per-File State Tracking**
   - Cannot track which files in a zip have been processed
   - If a zip has 1000 files and 999 are uploaded, it will re-process all 1000

3. **Extracted Files Cleanup**
   - Extracted files are cleaned up after successful upload
   - If upload fails, extracted files remain, but there's no state tracking this

## Retry Mechanisms in Terminal Mode

### Current Retry Functionality

1. **Failed Upload Retry** (`--retry-failed` flag)
   - Reads `failed_uploads.json`
   - Retries only the files that failed to upload
   - Skips download/extract/convert steps
   - Works for both API upload and Photos sync methods

2. **Automatic Retry on Resume**
   - When restarting, existing zip files are processed
   - If a zip had failed uploads, it will attempt to upload again
   - But it will also re-extract and re-convert (inefficient)

3. **Corrupted Zip Handling**
   - Corrupted zips are saved to `corrupted_zips.json`
   - User can manually re-download them
   - Program will wait for redownload in web UI mode

### ❌ Missing Retry Functionality

1. **No Retry for Failed Extractions**
   - If extraction fails, zip is marked as corrupted
   - No automatic retry of extraction

2. **No Retry for Failed Conversions**
   - If metadata merging fails for a file, it's logged but not retried
   - File will be skipped or uploaded without metadata

3. **No Retry for Failed Photos Copies**
   - If copying to Photos library fails, it's logged but not automatically retried
   - Only tracked if it's part of a failed upload

4. **No Per-Step Retry**
   - Cannot retry just the "Photos copy" step without re-uploading
   - Cannot retry just the "iCloud sync" step

## Recommendations for Improvement

### High Priority

1. **Add Per-Zip State Tracking**
   - Create `zip_processing_state.json` to track:
     - Which zips have been extracted
     - Which zips have been converted
     - Which zips have been uploaded
   - Allows resuming from any step

2. **Add Per-File Processing State**
   - Track each file's state: `pending` → `extracted` → `converted` → `copied_to_photos` → `synced_to_icloud`
   - Store in `file_processing_state.json`
   - Allows resuming from exact point of failure

3. **Enhance Photos Copy Logging**
   - Log detailed status: "Copying to Photos library", "Waiting for Photos sync", "Sync complete"
   - Track Photos library sync status in state file

4. **Add Retry for Each Step**
   - `--retry-failed-extractions`: Retry only failed extractions
   - `--retry-failed-conversions`: Retry only failed conversions
   - `--retry-failed-photos-copies`: Retry only failed Photos library copies
   - `--retry-failed-uploads`: Already exists

### Medium Priority

5. **Checkpoint System**
   - Save checkpoint after each major step (extract, convert, upload)
   - On resume, check checkpoint and continue from there

6. **Better Error Recovery**
   - If a file fails at conversion step, mark it and continue
   - Allow retrying just that step later

7. **Photos Sync Status Monitoring**
   - Periodically check Photos library for sync status
   - Log which files are still syncing
   - Track sync completion in state file

### Low Priority

8. **Detailed Progress Logging**
   - Log every file's progress through the pipeline
   - Make it easier to see exactly where a file is stuck

9. **Resume from Specific Zip**
   - Allow `--resume-from-zip <zip_name>` to resume from a specific zip
   - Useful if you know which zip was being processed

## Current Workarounds

### For Terminal Mode

1. **To Retry Failed Uploads Only**
   ```bash
   python -m google_photos_icloud_migration.cli.main --retry-failed
   ```

2. **To Resume from Interruption**
   - Simply restart the program
   - It will detect existing zip files and process them
   - Already-uploaded files will be skipped (if `uploaded_files.json` exists)

3. **To Handle Corrupted Zips**
   - Check `corrupted_zips.json` for file IDs
   - Manually re-download from Google Drive
   - Restart the program

### Limitations of Workarounds

- If a zip is partially processed, it will re-extract and re-convert (wasteful)
- Cannot resume from mid-zip processing
- Cannot retry individual steps (extraction, conversion, Photos copy) separately

## Conclusion

**Current State:**
- ✅ Logging covers all major steps (download, extract, convert, upload)
- ✅ Basic resumption works (skips already-uploaded files, processes existing zips)
- ✅ Failed uploads can be retried
- ❌ No granular state tracking for intermediate steps
- ❌ Cannot resume from mid-zip processing
- ❌ Cannot retry individual steps (extraction, conversion, Photos copy)

**For Your Use Case:**
The current system will log all the information you need, but resumption is not as granular as it could be. If a run is interrupted:
- It will skip already-uploaded files ✅
- It will process existing zip files ✅
- But it will re-extract and re-convert files that were partially processed ❌

For retries in terminal mode:
- Failed uploads can be retried with `--retry-failed` ✅
- But failed extractions, conversions, or Photos copies cannot be retried separately ❌






