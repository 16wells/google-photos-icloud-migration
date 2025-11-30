# Web POC Quick Start Guide

This guide will help you get the web-based POC running quickly. **If you're new to command line/Terminal, don't worry!** This guide explains everything step-by-step.

## Quick Reference (For Experienced Users)

If you're comfortable with Terminal/command line, here's the TL;DR:

```bash
# Install dependencies
pip3 install -r requirements-web.txt

# Install ExifTool
brew install exiftool  # Mac
# OR download from exiftool.org for Windows/Linux

# Set environment variables
export GOOGLE_CLIENT_ID="your-id"
export GOOGLE_CLIENT_SECRET="your-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/auth/google/callback"
export SECRET_KEY="your-secret-key"

# Run the app
cd web
python3 app.py
```

Then visit http://localhost:5000

**For detailed instructions, continue reading below.**

## Glossary (Important Terms)

**Terminal/Command Line:** A text-based way to control your computer by typing commands instead of clicking buttons.

**Directory/Folder:** A location on your computer where files are stored. Same thing, different names.

**Command:** An instruction you type in Terminal to tell the computer what to do (e.g., `cd`, `ls`, `python`).

**PATH:** A list of directories where your computer looks for programs. If a program isn't in your PATH, you can't run it by name.

**Environment Variable:** A setting that programs can read. Like a sticky note that says "GOOGLE_CLIENT_ID = abc123".

**Dependencies/Packages:** Additional code libraries that this project needs to work. Like installing plugins for a program.

**OAuth:** A secure way for apps to access your Google account without giving them your password.

**2FA (Two-Factor Authentication):** An extra security step where you enter a code from your phone/device in addition to your password.

## Prerequisites

1. Python 3.8 or higher
2. ExifTool installed (`brew install exiftool` on macOS)
3. Google OAuth credentials (see setup below)

## Installation

### Step 1: Open Terminal/Command Line

**What is Terminal/Command Line?**
- Terminal (Mac/Linux) or Command Prompt/PowerShell (Windows) is a text-based way to interact with your computer
- You'll type commands and press Enter to execute them

**How to open it:**
- **Mac**: Press `Cmd + Space`, type "Terminal", press Enter
- **Windows**: Press `Windows + R`, type "cmd", press Enter
- **Linux**: Press `Ctrl + Alt + T` or search for "Terminal" in applications

**What you'll see:**
- A window with text, usually showing something like `username@computer:~$` or `C:\Users\username>`
- This is called the "command prompt" - it's waiting for you to type commands

### Step 2: Navigate to the Project Directory

**What this means:** You need to tell the terminal which folder (directory) you want to work in.

**How to do it:**

1. **First, find where you saved this project:**
   - Look for the folder `google-photos-icloud-migration` on your computer
   - Note the full path (location) of this folder
   - Example paths:
     - Mac: `/Users/yourname/Sites/google-photos-icloud-migration`
     - Windows: `C:\Users\yourname\Sites\google-photos-icloud-migration`

