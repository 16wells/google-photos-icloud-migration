# Mac Terminal Setup - Ensuring Correct Home Directory

## Your Current Setup ✅

**Mac User:** `skipshean`  
**Mac Home Directory:** `/Users/skipshean`  
**VM User:** `skipshean`  
**VM Home Directory:** `/home/skipshean`

Everything is correctly configured! Your Mac and VM both use the same username, which makes transfers easier.

## Understanding the Difference

- **Mac (Local):** Files are in `/Users/skipshean/Sites/google-photos-icloud-migration/`
- **VM (Remote):** Files should be in `/home/skipshean/`

When you use `gcloud compute scp`, files automatically go to the **VM's** home directory (`/home/skipshean/`).

## Verifying Your Mac Terminal Uses the Right Home

### Check Current Settings

```bash
# Should show: skipshean
whoami

# Should show: /Users/skipshean
echo $HOME

# Should show: /Users/skipshean
pwd
```

### If Home Directory Seems Wrong

1. **Check your shell configuration:**
   ```bash
   # Check which shell you're using
   echo $SHELL
   
   # For bash
   cat ~/.bash_profile
   cat ~/.bashrc
   
   # For zsh (default on newer macOS)
   cat ~/.zshrc
   ```

2. **Make sure HOME is set correctly:**
   ```bash
   # This should show /Users/skipshean
   echo $HOME
   
   # If it's wrong, add to ~/.zshrc or ~/.bash_profile:
   export HOME=/Users/skipshean
   ```

3. **Restart your terminal** after making changes.

## Ensuring VM Transfers Go to the Right Place

### Method 1: Explicit Path (Recommended)

When transferring files, explicitly specify the user and path:

```bash
# Files will go to /home/skipshean/ on the VM
gcloud compute scp file.py photos-migration-vm:~/ --zone=us-central1-c

# Or explicitly specify the path
gcloud compute scp file.py photos-migration-vm:/home/skipshean/ --zone=us-central1-c
```

### Method 2: Verify After Transfer

After transferring, verify files are in the right place:

```bash
gcloud compute ssh photos-migration-vm --zone=us-central1-c \
  --command="cd /home/skipshean && ls -lh file.py && pwd"
```

### Method 3: Create a Helper Script

Use the helper script that ensures correct paths:

```bash
./transfer-2fa-helpers-to-vm.sh photos-migration-vm us-central1-c
```

Or update `sync-to-vm.sh`:

```bash
./sync-to-vm.sh photos-migration-vm
```

## Quick Reference

| Location | Path | Purpose |
|----------|------|---------|
| **Mac Local** | `/Users/skipshean/Sites/google-photos-icloud-migration/` | Your project files |
| **VM Remote** | `/home/skipshean/` | Files on the VM |
| **gcloud transfer** | `photos-migration-vm:~/` | Goes to `/home/skipshean/` on VM |

## Troubleshooting

### Problem: Files end up in wrong directory on VM

**Solution:** Always specify the full path:
```bash
gcloud compute scp file.py photos-migration-vm:/home/skipshean/file.py --zone=us-central1-c
```

### Problem: Permission denied errors

**Solution:** Make sure you're transferring to your own home directory:
```bash
# Check VM user
gcloud compute ssh photos-migration-vm --zone=us-central1-c --command="whoami"

# Should show: skipshean
```

### Problem: Can't find files after transfer

**Solution:** Verify location:
```bash
gcloud compute ssh photos-migration-vm --zone=us-central1-c \
  --command="ls -la /home/skipshean/ | grep filename"
```

## Creating Terminal Aliases (Optional)

Add these to `~/.zshrc` or `~/.bash_profile` for convenience:

```bash
# VM transfer alias
alias vm-transfer='gcloud compute scp'

# VM SSH alias  
alias vm-ssh='gcloud compute ssh photos-migration-vm --zone=us-central1-c'

# VM home directory
alias vm-home='gcloud compute ssh photos-migration-vm --zone=us-central1-c --command="cd /home/skipshean && bash"'
```

Then reload:
```bash
source ~/.zshrc  # or ~/.bash_profile
```

## Summary

✅ Your Mac is correctly configured  
✅ Your VM is correctly configured  
✅ Both use the same username (`skipshean`)  
✅ Files transfer to the right place automatically

No changes needed! Just be aware of the difference between:
- **Local Mac path:** `/Users/skipshean/...`
- **Remote VM path:** `/home/skipshean/...`

