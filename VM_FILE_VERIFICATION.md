# VM File Verification Guide

This document helps you verify that files on your VM match the expected versions, especially after the recent 2FA authentication fixes.

## Quick Verification

### Option 1: Run the Verification Script (Recommended)

**On your VM**, run:

```bash
# Download and run the verification script
curl -O https://raw.githubusercontent.com/your-repo/google-photos-icloud-migration/main/verify-vm-files.sh
# Or copy it from your local machine first
chmod +x verify-vm-files.sh
./verify-vm-files.sh
```

Or use the Python version:

```bash
python3 verify-vm-files.py
```

### Option 2: Manual Verification

**On your VM**, check these key patterns in `icloud_uploader.py`:

```bash
# Check for manual_service_creation initialization
grep -n "manual_service_creation = False" icloud_uploader.py

# Check for 2FA handling after exception handlers
grep -n "If 2FA was detected in exception handler" icloud_uploader.py

# Check for manual service creation flag check
grep -n "if manual_service_creation:" icloud_uploader.py

# Check for 2FA code entry prompt
grep -n "Enter 2FA code (attempt" icloud_uploader.py
```

All of these should return line numbers if the file is up to date.

## Expected File Versions

### icloud_uploader.py

**Key Changes Made (2025-11-26):**

1. **Variable Initialization** (around line 84):
   - `manual_service_creation = False` should be initialized at method level
   - `needs_2fa = False` should be initialized at method level

2. **Improved 2FA Detection** (around lines 207-245):
   - Detects 2FA from `PyiCloudFailedLoginException` by checking exception chain
   - Detects 2FA from traceback patterns (HSA2, PyiCloud2FARequiredException)
   - Manually creates service object when 2FA is detected

3. **2FA Handling After Exception Handlers** (around lines 656-740):
   - New section that handles 2FA if detected in exception handler
   - Triggers authentication to populate trusted devices
   - Handles device selection and code entry

4. **Key Code Patterns That Must Exist:**

```python
# Around line 84
manual_service_creation = False

# Around line 207-224
if not is_2fa and ("PyiCloud2FARequiredException" in tb_str or "HSA2" in tb_str...

# Around line 230-242
self.api = PyiCloudService.__new__(PyiCloudService)
manual_service_creation = True

# Around line 656-660
# If 2FA was detected in exception handler, handle it now
if needs_2fa and hasattr(self, 'api') and self.api is not None:
    if manual_service_creation:
        self.api._authenticate()
```

### main.py

Should have:
- `setup_icloud_uploader()` method
- `run()` method
- Uses `iCloudUploader` class

## Verification Checklist

Run these checks **on your VM**:

- [ ] `icloud_uploader.py` exists in home directory
- [ ] `main.py` exists in home directory
- [ ] `icloud_uploader.py` contains `manual_service_creation = False` (line ~84)
- [ ] `icloud_uploader.py` contains `# If 2FA was detected in exception handler` (line ~656)
- [ ] `icloud_uploader.py` contains `if manual_service_creation:` (line ~660)
- [ ] `icloud_uploader.py` contains `Enter 2FA code (attempt` (line ~700+)

## If Files Don't Match

If verification fails, update the files using one of these methods:

### Method 1: Use Sync Script (from local machine)

```bash
./sync-to-vm.sh photos-migration-vm
```

### Method 2: Use gcloud (from local machine)

```bash
gcloud compute scp icloud_uploader.py main.py photos-migration-vm:~/ --zone=YOUR_ZONE
```

### Method 3: Manual Copy (from local machine)

```bash
scp icloud_uploader.py main.py skipshean@photos-migration-vm:~/
```

### Method 4: Git Pull (on VM)

If you have a git repository on the VM:

```bash
cd ~/google-photos-icloud-migration  # or wherever your repo is
git pull origin main
cp icloud_uploader.py main.py ~/
```

## File Locations

Files should be in:
- `/home/skip/` (or `/home/skipshean/` depending on your VM setup)
- Or in the current working directory when you run `main.py`

## Testing After Update

After updating files, test the 2FA fix:

```bash
python3 main.py --config config.yaml
```

You should see:
1. Authentication attempt
2. 2FA detection from exception traceback
3. Manual service creation
4. Device selection prompt (if no trusted_device_id in config)
5. 2FA code entry prompt

## Troubleshooting

If verification script fails:

1. **Check file location**: Make sure you're in the directory containing the files
2. **Check file permissions**: Files should be readable
3. **Check Python version**: Script requires Python 3
4. **Manual check**: Use `grep` commands above to verify patterns exist

If files still don't match after updating:

1. Check that you copied from the correct source (local machine with latest changes)
2. Verify file timestamps: `ls -lh icloud_uploader.py main.py`
3. Check file sizes match between local and VM
4. Compare checksums: `md5sum icloud_uploader.py` on both machines