2. **In Terminal, type this command (replace with YOUR actual path):**
   ```bash
   cd /Users/yourname/Sites/google-photos-icloud-migration
   ```
   - **Mac/Linux**: Use forward slashes `/`
   - **Windows**: Use backslashes `\` or forward slashes `/`
   - Press Enter after typing

3. **Verify you're in the right place:**
   ```bash
   pwd
   ```
   - This shows your current directory
   - On Windows, use `cd` instead of `pwd`

4. **List files to confirm:**
   ```bash
   ls
   ```
   - Mac/Linux: `ls`
   - Windows: `dir`
   - You should see files like `README.md`, `requirements-web.txt`, `web/`, etc.

### Step 3: Check Python Installation

**What this means:** We need to make sure Python is installed on your computer.

**How to check:**

1. **Type this command:**
   ```bash
   python --version
   ```
   - Or try: `python3 --version`
   - You should see something like `Python 3.8.5` or higher

2. **If you get an error:**
   - **Mac**: Install Python from [python.org](https://www.python.org/downloads/) or use Homebrew: `brew install python3`
   - **Windows**: Download and install from [python.org](https://www.python.org/downloads/)
   - **Linux**: Usually pre-installed, but if not: `sudo apt-get install python3`

### Step 4: Install Python Dependencies

**What this means:** The project needs additional Python packages (libraries) to work. We'll install them all at once.

**How to do it:**

1. **Make sure you're in the project root directory** (where you see `requirements-web.txt`)

2. **Install all dependencies:**
   ```bash
   pip install -r requirements-web.txt
   ```
   - Or try: `pip3 install -r requirements-web.txt`
   - This command reads the `requirements-web.txt` file and installs everything listed in it
   - **What it does:** Downloads and installs packages like Flask, Google API client, etc.
   - **How long:** Usually takes 1-5 minutes depending on your internet speed

3. **What you'll see:**
   - Lots of text scrolling by showing what's being installed
   - Look for "Successfully installed" messages at the end
   - If you see errors, see Troubleshooting section below

4. **Verify installation:**
   ```bash
   pip list
   ```
   - This shows all installed packages
   - You should see `Flask`, `google-api-python-client`, etc. in the list

### Step 5: Install ExifTool (Required for Metadata Processing)

**What this means:** ExifTool is a separate program (not a Python package) that processes photo metadata.

**How to install:**

**Mac (using Homebrew - recommended):**
```bash
brew install exiftool
```

**Mac (without Homebrew):**
1. Download from [exiftool.org](https://exiftool.org/)
2. Extract and follow installation instructions

**Windows:**
1. Download Windows executable from [exiftool.org](https://exiftool.org/)
2. Extract to a folder (e.g., `C:\exiftool`)
3. Add to PATH (search "how to add folder to PATH Windows")

**Linux:**
```bash
sudo apt-get install libimage-exiftool-perl
```

**Verify installation:**
```bash
exiftool -ver
```
- Should show a version number like `12.50`

### Step 6: Set up Google OAuth Credentials

**What this means:** You need to create credentials so the app can access your Google Drive.

**Step-by-step:**

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create or select a project:**
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it something like "Photos Migration"
   - Click "Create"

3. **Enable Google Drive API:**
   - In the left menu, go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on it, then click "Enable"

4. **Create OAuth credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure OAuth consent screen first:
     - Choose "External" (unless you have a Google Workspace account)
     - Fill in app name: "Photos Migration"
     - Add your email as support email
     - Click "Save and Continue" through the steps
   - Back to creating OAuth client:
     - Application type: Choose "Web application"
     - Name: "Photos Migration Web App"
     - Authorized redirect URIs: Click "Add URI"
     - Enter: `http://localhost:5000/auth/google/callback`
     - Click "Create"
   - **IMPORTANT:** Copy the Client ID and Client Secret
     - You'll see a popup with these values
     - Save them somewhere safe (you'll need them in the next step)

### Step 7: Set Environment Variables

**What this means:** We need to tell the app your Google credentials. There are two ways to do this.

**Option A: Set Environment Variables (Temporary - Lost When Terminal Closes)**

1. **Open Terminal** (if not already open)

2. **Navigate to the project directory** (if not already there):
   ```bash
   cd /path/to/google-photos-icloud-migration
   ```

3. **Set each variable** (replace with YOUR actual values):
   ```bash
   export GOOGLE_CLIENT_ID="paste-your-client-id-here"
   export GOOGLE_CLIENT_SECRET="paste-your-client-secret-here"
   export GOOGLE_REDIRECT_URI="http://localhost:5000/auth/google/callback"
   export SECRET_KEY="create-a-random-secret-key-here"
   ```

4. **For the SECRET_KEY**, you can generate a random string:
   - Mac/Linux: `openssl rand -hex 32`
   - Or just make up a long random string like: `my-secret-key-12345-change-this`

5. **Verify they're set:**
   ```bash
   echo $GOOGLE_CLIENT_ID
   ```
   - Should show your client ID

**Note:** These variables are lost when you close Terminal. You'll need to set them again each time.

**Option B: Create a .env File (Recommended - Permanent)**

1. **Navigate to the web directory:**
   ```bash
   cd web
   ```

2. **Create a new file called `.env`:**
   - Mac/Linux:
     ```bash
     nano .env
     ```
   - Windows (using notepad):
     ```bash
     notepad .env
     ```

3. **Add these lines** (replace with YOUR actual values):
   ```
   GOOGLE_CLIENT_ID=your-actual-client-id-here
   GOOGLE_CLIENT_SECRET=your-actual-client-secret-here
   GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
   SECRET_KEY=your-random-secret-key-here
   ```

4. **Save the file:**
   - **Nano (Mac/Linux)**: Press `Ctrl + X`, then `Y`, then Enter
   - **Notepad (Windows)**: Click File > Save

5. **Important:** The `.env` file contains secrets. Don't commit it to git!

**Note:** The app currently doesn't auto-load `.env` files. You'll need to either:
- Use Option A (export commands) each time, OR
- Install `python-dotenv` and modify `app.py` to load `.env` (see Advanced Setup below)

## Running the Application

### Step 1: Navigate to the Web Directory

**In Terminal, type:**
```bash
cd web
```

**What this does:** Changes your current directory to the `web` folder inside the project.

**Verify you're in the right place:**
```bash
ls
```
- You should see files like `app.py`, `templates/`, `routes/`, etc.

**If you get "No such file or directory":**
- Make sure you're in the project root first: `cd /path/to/google-photos-icloud-migration`
- Then try `cd web` again

### Step 2: Set Environment Variables (If Using Option A)

**If you chose Option A** (export commands) in Step 7 above, you need to set them again:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/auth/google/callback"
export SECRET_KEY="your-secret-key"
```

**Note:** You must do this EVERY TIME you open a new Terminal window.

### Step 3: Run the Flask Application

**Type this command:**
```bash
python app.py
```

**Or if that doesn't work, try:**
```bash
python3 app.py
```

**What you should see:**
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

**What this means:**
- The web server is now running
- It's listening on port 5000
- The app is accessible at `http://localhost:5000`
- **Don't close this Terminal window!** The server needs to keep running

**If you see errors:**
- See Troubleshooting section below
- Common issues:
  - "Module not found" → Dependencies not installed (go back to Step 4)
  - "Address already in use" → Port 5000 is taken (close other apps or change port)
  - "GOOGLE_CLIENT_ID not set" → Environment variables not set (go back to Step 7)

### Step 4: Open the Application in Your Browser

1. **Open your web browser** (Chrome, Firefox, Safari, etc.)

2. **Type this in the address bar:**
   ```
   http://localhost:5000
   ```
   - Or try: `http://127.0.0.1:5000`

3. **What you should see:**
   - A page titled "Google Photos to iCloud Migration"
   - Three steps: Connect Google Drive, Sign in to iCloud, Start Migration

**If the page doesn't load:**
- Make sure the Flask app is still running in Terminal (Step 3)
- Check that you typed the URL correctly
- Try refreshing the page
- Check Terminal for error messages

### Step 5: Stopping the Application

**When you're done:**
- Go back to the Terminal window where Flask is running
- Press `Ctrl + C` (Mac/Linux) or `Ctrl + C` (Windows)
- This stops the server gracefully

**To run it again later:**
- Just repeat Steps 1-3 above

## Usage Flow

1. **Authenticate with Google Drive:**
   - Click "Connect Google Drive"
   - Sign in with your Google account
   - Grant permissions to access Google Drive

2. **Authenticate with iCloud:**
   - Click "Sign in to iCloud"
   - Enter your Apple ID and password
   - If 2FA is required:
     - Select a trusted device
     - Enter the verification code

3. **Start Migration:**
   - Configure migration settings (optional):
     - Google Drive Folder ID (leave empty to search all folders)
     - Zip file pattern (default: `takeout-*.zip`)
   - Click "Start Migration"
   - Monitor progress on the dashboard

## Troubleshooting

### "Command not found" or "pip: command not found"

**Problem:** Python or pip is not installed or not in your PATH.

**Solutions:**
- **Mac:** Install Python from [python.org](https://www.python.org/downloads/) or use Homebrew: `brew install python3`
- **Windows:** Download Python installer from [python.org](https://www.python.org/downloads/) - **IMPORTANT:** Check "Add Python to PATH" during installation
- **Linux:** `sudo apt-get install python3 python3-pip`

**Verify installation:**
```bash
python3 --version
pip3 --version
```

### Import Errors (ModuleNotFoundError)

**Problem:** Python packages aren't installed.

**Solution:**
1. Make sure you're in the project root directory
2. Run: `pip3 install -r requirements-web.txt`
3. If you get permission errors, try: `pip3 install --user -r requirements-web.txt`

**Still not working?**
- Try: `python3 -m pip install -r requirements-web.txt`
- Check Python version: `python3 --version` (needs 3.8+)

### "GOOGLE_CLIENT_ID not set" Error

**Problem:** Environment variables aren't set.

**Solutions:**
- **Option A users:** Make sure you ran the `export` commands in the same Terminal window
- **Option B users:** Check that `.env` file exists in `web/` directory
- Verify: `echo $GOOGLE_CLIENT_ID` (should show your client ID)

**Quick fix:** Set them again:
```bash
export GOOGLE_CLIENT_ID="your-id"
export GOOGLE_CLIENT_SECRET="your-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/auth/google/callback"
export SECRET_KEY="your-key"
```

### Google OAuth Errors

**"redirect_uri_mismatch" Error:**
- The redirect URI in Google Cloud Console must match EXACTLY: `http://localhost:5000/auth/google/callback`
- Check for typos, extra spaces, or missing `http://`
- Make sure you saved the OAuth credentials after adding the redirect URI

**"Access blocked" Error:**
- Your OAuth consent screen might need verification
- Go to Google Cloud Console > APIs & Services > OAuth consent screen
- Make sure you've completed all required fields

**"Invalid client" Error:**
- Double-check your Client ID and Client Secret are correct
- Make sure there are no extra spaces when copying/pasting
- Regenerate credentials if needed

### "Address already in use" Error

**Problem:** Port 5000 is already being used by another application.

**Solutions:**
1. **Find what's using port 5000:**
   - Mac/Linux: `lsof -i :5000`
   - Windows: `netstat -ano | findstr :5000`
2. **Close the other application** or change Flask's port:
   - Edit `web/app.py`, change `port=5000` to `port=5001`
   - Then access at `http://localhost:5001`

### iCloud Authentication Errors

**"2FA Required" but already completed:**
- The worker creates a new iCloud session, which may require 2FA again
- This is a limitation of the POC - complete 2FA when prompted
- In production, this would be handled better

**"Invalid credentials" Error:**
- Double-check your Apple ID and password
- Make sure you're using the correct Apple ID (not an alias)
- Try logging into icloud.com in a browser first to verify credentials

### Status Not Updating

**Problem:** Dashboard shows "Not started" even after clicking "Start Migration"

**Check:**
1. Open a new Terminal window
2. Check if status file exists:
   ```bash
   ls /tmp/migration_status_*.json
   ```
3. If files exist, check their contents:
   ```bash
   cat /tmp/migration_status_*.json
   ```
4. Make sure the session ID matches (check browser cookies or session storage)

**Solution:**
- Refresh the dashboard page
- Check browser console for JavaScript errors (F12 > Console)
- Make sure Flask app is still running

### Migration Worker Errors

**"ExifTool not found" Error:**
- Install ExifTool (see Step 5 in Installation)
- Verify: `exiftool -ver`
- Make sure it's in your PATH

**"Out of disk space" Error:**
- The migration uses `/tmp/google-photos-migration` for processing
- Check available space: `df -h /tmp` (Mac/Linux) or check disk properties (Windows)
- Free up space or change the base directory in the code

**"Permission denied" Errors:**
- Make sure you have write permissions to `/tmp/`
- Try creating the directory manually: `mkdir -p /tmp/google-photos-migration`
- On Mac/Linux, you might need `sudo` for some operations (not recommended)

### Browser Shows "This site can't be reached"

**Problem:** Flask app isn't running or wrong URL.

**Check:**
1. Is Flask still running in Terminal? (Look for the "Running on..." message)
2. Did you close the Terminal window? (You need to keep it open)
3. Is the URL correct? Should be `http://localhost:5000` (not `https://`)
4. Try `http://127.0.0.1:5000` instead

**Solution:**
- Go back to Terminal and start Flask again: `python3 app.py`
- Make sure you're in the `web/` directory

### "No zip files found" Error

**Problem:** Migration can't find Google Takeout zip files.

**Check:**
1. Did you specify a folder ID? Make sure it's correct
2. Is the zip file pattern correct? Default is `takeout-*.zip`
3. Are the files actually in Google Drive?
4. Check Google Drive API permissions - make sure you granted access

### General Tips

**Always check Terminal output:**
- Flask shows errors in the Terminal window
- Look for red error messages
- Copy error messages to search for solutions

**Check browser console:**
- Press F12 to open developer tools
- Click "Console" tab
- Look for red error messages
- These can help identify JavaScript or network issues

**Start fresh:**
- If nothing works, try:
  1. Close all Terminal windows
  2. Open a new Terminal
  3. Navigate to project: `cd /path/to/google-photos-icloud-migration`
  4. Set environment variables again
  5. Run: `cd web && python3 app.py`

## File Structure

```
web/
├── app.py                 # Main Flask application
├── routes/                # Route handlers
│   ├── auth.py           # Google/iCloud authentication
│   ├── migration.py      # Migration control
│   └── status.py         # Status/progress updates
├── services/             # Background services
│   └── migration_worker.py  # Migration worker thread
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   └── dashboard.html
└── flask_session/        # Session storage (auto-created)
```

## Notes

- This is a **proof of concept** - not production-ready
- Sessions are stored in files (use Redis/database in production)
- iCloud credentials are stored in session (encrypt in production)
- Status tracking uses file-based storage (use Redis in production)
- Background tasks run in threads (use Celery in production)

## Next Steps

For production deployment:
1. Use HTTPS and set `SESSION_COOKIE_SECURE = True`
2. Encrypt sensitive data (iCloud credentials)
3. Use Redis/database for sessions and status
4. Use Celery for background tasks
5. Add proper error recovery and retry logic
6. Add user authentication/accounts
7. Add monitoring and logging

