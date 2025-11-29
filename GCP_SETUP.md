# Google Cloud Platform Setup Guide

This guide walks you through setting up a GCP VM instance to run the Google Photos to iCloud migration tool.

## Prerequisites

- Google Cloud Platform account
- Billing enabled on your GCP project
- Basic familiarity with GCP Console

## Step 1: Create a GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "photos-migration")
5. Click "Create"

## Step 2: Enable Required APIs

1. In the GCP Console, go to "APIs & Services" > "Library"
2. Search for and enable:
   - **Google Drive API**
   - **Compute Engine API**

## Step 3: Create Service Account for Google Drive API

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace account)
   - Fill in required fields
   - Add your email as a test user
4. For application type, choose "Desktop app"
5. Name it (e.g., "Photos Migration")
6. Click "Create"
7. Download the JSON file and save it as `credentials.json`

## Step 4: Create VM Instance

1. Go to "Compute Engine" > "VM instances"
2. Click "Create Instance"
3. Configure the instance:
   - **Name**: `photos-migration-vm`
   - **Region**: Choose closest to you (or Google Drive data location)
   - **Machine type**: 
     - For small libraries (<100GB): `e2-standard-2` (2 vCPU, 8GB RAM)
     - For medium libraries (100-500GB): `e2-standard-4` (4 vCPU, 16GB RAM)
     - For large libraries (>500GB): `e2-standard-8` (8 vCPU, 32GB RAM)
   - **Boot disk**: 
     - Click "Change"
     - Choose "Ubuntu 22.04 LTS" or "Debian 11"
     - Increase disk size based on your needs:
       - Minimum: 100GB (for processing in batches)
       - Recommended: 200-500GB (to hold all extracted files)
     - Click "Select"
   - **Firewall**: Allow HTTP and HTTPS traffic (optional, for OAuth flow)
4. Click "Create"

## Step 5: Connect to VM

1. Wait for the VM to start (green checkmark)
2. Click "SSH" button next to your VM instance
3. This opens a browser-based SSH session

## Step 6: Upload Files to VM

### Option A: Using gcloud CLI (from your local machine)

