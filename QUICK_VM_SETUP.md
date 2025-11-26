# Quick VM Setup - 2FA Helpers

## Fastest Method: Copy Generated Commands

**On your local machine**, run:

```bash
./generate-vm-transfer-commands.sh > vm-transfer.txt
```

This creates `vm-transfer.txt` with all the commands ready to paste.

**Then in Browser SSH:**

1. Open Browser SSH in GCP Console
2. Open `vm-transfer.txt` in a text editor
3. Copy and paste the commands section by section

## Or Use Individual Transfer Script

**On your local machine:**

```bash
./transfer-2fa-helpers-to-vm.sh photos-migration-vm us-central1-c
```

If that doesn't work, it will show you alternative methods.

## Manual Method (Most Reliable)

### Step 1: Get File Contents

**On your local machine**, display each file:

```bash
cat setup-vm-2fa.sh
cat check-auth-status.py  
cat request-2fa-code.py
cat VM_2FA_SETUP.md
```

### Step 2: Transfer via Browser SSH

**In Browser SSH**, for each file:

```bash
cat > setup-vm-2fa.sh << 'ENDOFFILE'
[paste the entire file contents here]
ENDOFFILE
```

Repeat for each file.

### Step 3: Make Executable

```bash
chmod +x setup-vm-2fa.sh check-auth-status.py request-2fa-code.py
```

### Step 4: Test

```bash
./setup-vm-2fa.sh  # Should show usage
python3 check-auth-status.py  # Should check auth status
```

## What You'll Have After Transfer

- ✅ `setup-vm-2fa.sh` - Interactive setup wizard
- ✅ `check-auth-status.py` - Check authentication status  
- ✅ `request-2fa-code.py` - Request 2FA codes
- ✅ `VM_2FA_SETUP.md` - Documentation

## Next Steps

Once files are on the VM:

1. **Check current status:**
   ```bash
   python3 check-auth-status.py
   ```

2. **Run setup wizard:**
   ```bash
   bash setup-vm-2fa.sh
   ```

3. **Or request a code directly:**
   ```bash
   python3 request-2fa-code.py
   ```

## Troubleshooting

**Files not found?**
- Make sure you're in the right directory on the VM
- Check with: `ls -la`

**Permission denied?**
- Make scripts executable: `chmod +x *.sh *.py`

**Scripts don't work?**
- Check Python: `python3 --version`
- Check shebang lines: `head -1 setup-vm-2fa.sh`

