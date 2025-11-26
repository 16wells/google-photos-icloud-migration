# How to Get 2FA Helper Scripts on Your VM

The new 2FA helper scripts need to be transferred to your VM. Here are the easiest methods:

## Quick Method: Use the Transfer Script

**On your local machine**, run:

```bash
./transfer-2fa-helpers-to-vm.sh photos-migration-vm us-central1-c
```

Or update the sync script to include helpers:

```bash
./sync-to-vm.sh photos-migration-vm
```

## Easiest Method: Browser SSH (If gcloud doesn't work)

### Step 1: Open Browser SSH

1. Go to: https://console.cloud.google.com/compute/instances?project=photos-migration-2025
2. Find `photos-migration-vm` 
3. Click the **"SSH"** button

### Step 2: Transfer Each File

For each file, run this in Browser SSH:

```bash
cat > setup-vm-2fa.sh << 'ENDOFFILE'
[paste entire file contents here]
ENDOFFILE
```

Repeat for:
- `check-auth-status.py`
- `request-2fa-code.py`  
- `VM_2FA_SETUP.md`

### Step 3: Make Scripts Executable

```bash
chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py
```

### Step 4: Verify

```bash
ls -lh setup-vm-2fa.sh check-auth-status.py request-2fa-code.py
./setup-vm-2fa.sh  # Should show usage info
```

## Alternative: Copy File Contents Directly

**On your local machine**, get file contents:

```bash
# Display each file
cat setup-vm-2fa.sh
cat check-auth-status.py
cat request-2fa-code.py
cat VM_2FA_SETUP.md
```

**In Browser SSH**, for each file:

```bash
cat > filename << 'ENDOFFILE'
[paste the entire contents from your local machine]
ENDOFFILE
```

## What Files You Need

1. **setup-vm-2fa.sh** - Interactive setup wizard
2. **check-auth-status.py** - Check authentication status
3. **request-2fa-code.py** - Request 2FA codes
4. **VM_2FA_SETUP.md** - Documentation (optional but helpful)

## After Transferring

Once files are on the VM, you can:

```bash
# Check authentication status
python3 check-auth-status.py

# Run the setup wizard
bash setup-vm-2fa.sh

# Request a code
python3 request-2fa-code.py
```

## Need the File Contents?

If you need me to display the file contents for copying, let me know which files and I can show them.

