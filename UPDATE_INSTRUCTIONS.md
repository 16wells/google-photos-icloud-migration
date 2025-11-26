# Updating Files on VM

The migration script has been updated to handle disk space issues. You need to update the files on your VM.

## Quick Update Methods

### Method 1: Using the Sync Script (Recommended)

From your **local machine** (where you have the updated files):

```bash
./sync-to-vm.sh skipshean@photos-migration-vm
```

Or if your VM has a different path:
```bash
./sync-to-vm.sh skipshean@photos-migration-vm /home/skipshean
```

This will copy the updated `main.py` and `drive_downloader.py` files to your VM.

### Method 2: Manual Copy with SCP

From your **local machine**:

```bash
scp main.py drive_downloader.py skipshean@photos-migration-vm:~/
```

### Method 3: Using Git (if you've pushed to GitHub)

On your **VM**:

```bash
cd ~
git clone https://github.com/16wells/google-photos-icloud-migration.git
# Or if you already have it:
cd google-photos-icloud-migration
git pull origin main

# Copy updated files to your working directory
cp main.py drive_downloader.py /path/to/your/working/directory/
```

### Method 4: Manual File Edit

If you can't copy files, you can manually edit the files on the VM. The key changes are:

1. **main.py**: The `run()` method now processes files one at a time
2. **drive_downloader.py**: Added `_check_disk_space()` method and `download_single_zip()` method

## Verify Update

After updating, verify the changes worked:

```bash
# Check that the new method exists
grep -n "_find_existing_zips" main.py
grep -n "_check_disk_space" drive_downloader.py

# Check the run method uses list_zip_files instead of download_all_zips
grep -A 5 "def run" main.py | grep "list_zip_files"
```

## What Changed

### Key Improvements:

1. **Processes existing files first** - Finds already-downloaded zip files and processes them before downloading new ones
2. **One-at-a-time processing** - Downloads, processes, and deletes each zip file individually
3. **Disk space checking** - Checks available disk space before downloading
4. **Resilient logging** - Continues working even if log file can't be written (disk full)

### Files Updated:

- `main.py` - Updated `run()` method and added `_find_existing_zips()` method
- `drive_downloader.py` - Added `_check_disk_space()` and `download_single_zip()` methods

## After Updating

Once files are updated, run:

```bash
python3 main.py --config config.yaml
```

The script will now:
1. Detect your 10 existing zip files (~100GB)
2. Process them first to free up space
3. Delete each zip after successful processing
4. Then download and process remaining files one at a time

