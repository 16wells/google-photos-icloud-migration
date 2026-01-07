# Complete Installation Guide for New MacBook

This guide will walk you through setting up the Google Photos to iCloud Photos migration tool on a **brand new MacBook** with no developer tools, Python, or other prerequisites installed.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites Checklist](#prerequisites-checklist)
3. [Step 1: Install Xcode Command Line Tools](#step-1-install-xcode-command-line-tools)
4. [Step 2: Install Homebrew](#step-2-install-homebrew)
5. [Step 3: Install Python and Required Tools](#step-3-install-python-and-required-tools)
6. [Step 4: Download the Migration Tool](#step-4-download-the-migration-tool)
7. [Step 5: Set Up Python Virtual Environment](#step-5-set-up-python-virtual-environment)
8. [Step 6: Install Python Dependencies](#step-6-install-python-dependencies)
9. [Step 7: Set Up Google Drive API Credentials](#step-7-set-up-google-drive-api-credentials)
10. [Step 8: Configure the Tool](#step-8-configure-the-tool)
11. [Step 9: Verify Installation](#step-9-verify-installation)
12. [Step 10: Run Your First Migration](#step-10-run-your-first-migration)
13. [Troubleshooting](#troubleshooting)

---

## Overview

This tool migrates photos and videos from Google Photos (exported via Google Takeout) to iCloud Photos, preserving all metadata and album structures. It runs on macOS and uses Apple's PhotoKit framework to save photos directly to your Photos library, which then syncs to iCloud Photos automatically.

**Estimated Setup Time:** 30-45 minutes (depending on download speeds)

> **Already have Python and ExifTool installed?** See [QUICKSTART.md](QUICKSTART.md) for a faster 5-minute setup guide instead of this complete installation guide.

---

## Prerequisites Checklist

Before starting, make sure you have:

- ✅ A MacBook running macOS 10.15 (Catalina) or later
- ✅ Administrator access to your MacBook
- ✅ Internet connection
- ✅ Your Google account credentials
- ✅ Your Apple ID credentials
- ✅ Google Takeout zip files uploaded to Google Drive (or access to download them)
- ✅ At least 2x the size of your Google Photos data in free disk space

---

## Step 1: Install Xcode Command Line Tools

The Command Line Tools provide essential development tools needed for Python packages.

### 1.1 Open Terminal

1. Press `Command + Space` to open Spotlight
2. Type "Terminal" and press Enter
3. Terminal will open with a command prompt

### 1.2 Install Command Line Tools

In Terminal, type the following command and press Enter:

```bash
xcode-select --install
```

### 1.3 Complete the Installation

1. A popup window will appear asking to install Command Line Tools
2. Click **"Install"**
3. Wait for the installation to complete (5-10 minutes)
4. You may be asked to agree to the license - click **"Agree"**

### 1.4 Verify Installation

After installation completes, verify it worked:

```bash
xcode-select -p
```

You should see a path like `/Library/Developer/CommandLineTools`. If you see an error, try the installation again.

**Troubleshooting:**
- If you see "command line tools are already installed" - you're all set!
- If installation fails, check your internet connection and try again
- If you get a "not currently available" error, wait a few minutes and try again

---

## Step 2: Install Homebrew

Homebrew is a package manager for macOS that makes it easy to install software.

### 2.1 Install Homebrew

Copy and paste this entire command into Terminal and press Enter:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2.2 Follow the Prompts

1. You'll be asked for your MacBook password (the one you use to log in)
2. Type your password and press Enter (you won't see characters as you type - this is normal)
3. Press Enter again when prompted
4. Wait for installation to complete (5-10 minutes)

### 2.3 Add Homebrew to Your Path

After installation, you'll see a message like:

```
Next steps:
- Run these two commands in your terminal to add Homebrew to your PATH:
```

Follow the instructions shown. Typically, you'll need to run:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

**Note:** If you have an Intel Mac (not Apple Silicon), the path might be `/usr/local/bin/brew` instead of `/opt/homebrew/bin/brew`.

### 2.4 Verify Homebrew Installation

Verify Homebrew is working:

```bash
brew --version
```

You should see a version number. If you get a "command not found" error, make sure you completed step 2.3.

---

## Step 3: Install Python and Required Tools

Now we'll install Python 3 and ExifTool (needed for metadata processing).

### 3.1 Install Python 3

```bash
brew install python@3.11
```

This will install Python 3.11 (or the latest stable version). Wait for installation to complete.

### 3.2 Install ExifTool

ExifTool is used to merge metadata into photos:

```bash
brew install exiftool
```

### 3.3 Verify Installations

Check that everything is installed correctly:

```bash
python3 --version
exiftool -ver
```

You should see version numbers for both.

---

## Step 4: Download the Migration Tool

You can download the tool in one of two ways:

### Option A: Download as ZIP (Easier for beginners)

1. Go to the GitHub repository page
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. The ZIP file will download to your Downloads folder
5. Double-click the ZIP file to extract it
6. Move the extracted folder to a convenient location (e.g., `~/Documents/google-photos-icloud-migration`)

### Option B: Clone with Git (If you're comfortable with Git)

```bash
cd ~/Documents
git clone https://github.com/your-username/google-photos-icloud-migration.git
cd google-photos-icloud-migration
```

**Note:** Replace `your-username` with the actual GitHub username or repository URL.

### 4.1 Navigate to the Tool Directory

Open Terminal and navigate to where you extracted/downloaded the tool:

```bash
cd ~/Documents/google-photos-icloud-migration
```

(Adjust the path if you put it in a different location)

---

## Step 5: Set Up Python Virtual Environment

A virtual environment keeps the tool's dependencies separate from other Python projects.

### 5.1 Create Virtual Environment

```bash
python3 -m venv venv
```

This creates a folder called `venv` in your project directory.

### 5.2 Activate Virtual Environment

```bash
source venv/bin/activate
```

After activation, you should see `(venv)` at the beginning of your Terminal prompt, like:

```
(venv) your-username@your-macbook google-photos-icloud-migration %
```

**Important:** You need to activate the virtual environment every time you open a new Terminal window to work with this tool. You can tell it's activated when you see `(venv)` in your prompt.

---

## Step 6: Install Python Dependencies

Now we'll install all the Python packages the tool needs.

### 6.1 Upgrade pip (Python package installer)

```bash
pip install --upgrade pip
```

### 6.2 Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages. Wait for installation to complete (5-10 minutes depending on your internet speed).

**What gets installed:**
- `google-api-python-client` - For accessing Google Drive
- `pyicloud` - For iCloud API access (optional, for API method)
- `pyobjc-framework-Photos` - For PhotoKit framework (required for `--use-sync` method)
- `Pillow` - For image processing
- `pyyaml` - For configuration files
- `tqdm` - For progress bars
- And other dependencies

### 6.3 Verify Installation

Check that key packages are installed:

```bash
python3 -c "import googleapiclient; import pyicloud; import Photos; print('All packages installed successfully!')"
```

If you see "All packages installed successfully!" you're good to go. If you see errors, make sure you activated the virtual environment (step 5.2).

---

## Step 7: Set Up Authentication

The tool needs to authenticate with Google Drive to access your Takeout zip files.

### Option A: Use the Authentication Setup Wizard (Recommended)

The easiest way is to use the built-in authentication wizard:

```bash
python3 auth_setup.py
```

This wizard will:
- Guide you through Google Drive OAuth setup step-by-step
- Open browser windows automatically for signing in
- Handle all the authentication flows for you
- Create your `config.yaml` file automatically
- No manual file management needed!

**Skip to Step 9** if you use the wizard.

### Option B: Manual Setup

If you prefer to set up manually, follow the steps below.

## Step 7 (Manual): Set Up Google Drive API Credentials

The tool needs credentials to access your Google Drive where the Takeout zip files are stored.

### 7.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click the project dropdown at the top
4. Click **"New Project"**
5. Enter a project name (e.g., "Photos Migration")
6. Click **"Create"**
7. Wait for the project to be created, then select it from the dropdown

### 7.2 Enable Google Drive API

1. In the Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for "Google Drive API"
3. Click on "Google Drive API"
4. Click **"Enable"**
5. Wait for it to enable

### 7.3 Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"**
3. Select **"OAuth client ID"**
4. If prompted, configure the OAuth consent screen:
   - User Type: **"External"** (unless you have a Google Workspace account)
   - Click **"Create"**
   - App name: "Photos Migration Tool"
   - User support email: Your email
   - Developer contact: Your email
   - Click **"Save and Continue"**
   - Scopes: Click **"Save and Continue"** (no need to add scopes)
   - Test users: Add your Google account email, click **"Save and Continue"**
   - Click **"Back to Dashboard"**

5. Back at Credentials, click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
6. Application type: **"Desktop app"**
7. Name: "Photos Migration Desktop Client"
8. Click **"Create"**
9. A popup will show your Client ID and Client Secret - **download the JSON file** by clicking the download button
10. Save the downloaded file as `credentials.json` in the migration tool directory

### 7.4 Move Credentials File

Move the downloaded `credentials.json` file to your migration tool directory:

```bash
# If the file is in Downloads
mv ~/Downloads/credentials.json ~/Documents/google-photos-icloud-migration/
```

Or use Finder to drag and drop the file into the migration tool folder.

---

## Step 8: Configure the Tool

**Note:** If you used the Authentication Setup Wizard (Option A in Step 7), your `config.yaml` file has already been created! You can skip to Step 9.

Otherwise, manually create and configure the `config.yaml` file:

### 8.1 Create Configuration File

```bash
cp config.yaml.example config.yaml
```

### 8.2 Edit Configuration File

Open `config.yaml` in a text editor. You can use:

- **TextEdit** (built into macOS): `open -a TextEdit config.yaml`
- **VS Code** (if installed): `code config.yaml`
- **Nano** (Terminal editor): `nano config.yaml`

### 8.3 Configure Settings

Edit the following sections in `config.yaml`:

#### Google Drive Configuration

```yaml
google_drive:
  credentials_file: "credentials.json"  # Should already be correct
  folder_id: ""  # Leave empty to search all of Drive, or enter a specific folder ID
  zip_file_pattern: "takeout-*.zip"  # Pattern to match your Takeout files
```

**To find a folder ID:**
1. Open Google Drive in a web browser
2. Navigate to the folder containing your Takeout zip files
3. Look at the URL - it will contain something like `folders/ABC123xyz`
4. Copy the part after `folders/` (e.g., `ABC123xyz`) and paste it as `folder_id`

#### iCloud Configuration

```yaml
icloud:
  apple_id: "your-apple-id@example.com"  # Your Apple ID email
  password: ""  # Leave empty - you'll be prompted when running
  # For PhotoKit method (--use-sync), password is not needed
```

**Note:** For the PhotoKit sync method (`--use-sync`), you don't need to provide your Apple ID password in the config. The tool uses your macOS iCloud account automatically.

#### Processing Configuration

```yaml
processing:
  base_dir: "/tmp/google-photos-migration"  # Where temporary files are stored
  # You can change this to a location with more space if needed
  batch_size: 100  # Number of files to process at once
  cleanup_after_upload: true  # Delete extracted files after upload
```

**Important:** Make sure `base_dir` has enough free space (at least 2x your Google Photos data size). You can change it to:

```yaml
base_dir: "~/Documents/photos-migration-temp"
```

#### Metadata Configuration

```yaml
metadata:
  preserve_dates: true  # Keep original photo dates
  preserve_gps: true  # Keep location data
  preserve_descriptions: true  # Keep captions/descriptions
  preserve_albums: true  # Organize into albums
```

These should all be `true` to preserve everything from Google Photos.

### 8.4 Optional: Set Up .env File for Sensitive Credentials

For better security, you can store sensitive credentials (like passwords or API tokens) in a `.env` file instead of `config.yaml`. The `.env` file is automatically ignored by git.

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your credentials (optional)
# This is recommended for passwords and API tokens
```

The `.env` file supports:
- `ICLOUD_APPLE_ID` - Your Apple ID email
- `ICLOUD_PASSWORD` - Your Apple ID password (for API method only)
- `ICLOUD_2FA_CODE` - 2FA verification code
- `ICLOUD_2FA_DEVICE_ID` - Trusted device ID
- `GOOGLE_DRIVE_CREDENTIALS_FILE` - Path to credentials.json
- `GITHUB_TOKEN` - GitHub personal access token (for repository management scripts)

**Note:** Environment variables in `.env` take precedence over `config.yaml` values. This is optional - you can also leave passwords empty in `config.yaml` and be prompted when running.

### 8.5 Save the Configuration

Save the files and close the editor.

---

## Step 9: Verify Installation

Let's make sure everything is set up correctly.

### 9.1 Check Python and Dependencies

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Check Python version (should be 3.11+)
python3 --version

# Check that packages are installed
python3 -c "import googleapiclient; import Photos; print('✓ All packages installed')"
```

### 9.2 Check ExifTool

```bash
exiftool -ver
```

Should show a version number.

### 9.3 Check Configuration File

```bash
python3 -c "import yaml; config = yaml.safe_load(open('config.yaml')); print('✓ Config file is valid')"
```

### 9.4 Check Credentials File

```bash
ls -la credentials.json
```

Should show the file exists.

---

## Step 10: Run Your First Migration

Now you're ready to run the migration!

### 10.1 Make Sure Virtual Environment is Activated

```bash
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### 10.2 Enable iCloud Photos (Recommended)

For the PhotoKit sync method (`--use-sync`), you should enable iCloud Photos:

1. **System Settings** → **Apple ID** → **iCloud**
2. Enable **"Photos"** (or **"iCloud Photos"**)
3. Choose **"Download Originals"** or **"Optimize Storage"** based on your needs

**Note:** The PhotoKit method uses your macOS iCloud account automatically - no password needed in config!

### 10.3 Grant Photo Library Permission

Before running, you'll need to grant permission to access your Photos library:

1. The first time you run the tool, macOS will prompt you for permission
2. Go to **System Settings** → **Privacy & Security** → **Photos**
3. Find "Terminal" or "Python" in the list
4. Check the box to allow access
5. Choose **"Add Photos Only"** or **"Read and Write"** (Add Photos Only is sufficient)

### 10.4 Run the Migration

Run the migration using the command line:

**Option A: Process local zip files (if you already have Google Takeout zips):**

```bash
python3 process_local_zips.py --use-sync --takeout-dir "/path/to/your/zips"
```

**Option B: Download from Google Drive and process:**

```bash
python3 main.py --config config.yaml --use-sync
```

Both methods use the recommended PhotoKit method (preserves metadata, supports albums).

**Why PhotoKit Method?**
- ✅ **Native Photos App Integration**: Uses macOS Photos app with built-in iCloud Photos sync
- ✅ **Full Album Support**: Complete album organization via PhotoKit framework
- ✅ **No API Limitations**: Uses Apple's native PhotoKit instead of reverse-engineered APIs
- ✅ **Automatic Sync**: Photos automatically sync to iCloud Photos once saved
- ✅ **Metadata Preservation**: Preserves all EXIF metadata (GPS, dates, camera info)
- ✅ **Better Reliability**: Uses Apple's official PhotoKit framework
- ✅ **No Authentication Needed**: Uses your macOS iCloud account automatically

### 10.5 First Run - Google Drive Authentication

On the first run, the tool will:

1. Open a web browser
2. Ask you to sign in to your Google account
3. Ask for permission to access Google Drive
4. Click **"Allow"**
5. You'll see a message saying "The authentication flow has completed"
6. Return to Terminal - the tool will continue

### 10.6 Monitor Progress

The tool will:

1. **List zip files** from Google Drive
2. **Download** each zip file
3. **Extract** the zip file
4. **Process metadata** (merge JSON into photos)
5. **Parse albums** from directory structure
6. **Save to Photos library** using PhotoKit
7. **Sync to iCloud Photos** automatically (if enabled)

After each zip file, you'll be prompted:
- **(C) Continue** - Process next zip
- **(A) Continue All** - Process all remaining without prompts
- **(S) Stop** - Stop and exit

### 10.7 Check Results

1. Open the **Photos** app on your Mac
2. You should see photos being imported
3. Check **iCloud Photos** on another device to see them syncing
4. Verify albums are created correctly

---

## Optional: Prepare Today, Run Tomorrow Workflow

If you want to prepare the MacBook today but run the migration tomorrow (e.g., after validating the iCloud account):

### Today: Setup Steps

1. **Complete Steps 1-9** from this guide (install tools, set up credentials, verify installation)
2. **Copy configuration files** (`credentials.json` and `config.yaml`) to the MacBook
3. **Run verification** to ensure everything is ready:
   ```bash
   python3 verify-setup.py
   ```
   All checks should pass ✓

### Tomorrow: Final Steps

Once you've validated the iCloud account:

1. **Sign into iCloud**:
   - System Settings → Apple ID
   - Sign in with your Apple ID
   - Enable iCloud Photos: System Settings → Apple ID → iCloud → Photos → ON

2. **Grant Permissions** (when prompted):
   - System Settings → Privacy & Security → Photos → Allow Terminal/Python
   - System Settings → Privacy & Security → Files and Folders → Allow access

3. **Run the migration**:
   ```bash
   source venv/bin/activate
   python3 main.py --config config.yaml --use-sync
   ```

## Optional: Using a Separate User Account

For isolation and to prevent conflicts, you can create a separate macOS user account for the migration:

1. **System Settings** → **Users & Groups**
2. Click **"+"** to add new user
3. Create account with:
   - Full Name: (your choice, e.g., "Photos Migration")
   - Account Name: (your choice, e.g., "photos-migration")
   - Password: (secure password)
   - Allow user to administer this computer: ✅ (for script permissions)
4. **Log in as the new user**
5. **Sign into iCloud** with the target account
6. **Follow this installation guide** from the new user account
7. **After migration completes**, you can delete the temporary user account (optional)

## Troubleshooting

### "Command not found" Errors

- Make sure you activated the virtual environment: `source venv/bin/activate`
- Check that you're in the correct directory: `pwd` should show the migration tool folder
- Verify installations: `python3 --version`, `brew --version`

### "Permission denied" Errors

- Make sure you granted Photos library permission in System Settings
- Try running with `sudo` (not recommended, but can help diagnose)
- Check file permissions: `ls -la` in the tool directory

### "Module not found" Errors

- Reinstall dependencies: `pip install -r requirements.txt`
- Make sure virtual environment is activated
- Try: `pip install --upgrade pip` then reinstall

### Google Drive Authentication Issues

- Make sure `credentials.json` is in the tool directory
- Verify the file is valid JSON: `python3 -c "import json; json.load(open('credentials.json'))"`
- Re-download credentials from Google Cloud Console if needed
- Run `python3 verify-oauth-setup.py` to diagnose OAuth issues

### PhotoKit Permission Issues

- Go to **System Settings** → **Privacy & Security** → **Photos**
- Ensure Terminal/Python has permission
- Restart Terminal and try again

### Photos App Not Responding

If Photos app becomes unresponsive during import:
1. Wait - large imports can take time
2. Check Activity Monitor for Photos process
3. If truly stuck, force quit and restart Photos app
4. Re-run script with `--retry-failed` to retry failed uploads

### Album Creation Issues

The PhotoKit sync method:
- ✅ Creates albums in Photos app if they don't exist
- ✅ Reuses existing albums (case-insensitive matching)
- ✅ Organizes photos into correct albums
- ✅ Preserves album structure from Google Photos

If albums aren't being created:
- Check Photos app permissions (System Settings → Privacy & Security → Photos)
- Verify you're using `--use-sync` flag
- Check logs for album-related errors

### Out of Disk Space

- Check available space: `df -h`
- Change `base_dir` in `config.yaml` to a location with more space
- Enable `cleanup_after_upload: true` to delete files after processing

### Photos Not Syncing to iCloud

- Check **System Settings** → **Apple ID** → **iCloud** → **Photos** is enabled
- Ensure you're signed into the correct Apple ID
- Wait - initial sync can take hours for large libraries
- Check iCloud storage space

### Need More Help?

1. Check the main [README.md](README.md) for more details
2. See [README.md](README.md) for detailed documentation
3. Review logs in `migration.log` file
4. Check the [Troubleshooting section](README.md#troubleshooting) in README

---

## Next Steps

After your first successful migration:

1. **Verify photos** in Photos app and iCloud Photos
2. **Check albums** are organized correctly
3. **Review metadata** - dates, locations, descriptions should be preserved
4. **Clean up** - delete temporary files if migration completed successfully
5. **Keep the tool** - you can use it again if you get more Google Takeout files

---

## Quick Reference Commands

```bash
# Activate virtual environment (do this every time you open Terminal)
source venv/bin/activate

# Run migration with Command Line (PhotoKit method - recommended)
python3 main.py --config config.yaml --use-sync

# Retry failed uploads
python3 main.py --config config.yaml --retry-failed --use-sync

# Check what's installed
python3 --version
brew --version
exiftool -ver
```

---

## Summary

You've successfully:

✅ Installed Xcode Command Line Tools  
✅ Installed Homebrew  
✅ Installed Python 3 and ExifTool  
✅ Downloaded the migration tool  
✅ Set up Python virtual environment  
✅ Installed all dependencies  
✅ Configured Google Drive API credentials  
✅ Created and configured `config.yaml`  
✅ Run your first migration  

The tool is now ready to migrate your Google Photos to iCloud Photos with full metadata and album preservation!

