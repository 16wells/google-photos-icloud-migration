# Easy Launcher Guide for Non-Technical Users

This guide explains how to use the simplified launcher interface for the Google Photos to iCloud Migration Tool.

## Quick Start (3 Easy Steps)

### Step 1: Open the Launcher
Double-click the `launcher.html` file in your migration tool folder. It will open in your default web browser.

### Step 2: Start the Web Server
The launcher page will check if the web server is running. If it's not running, you'll see instructions. Simply:
- **Double-click** the `start-web-server.command` file in the same folder, OR
- Copy and paste the command shown into Terminal

### Step 3: Access the Tool
Once the server is running (the launcher will show a green "✅ Web Server is Running" message):
- Click the **"Open Web Interface"** button
- The full migration tool will open in a new tab

## What the Launcher Shows

The launcher page displays:

### 🟢 Server Status
- **Green (Online)**: Web server is running and ready to use
- **Red (Offline)**: Web server needs to be started

### 📊 Migration Statistics
When the server is running, you'll see:
- Number of ZIP files processed
- Total media files found
- Files successfully uploaded
- Failed uploads count
- Albums identified
- Time elapsed

### ⚠️ Failed Uploads
If any files failed to upload, they'll be listed here with:
- File name and path
- Album it belongs to
- Error message
- When it failed

## Bookmarking for Easy Access

### Bookmark the Launcher
1. Open `launcher.html` in your browser
2. Bookmark the page (Cmd+D on Mac)
3. Name it something like "Google Photos Migration"
4. Now you can access it anytime from your bookmarks!

### Desktop Shortcut (macOS)
1. Find `launcher.html` in Finder
2. Right-click → "Make Alias"
3. Drag the alias to your Desktop
4. Double-click it anytime to open the launcher

## Starting the Server Automatically

### Option 1: Create a Desktop Shortcut
1. Find `start-web-server.command` in Finder
2. Right-click → "Make Alias"
3. Drag the alias to your Desktop
4. Double-click whenever you want to start the server

### Option 2: Add to Login Items (Auto-start on Mac startup)
1. Open System Preferences → Users & Groups
2. Click your username → Login Items
3. Click the "+" button
4. Navigate to and select `start-web-server.command`
5. The server will now start automatically when you log in

## Troubleshooting

### "Permission Denied" Error
If you can't run `start-web-server.command`:
```bash
chmod +x start-web-server.command
```

### Port Already in Use
If you see an error about port 5001 being in use:
1. Another instance may be running
2. Stop it: Open Terminal and run `pkill -f web_server.py`
3. Try starting again

### Can't See Statistics or Failed Uploads
- Make sure the web server is running (green status)
- Click the "Refresh Status" button
- Check that your browser isn't blocking local connections

## Files Overview

| File | Purpose |
|------|---------|
| `launcher.html` | The easy-to-use launcher page you open in your browser |
| `start-web-server.command` | Double-click this to start the web server |
| `web_server.py` | The actual web server (you don't need to touch this) |
| `config.yaml` | Your migration settings |

## Security Note

All of this runs locally on your Mac. Nothing is sent to external servers. The web interface only works at `http://localhost:5001`, which means only you can access it from your computer.

## Need Help?

If you need to run commands in Terminal:
1. Open Terminal (Applications → Utilities → Terminal)
2. Type or paste the command
3. Press Enter

The launcher page shows the exact commands you need, with a "Copy" button for easy pasting.

## Advanced: Running Server in Background

If you don't want to keep a Terminal window open:

```bash
# Start server in background
cd /Users/skipshean/Sites/google-photos-icloud-migration
nohup python3 web_server.py > web_server.log 2>&1 &

# Check if it's running
curl http://localhost:5001/api/server/status

# Stop it when done
pkill -f web_server.py
```

## Summary

The new launcher makes it easy for anyone to use the migration tool:
1. 📄 Open `launcher.html` → See status and stats
2. ▶️ Double-click `start-web-server.command` → Start the server
3. 🌐 Click "Open Web Interface" → Use the full migration tool
4. 🔖 Bookmark for easy access anytime!

No Terminal commands needed (except for first-time setup)!

