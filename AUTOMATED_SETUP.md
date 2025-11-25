# Automated VM Setup Guide

This guide provides automated scripts to help set up and verify your GCP VM.

## Prerequisites

1. **Install gcloud CLI** (if not already installed):
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate**:
   ```bash
   gcloud auth login
   ```

3. **Set your project**:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

## Quick Setup

### Step 1: Upload All Files to VM

Run this script from your local machine (in the project directory):

```bash
cd ~/Sites/google-photos-to-icloud-migration
./upload-to-vm.sh
```

Or specify VM name and zone:
```bash
./upload-to-vm.sh photos-migration-vm us-central1-a
```

This script will:
- ✅ Check gcloud authentication
- ✅ Find your VM automatically
- ✅ Start VM if it's stopped
- ✅ Upload all project files
- ✅ Install Python dependencies
- ✅ Verify setup

### Step 2: Verify Setup

Check that everything uploaded correctly:

```bash
./verify-vm-setup.sh
```

Or with specific VM:
```bash
./verify-vm-setup.sh photos-migration-vm us-central1-a
```

This will show you:
- ✅ VM status
- ✅ Files that exist on VM
- ✅ Missing files
- ✅ Installed dependencies

### Step 3: Configure and Run

SSH into your VM:
```bash
gcloud compute ssh photos-migration-vm --zone=YOUR_ZONE
```

Then on the VM:
```bash
# Copy example config
cp config.yaml.example config.yaml

# Edit config (use nano or vi)
nano config.yaml

# Run the migration
python3 main.py --config config.yaml
```

## Troubleshooting

### Script says "VM not found"
- Check VM name: `gcloud compute instances list`
- Make sure you're in the correct project: `gcloud config get-value project`

### Upload fails
- Check VM is running: `gcloud compute instances describe VM_NAME --zone=ZONE`
- Start VM if stopped: `gcloud compute instances start VM_NAME --zone=ZONE`
- Check firewall rules allow SSH

### Files not appearing on VM
- Run verification script: `./verify-vm-setup.sh`
- Check different directories: `gcloud compute ssh VM_NAME --zone=ZONE --command="ls -la ~/"`

### Authentication issues
- Re-authenticate: `gcloud auth login`
- Check active account: `gcloud auth list`

## Manual Alternative

If scripts don't work, you can manually:

1. **Clone repo on VM** (easiest method):
   ```bash
   gcloud compute ssh photos-migration-vm --zone=YOUR_ZONE
   # Then on VM:
   git clone https://github.com/16wells/google-photos-icloud-migration.git
   cd google-photos-icloud-migration
   ```

2. **Upload credentials**:
   ```bash
   gcloud compute scp credentials.json photos-migration-vm:~/google-photos-icloud-migration/ --zone=YOUR_ZONE
   ```

3. **Run setup**:
   ```bash
   cd google-photos-icloud-migration
   ./setup.sh
   cp config.yaml.example config.yaml
   nano config.yaml
   ```

## What the Scripts Do

### upload-to-vm.sh
- Checks prerequisites (gcloud, auth, project)
- Finds your VM automatically
- Starts VM if needed
- Uploads all project files
- Installs dependencies
- Provides next steps

### verify-vm-setup.sh
- Checks VM status
- Lists files on VM
- Verifies required files exist
- Checks installed dependencies
- Provides diagnostic information

## Getting Help

If scripts fail, check:
1. Error messages - they usually tell you what's wrong
2. VM status - make sure it's running
3. Network - make sure you can reach GCP
4. Permissions - make sure you have access to the VM

Run verification to see detailed diagnostics:
```bash
./verify-vm-setup.sh
```

