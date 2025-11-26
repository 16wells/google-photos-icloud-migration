# Instructions to Update Files on VM

Since you chose Option 2, here's how to update the files directly on your VM.

## Step 1: Backup Current Files

On your VM, run:
```bash
cp main.py main.py.backup
cp drive_downloader.py drive_downloader.py.backup
```

## Step 2: Update drive_downloader.py

The file needs these changes:
1. Add `import shutil` at the top
2. Add `_check_disk_space()` method
3. Update `download_file()` to accept `file_size` parameter
4. Add disk space checking in `download_file()`
5. Add `download_single_zip()` method

**Easiest way**: Replace the entire file. See the complete file content below.

## Step 3: Update main.py

The file needs these changes:
1. Update `_setup_logging()` to handle disk space errors
2. Add `_find_existing_zips()` method
3. Completely rewrite `run()` method to process files one at a time

**Easiest way**: Replace the entire file. See the complete file content below.

## Quick Update Method

On your VM, you can use Python to create the files:

```bash
python3 << 'ENDPYTHON'
# This will create the updated files
# (Files will be provided in separate steps)
ENDPYTHON
```

Or simply use a text editor to replace the files entirely.

## Verification

After updating, verify the changes:

```bash
grep -n "_find_existing_zips" main.py
grep -n "_check_disk_space" drive_downloader.py
grep -n "Phase 1: Listing zip files" main.py
```

You should see:
- Line numbers for `_find_existing_zips` in main.py
- Line numbers for `_check_disk_space` in drive_downloader.py  
- "Phase 1: Listing zip files" (not "Downloading zip files")

