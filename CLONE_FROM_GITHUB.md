# Cloning Repository from GitHub

## Quick Command

On the new MacBook, open Terminal and run:

```bash
cd ~
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration
```

That's it! The repository will be cloned to `~/google-photos-icloud-migration`.

## Full Setup Process

### Step 1: Clone the Repository

```bash
# Navigate to where you want the repo (home directory is recommended)
cd ~

# Clone the repository
git clone https://github.com/16wells/google-photos-icloud-migration.git

# Enter the repository directory
cd google-photos-icloud-migration
```

### Step 2: Run Setup Script

```bash
# Make setup script executable (if not already)
chmod +x setup-macbook.sh

# Run the setup script
./setup-macbook.sh
```

This will install:
- **Xcode Command Line Tools** (required for development tools)
- Homebrew (if needed)
- ExifTool
- Python 3 (if needed)
- All Python dependencies

**Note:** The Xcode Command Line Tools installation will show a popup window. Click "Install" and wait for it to complete (5-10 minutes). The script will pause and wait for you to press Enter once installation is complete.

### Step 3: Copy Configuration Files

The repository doesn't include `credentials.json` and `config.yaml` (they're in `.gitignore` for security).

**Copy these files from your current machine:**

**Option A: Using AirDrop**
1. On current Mac: Select `credentials.json` and `config.yaml`
2. Right-click → Share → AirDrop
3. Select the new MacBook
4. On new MacBook: Save files to `~/google-photos-icloud-migration/`

**Option B: Using USB Drive**
1. Copy files to USB drive
2. Plug USB into new MacBook
3. Copy files to `~/google-photos-icloud-migration/`

**Option C: Using scp (if both machines on same network)**
```bash
# From your current machine
scp credentials.json config.yaml user@new-macbook.local:~/google-photos-icloud-migration/
```

**Option D: Using iCloud Drive**
1. Copy files to iCloud Drive on current Mac
2. Download from iCloud Drive on new MacBook
3. Move to `~/google-photos-icloud-migration/`

### Step 4: Verify Setup

```bash
# Run verification script
python3 verify-setup.py
```

All checks should pass ✓

## Alternative: Clone to Different Location

If you prefer a different location:

```bash
# Clone to Documents folder
cd ~/Documents
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration

# Or clone to Sites folder (if it exists)
cd ~/Sites
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration
```

## Updating the Repository

If you make changes on your current machine and push to GitHub, you can update on the new MacBook:

```bash
cd ~/google-photos-icloud-migration
git pull
```

## Troubleshooting

### "command not found: git"
Git comes pre-installed on macOS. If missing:
```bash
# Install via Homebrew
brew install git
```

### Authentication Issues
If GitHub requires authentication:
- Use HTTPS with a Personal Access Token, or
- Set up SSH keys (see GitHub docs)

### "Repository not found"
- Make sure the repository is public, or
- You have access if it's private

## What Gets Cloned

The repository includes:
- ✅ All Python scripts
- ✅ Configuration examples
- ✅ Documentation files
- ✅ Setup scripts
- ✅ Requirements file

**Does NOT include** (by design, for security):
- ❌ `credentials.json` (you must copy this)
- ❌ `config.yaml` (you must copy this)
- ❌ `token.json` (generated automatically)
- ❌ Processing directories (`zips/`, `extracted/`, `processed/`)

