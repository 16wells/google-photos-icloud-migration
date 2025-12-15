# Google Photos Deletion Script Guide

## Overview

This script allows you to delete all photos and videos from your Google Photos account using browser automation. Since the Google Photos API doesn't support deletion, this script automates the web interface.

**⚠️ WARNING: This will permanently delete all photos and videos. Make sure you have a complete backup via Google Takeout before proceeding!**

## Prerequisites

1. **Complete backup**: Ensure you've downloaded everything via Google Takeout
2. **Browser**: Chrome or Safari (Safari is built-in on macOS, no additional installation needed)
3. **Python dependencies**: Install required packages

## Installation

1. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate it
   # macOS/Linux:
   source venv/bin/activate
   # Windows:
   # venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Choose your browser:**

   **Option A: Safari (Recommended for macOS)**
   - No additional installation needed - Safari is built-in!
   - Enable Safari WebDriver:
     ```bash
     # 1. Enable Develop menu in Safari:
     #    Safari > Preferences > Advanced > Show Develop menu
     
     # 2. Enable Remote Automation:
     #    Develop > Allow Remote Automation
     
     # 3. Authorize safaridriver (run in terminal):
     /usr/bin/safaridriver --enable
     ```
   - That's it! Safari is ready to use.

   **Option B: Chrome**
   - The script uses `webdriver-manager` which automatically downloads and manages ChromeDriver. No manual installation needed!
   - **Alternative:** If you prefer manual installation:
     - Download ChromeDriver from: https://googlechromelabs.github.io/chrome-for-testing/
     - Extract and place `chromedriver` in your PATH
     - ⚠️ **Note:** Homebrew's `chromedriver` is deprecated and will be disabled on 2026-09-01

## Usage

### Step 1: Activate Virtual Environment

Make sure your virtual environment is activated:

```bash
source venv/bin/activate  # macOS/Linux
# or
# venv\Scripts\activate  # Windows
```

### Step 2: Dry Run (Plan Mode) - **RECOMMENDED FIRST**

Run the script in dry-run mode to see what would be deleted:

```bash
python delete_google_photos.py --dry-run
```

This will:
- Open Google Photos in a browser
- Ask you to log in manually
- Scan your photos to estimate how many would be deleted
- Show you a plan without actually deleting anything

### Step 3: Review the Plan

The script will display:
- Estimated number of photos/videos
- Account URL
- Scan information

**Review this carefully before proceeding!**

### Step 4: Execute Deletion (If You're Sure)

If you're certain you want to delete everything:

```bash
python delete_google_photos.py --execute
```

You'll be asked to type two confirmations:
1. `DELETE ALL PHOTOS`
2. `YES I AM SURE`

## Options

```bash
# Make sure venv is activated first!
source venv/bin/activate

# Dry run (default - safe, no deletion)
python delete_google_photos.py --dry-run

# Actually delete (requires confirmations)
python delete_google_photos.py --execute

# Use Safari instead of Chrome (macOS)
python delete_google_photos.py --execute --browser safari

# Run in headless mode (Chrome only, no visible browser)
python delete_google_photos.py --execute --headless

# Customize batch size and delay
python delete_google_photos.py --execute --batch-size 100 --delay 3.0
```

### Command Line Arguments

- `--dry-run`: Plan mode - shows what would be deleted (default)
- `--execute`: Actually delete photos (overrides --dry-run)
- `--browser {chrome,safari}`: Browser to use (default: chrome)
- `--headless`: Run browser in headless mode (Chrome only, Safari doesn't support headless)
- `--batch-size N`: Number of items to delete per batch (default: 50)
- `--delay N`: Delay between operations in seconds (default: 2.0)

## How It Works

1. **Opens Google Photos**: Launches Chrome and navigates to photos.google.com
2. **Manual Login**: You log in to your Google account in the browser
3. **Scans Photos**: Scrolls through your library to estimate total count
4. **Shows Plan**: Displays what would be deleted (in dry-run mode)
5. **Deletes in Batches**: Selects and deletes photos in batches to avoid timeouts
6. **Progress Tracking**: Shows progress and logs all operations

## Safety Features

- **Dry-run by default**: Won't delete anything unless you explicitly use `--execute`
- **Double confirmation**: Requires typing two confirmation phrases
- **Progress logging**: All operations logged to `google_photos_deletion.log`
- **Batch processing**: Deletes in manageable batches to avoid errors
- **Error handling**: Continues even if some batches fail

## Troubleshooting

### Browser Setup Issues

**Safari WebDriver Issues:**

If Safari fails to initialize:

1. **Enable Develop menu:**
   - Safari > Preferences > Advanced
   - Check "Show Develop menu in menu bar"

2. **Enable Remote Automation:**
   - Develop > Allow Remote Automation

3. **Authorize safaridriver:**
   ```bash
   /usr/bin/safaridriver --enable
   ```
   You may be prompted for your password.

**ChromeDriver Not Found:**

The script uses `webdriver-manager` which should automatically download ChromeDriver. If you encounter issues:

1. **Make sure webdriver-manager is installed:**
   ```bash
   pip install webdriver-manager
   ```

2. **Manual installation (if needed):**
   - Download from: https://googlechromelabs.github.io/chrome-for-testing/
   - Extract and place `chromedriver` in your PATH
   - ⚠️ **Note:** Homebrew's `chromedriver` is deprecated and will be disabled on 2026-09-01

### Browser Doesn't Open

**For Chrome:**
- Make sure Chrome is installed
- Try running without `--headless` to see what's happening
- Check that ChromeDriver version matches your Chrome version

**For Safari:**
- Make sure Safari is installed (comes with macOS)
- Verify Remote Automation is enabled: Develop > Allow Remote Automation
- Run `/usr/bin/safaridriver --enable` if you haven't already
- Safari doesn't support headless mode - the browser window will always be visible

### Photos Not Being Selected

- The script uses keyboard shortcuts (Cmd+A / Ctrl+A)
- Make sure the browser window has focus
- Try increasing the `--delay` value

### Deletion Fails

- Google Photos UI may have changed
- Check the log file: `google_photos_deletion.log`
- Try running in non-headless mode to see what's happening
- You may need to manually adjust selectors in the script

## Logs

All operations are logged to:
- `google_photos_deletion.log` - Main log file
- Console output - Real-time progress

## Important Notes

1. **This is irreversible**: Once deleted, photos cannot be recovered (unless you have backups)
2. **Takes time**: Large libraries may take hours to delete
3. **Keep browser open**: Don't close the browser window during deletion
4. **Network required**: Needs stable internet connection
5. **Rate limiting**: Google may rate-limit if you delete too quickly (script includes delays)

## Quick Start Summary

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Setup Safari (if using Safari instead of Chrome):
#    - Safari > Preferences > Advanced > Show Develop menu
#    - Develop > Allow Remote Automation
#    - Run: /usr/bin/safaridriver --enable

# 4. Run dry-run first (safe, no deletion)
python delete_google_photos.py --dry-run

# 5. If satisfied, execute deletion
python delete_google_photos.py --execute

# Or use Safari:
python delete_google_photos.py --execute --browser safari
```
