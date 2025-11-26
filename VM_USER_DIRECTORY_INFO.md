# VM User Directory Information

## Current Setup

**Active User:** `skipshean`  
**Home Directory:** `/home/skipshean`  
**Working Directory:** All migration files should be in `/home/skipshean`

## User Accounts on VM

The VM has multiple user accounts with home directories:

1. **`ubuntu`** → `/home/ubuntu` (default GCP user)
2. **`skip`** → `/home/skip` (different user account)
3. **`skipshean`** → `/home/skipshean` ← **CURRENT USER** (use this one)

## Important Notes

- **Always use `/home/skipshean`** when transferring files
- The `skip` account may have permission restrictions
- When using `gcloud compute scp`, files go to the current user's home by default
- When using `gcloud compute ssh`, you connect as the current user

## Current File Locations

All migration files are in:
```
/home/skipshean/
```

Helper scripts are in:
```
/home/skipshean/setup-vm-2fa.sh
/home/skipshean/check-auth-status.py
/home/skipshean/request-2fa-code.py
/home/skipshean/VM_2FA_SETUP.md
```

## To Verify Current User

```bash
whoami                    # Should show: skipshean
echo $HOME               # Should show: /home/skipshean
pwd                      # Should show: /home/skipshean
```

## Transferring Files

When transferring files, they automatically go to `/home/skipshean/`:

```bash
# From local machine
gcloud compute scp file.py photos-migration-vm:~/ --zone=us-central1-c

# Files will be in /home/skipshean/file.py on the VM
```

## If You Need to Access Files in /home/skip

If files somehow end up in `/home/skip`, you may need sudo or to switch users. However, it's better to keep everything in `/home/skipshean` to avoid permission issues.