1. Install [gcloud CLI](https://cloud.google.com/sdk/docs/install) if not already installed
2. Authenticate: `gcloud auth login`
3. Set project: `gcloud config set project YOUR_PROJECT_ID`
4. Upload files:
```bash
gcloud compute scp credentials.json photos-migration-vm:~/
gcloud compute scp config.yaml photos-migration-vm:~/
gcloud compute scp *.py photos-migration-vm:~/
gcloud compute scp requirements.txt photos-migration-vm:~/
gcloud compute scp setup.sh photos-migration-vm:~/
```

### Option B: Using Cloud Console (browser-based)

1. In the VM instance page, click "Edit"
2. Scroll to "Startup script" section
3. Paste the setup commands (see below)
4. Or use the browser-based file upload in SSH session

### Option C: Git Clone (if you have the code in a repo)

```bash
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration
```

## Verifying Files on the VM

After uploading files, verify they're on the VM:

### Via SSH (Browser Terminal):
```bash
# List files in home directory
ls -la

# Check project directory
ls -la ~/google-photos-to-icloud-migration/
# or if cloned to Sites:
ls -la ~/Sites/google-photos-to-icloud-migration/

# Verify specific files exist
ls -la credentials.json config.yaml *.py

# Check file contents
cat config.yaml
head -20 main.py
```

### Via gcloud CLI (from local machine):
```bash
# List files on VM
gcloud compute ssh photos-migration-vm --zone=YOUR_ZONE --command="ls -la"

# Check specific directory
gcloud compute ssh photos-migration-vm --zone=YOUR_ZONE --command="ls -la ~/google-photos-to-icloud-migration/"

# Download a file to verify (optional)
gcloud compute scp photos-migration-vm:~/config.yaml ./downloaded-config.yaml --zone=YOUR_ZONE
```

### Check Upload Logs:
```bash
# Via SSH, check if files were uploaded successfully
gcloud compute ssh photos-migration-vm --zone=YOUR_ZONE --command="df -h"
```

## Step 7: Install Dependencies

In the VM SSH session:

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh

# Or install manually:
sudo apt-get update
sudo apt-get install -y python3 python3-pip unzip libimage-exiftool-perl
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

## Step 8: Configure the Tool

1. Copy the example config:
```bash
cp config.yaml.example config.yaml
```

2. Edit config.yaml:
```bash
nano config.yaml
```

Update:
- `google_drive.credentials_file`: Path to credentials.json (usually `./credentials.json`)
- `icloud.apple_id`: Your Apple ID email
- `icloud.password`: Leave empty to be prompted, or enter password
- `processing.base_dir`: Use `/tmp/google-photos-migration` or a persistent disk path

## Step 9: Run the Migration

```bash
python3 main.py --config config.yaml
```

For the first run, you'll need to:
1. Authenticate with Google Drive (browser will open)
2. Authenticate with iCloud (if 2FA, enter code)

## Step 10: Monitor Progress

- Check logs: `tail -f migration.log`
- Monitor disk usage: `df -h`
- Check running processes: `ps aux | grep python`

## Cost Optimization Tips

1. **Use Preemptible Instances**: Save up to 80% on compute costs
   - Create preemptible VM: Add `--preemptible` flag when creating
   - Note: VM may be terminated, but you can resume from checkpoints

2. **Process in Batches**: 
   - Adjust `batch_size` in config.yaml
   - Delete extracted files after processing each batch
   - Set `cleanup_after_upload: true`

3. **Use Appropriate Instance Size**:
   - Start with smaller instance, scale up if needed
   - Monitor CPU and memory usage

4. **Stop VM When Not in Use**:
   - Stop the VM when migration is complete
   - You only pay for storage when VM is stopped

## Estimated Costs

- **Compute**: 
  - e2-standard-2: ~$0.067/hour (~$50/month if running continuously)
  - e2-standard-4: ~$0.134/hour (~$100/month)
- **Storage**: 
  - 200GB disk: ~$20/month
  - 500GB disk: ~$50/month
- **Network**: Minimal (mostly egress to iCloud)

**Total estimate for a 200GB library**: ~$70-150 depending on processing time

## Troubleshooting

### OAuth Authentication Issues

If browser-based OAuth doesn't work:
1. Use `gcloud auth application-default login` for service account
2. Or download credentials and use service account key

### Disk Space Issues

If running out of disk space:
1. Process in smaller batches
2. Enable cleanup after processing
3. Use Cloud Storage as intermediate storage
4. Increase disk size (can be done without recreating VM)

### Network Issues

If uploads are slow:
1. Choose VM region closer to iCloud servers
2. Use larger instance for better network performance
3. Consider using Cloud Storage + transfer service

### Authentication Timeout

If iCloud authentication times out:
1. Use trusted device ID in config.yaml
2. Run interactively and enter 2FA code when prompted
3. Consider using Photos library sync method (`--use-sync`) if on macOS

## Restarting the VM

To restart your VM instance (useful for running startup scripts):

### Via Google Cloud Console:
1. Go to Compute Engine > VM instances
2. Find your VM instance
3. Click the three dots (⋮) menu
4. Select "Reset" (hard restart) or "Restart" (soft restart)
5. Confirm the restart

### Via gcloud CLI:
```bash
# Restart the VM (replace with your instance name and zone)
gcloud compute instances reset photos-migration-vm --zone=YOUR_ZONE

# Find your zone:
gcloud compute instances list
```

### Via SSH (from inside the VM):
```bash
sudo reboot
```

**Note:** If you've added a startup script, make sure it's configured in the VM settings before restarting. The startup script runs automatically when the VM boots.

## Cleanup

After migration is complete:

1. Stop the VM to save costs
2. Delete the VM if no longer needed
3. Delete any temporary storage
4. Revoke OAuth credentials if not needed

## Next Steps

- Review the main README.md for usage instructions
- Check migration.log for detailed progress
- Verify files in iCloud Photos
- Recreate albums manually if needed

