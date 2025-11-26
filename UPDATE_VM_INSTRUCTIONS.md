# How to Update Files on the VM

## Quick Solution: Use GCP Console Browser SSH (Recommended)

The easiest way to update files on your VM is using the GCP Console's built-in SSH terminal, which doesn't require SSH key authentication.

### Steps:

1. **Open GCP Console**
   - Go to: https://console.cloud.google.com/compute/instances?project=photos-migration-2025
   - Or navigate to: Compute Engine → VM instances

2. **Open Browser SSH**
   - Find `photos-migration-vm` in the list
   - Click the **"SSH"** button (opens a browser terminal)

3. **Update the file**
   ```bash
   # Create/edit the file
   nano icloud_uploader.py
   ```
   
   Then copy and paste the entire contents of `icloud_uploader.py` from your local machine.

4. **Save and exit**
   - Press `Ctrl+X`, then `Y`, then `Enter` to save

5. **Verify the update**
   ```bash
   grep -n "No trusted devices found" icloud_uploader.py
   ```
   You should see line numbers if the file was updated correctly.

---

## Alternative: Fix SSH Authentication (If Needed)

If you want to fix SSH authentication for future use, here are some options:

### Option 1: Check if OS Login is Enabled

The VM might be using OS Login instead of metadata-based SSH keys:

```bash
gcloud compute instances describe photos-migration-vm \
  --zone=us-central1-c \
  --format="get(metadata.items[].key,metadata.items[].value)" | grep -i oslogin
```

If OS Login is enabled, you'll need to:
1. Add your Google account to OS Login: https://console.cloud.google.com/compute/oslogin
2. Or disable OS Login and use metadata SSH keys instead

### Option 2: Use IAP Tunneling

Try using Identity-Aware Proxy tunneling:

```bash
gcloud compute scp icloud_uploader.py photos-migration-vm:~/ \
  --zone=us-central1-c \
  --tunnel-through-iap
```

### Option 3: Generate and Add New SSH Key

```bash
# Generate a new SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/gcp_vm_key -N ""

# Add to VM metadata
gcloud compute instances add-metadata photos-migration-vm \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=<(echo "skipshean:$(cat ~/.ssh/gcp_vm_key.pub)")

# Try connecting with the new key
gcloud compute ssh photos-migration-vm \
  --zone=us-central1-c \
  --ssh-key-file=~/.ssh/gcp_vm_key
```

---

## What Was Fixed in icloud_uploader.py

The updated file includes:

1. **Validation for trusted devices list** - Checks if devices exist before accessing them
2. **Input validation loop** - Prompts again if invalid device number is entered  
3. **Better error messages** - Clear messages when no trusted devices are found

The key changes are in the `_authenticate()` method around lines 51-114.

---

## Quick Copy-Paste Method

If you're using Browser SSH, here's the fastest way:

1. Open Browser SSH (see steps above)
2. Run: `cat > icloud_uploader.py << 'ENDOFFILE'`
3. Paste the entire file contents
4. Type `ENDOFFILE` on a new line and press Enter

This creates the file with all the correct contents.

