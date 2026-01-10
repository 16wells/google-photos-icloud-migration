# Authentication Guide

This guide explains how authentication works for the Google Photos to iCloud Photos migration tool.

## Overview

The tool needs to authenticate with one service:
1. **Google Drive** - To download your Google Takeout zip files

**Note:** No iCloud authentication needed! The tool uses your macOS iCloud account automatically via PhotoKit.

## Quick Start: Use the Setup Wizard

The easiest way to set up authentication is to use the built-in wizard:

```bash
python3 auth_setup.py
```

This will guide you through everything step-by-step with no manual file management needed!

> **New to the tool?** See [QUICKSTART.md](../QUICKSTART.md) for a complete 5-minute setup guide.

## Google Drive Authentication

### How It Works

The tool uses **OAuth 2.0** to authenticate with Google Drive. This is a secure, industry-standard method that:
- Never stores your Google password
- Uses temporary access tokens
- Automatically refreshes tokens when they expire
- Requires one-time setup

### Setup Methods

#### Method 1: Interactive Setup Wizard (Recommended)

Run the setup wizard:
```bash
python3 auth_setup.py
```

The wizard will:
1. Guide you through creating Google Cloud credentials
2. Open browser windows for you to sign in
3. Automatically handle the OAuth flow
4. Save credentials securely

#### Method 2: Manual Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable Google Drive API**
   - Go to APIs & Services → Library
   - Search for "Google Drive API"
   - Click "Enable"

3. **Create OAuth Credentials**
   - Go to APIs & Services → Credentials
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Configure OAuth consent screen (if prompted)
   - Application type: "Desktop app"
   - Download the JSON file as `credentials.json`

4. **Authenticate**
   - The tool will automatically open a browser
   - Sign in with your Google account
   - Grant permission to access Google Drive
   - You'll be redirected back automatically

### What Gets Stored

- **`credentials.json`**: OAuth client ID **and client secret** (one-time setup). **Treat this as sensitive** (don’t commit to git; don’t share publicly).
- **`token.json`**: Your access token (auto-generated, don't share)

The `token.json` file allows the tool to access your Google Drive without asking for your password every time.

## Apple/iCloud Authentication

**No authentication needed!** 

The tool uses your macOS system's iCloud account automatically via PhotoKit. It:
- Uses the Apple ID you're signed into on your Mac
- Requires no passwords or credentials
- Works seamlessly with iCloud Photos
- Preserves all metadata

**Requirements:**
- macOS (required for PhotoKit)
- Signed into iCloud on your Mac
- iCloud Photos enabled in System Settings (optional, but recommended)

**To enable iCloud Photos:**
1. System Settings → Apple ID → iCloud
2. Enable "Photos" (or "iCloud Photos")
3. Choose "Download Originals" or "Optimize Storage"

**Note:** This tool requires macOS and uses PhotoKit. It cannot be run on Linux, Windows, or in virtual machines/cloud servers.

## Environment Variables (.env File)

For better security, you can store sensitive credentials in a `.env` file instead of `config.yaml`. The `.env` file is automatically ignored by git (already in `.gitignore`).

### Setup .env File

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your credentials:**
   ```bash
   # Google Drive Configuration (optional)
   GOOGLE_DRIVE_CREDENTIALS_FILE=credentials.json
   
   # GitHub Token (for repository management scripts, optional)
   GITHUB_TOKEN=your_github_token_here
   
   # Note: iCloud credentials are NOT needed!
   # The tool uses your macOS iCloud account automatically via PhotoKit.
   ```

3. **Environment variables take precedence** over `config.yaml` values, providing an extra layer of security.

### Supported Environment Variables

- `GOOGLE_DRIVE_CREDENTIALS_FILE` - Path to credentials.json (optional)
- `GITHUB_TOKEN` - GitHub personal access token (for scripts like `scripts/set_github_repo_info.py`, optional)

**Note:** iCloud credentials are not needed - the tool uses your macOS iCloud account automatically via PhotoKit.

**Note:** The tool automatically loads `.env` files using `python-dotenv` (already included in `requirements.txt`).

## Security Considerations

### Google Drive

- ✅ OAuth 2.0 is secure and industry-standard
- ✅ Your Google password is never stored
- ✅ Tokens can be revoked at any time
- ✅ Access is limited to Google Drive read-only
- ⚠️ `credentials.json` contains an OAuth **client secret**. **Keep it private** and **never commit it** (even in private repos, unless you absolutely must).
- ⚠️ `token.json` contains your access token (keep private)

### Apple/iCloud

**PhotoKit Method:**
- ✅ Uses system authentication (most secure)
- ✅ No passwords stored
- ✅ Uses macOS security features

**Note:** The tool uses PhotoKit sync method which requires no authentication. It uses your macOS iCloud account automatically.

## Troubleshooting

### Google Drive Authentication Issues

**Problem:** "Credentials file not found"
- **Solution:** Run `python3 auth_setup.py` to set up credentials

**Problem:** "Authentication failed"
- **Solution:** 
  - Delete `token.json` and try again
  - Make sure `credentials.json` is valid
  - Check internet connection

**Problem:** Browser doesn't open
- **Solution:** 
  - Manually visit the URL shown in terminal
  - Copy the authorization code from the redirect URL
  - Paste it when prompted

### Apple/iCloud Authentication Issues

**PhotoKit Method:**
- **Problem:** "Photo library write permission denied"
  - **Solution:** Grant permission in System Settings → Privacy & Security → Photos

- **Problem:** Photos not syncing to iCloud
  - **Solution:** Enable iCloud Photos in System Settings → Apple ID → iCloud

**Note:** No authentication issues should occur with PhotoKit method as it uses your macOS iCloud account automatically. If you have issues, check:
- You're signed into iCloud on your Mac
- iCloud Photos is enabled in System Settings
- Photo library write permission is granted

## Revoking Access

### Google Drive

To revoke access:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Click "Third-party apps with account access"
3. Find "Photos Migration Tool" (or your app name)
4. Click "Remove access"

Or delete `token.json` to force re-authentication.

### Apple/iCloud

**PhotoKit Method:** No action needed - uses system account

**Note:** PhotoKit method requires no cleanup - it uses your macOS iCloud account automatically. No credentials are stored.

## Best Practices

1. **Use the setup wizard** for easiest experience
2. **Use `.env` file** for sensitive credentials (GitHub token, Google Drive credentials, etc.)
3. **Keep `token.json`, `config.yaml`, and `.env` private** (don't commit to git - `.env` is already gitignored)
4. **Revoke access** if you stop using the tool
5. **Use separate Google Cloud project** for production use
6. **Ensure iCloud Photos is enabled** on your Mac for automatic syncing

## Summary

- **Google Drive**: OAuth 2.0, one-time setup, secure
- **Apple/iCloud (PhotoKit)**: No auth needed, uses macOS iCloud account automatically, secure

This tool uses PhotoKit sync method exclusively - no passwords or credentials needed for iCloud!

