# Authentication Guide

This guide explains how authentication works for the Google Photos to iCloud Photos migration tool.

## Overview

The tool needs to authenticate with two services:
1. **Google Drive** - To download your Google Takeout zip files
2. **Apple/iCloud** - To upload photos to iCloud Photos (optional, depends on method)

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

- **`credentials.json`**: OAuth client ID and secret (one-time setup, safe to share)
- **`token.json`**: Your access token (auto-generated, don't share)

The `token.json` file allows the tool to access your Google Drive without asking for your password every time.

## Apple/iCloud Authentication

### PhotoKit Method (--use-sync) - Recommended

**No authentication needed!** 

The PhotoKit method uses your macOS system's iCloud account automatically. It:
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

### API Method (Alternative)

The API method uses `pyicloud` library and requires:
- Apple ID email
- Apple ID password
- 2FA code (if 2FA is enabled)

**Limitations:**
- Apple doesn't provide OAuth for iCloud Photos API
- Requires password (stored in config or entered interactively)
- May have API limitations
- 2FA can be complex on headless systems

**Recommendation:** Use PhotoKit method (`--use-sync`) instead if you're on macOS.

## Security Considerations

### Google Drive

- ✅ OAuth 2.0 is secure and industry-standard
- ✅ Your Google password is never stored
- ✅ Tokens can be revoked at any time
- ✅ Access is limited to Google Drive read-only
- ⚠️ `credentials.json` contains OAuth client secrets (safe to share, but don't commit to public repos)
- ⚠️ `token.json` contains your access token (keep private)

### Apple/iCloud

**PhotoKit Method:**
- ✅ Uses system authentication (most secure)
- ✅ No passwords stored
- ✅ Uses macOS security features

**API Method:**
- ⚠️ Requires Apple ID password
- ⚠️ Password stored in `config.yaml` (keep private)
- ⚠️ 2FA codes may be needed

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

**API Method:**
- **Problem:** "2FA required"
  - **Solution:** Enter 2FA code when prompted, or use trusted device ID

- **Problem:** "Authentication failed"
  - **Solution:** 
    - Verify Apple ID and password
    - Check if 2FA is enabled
    - Try clearing cookies: `rm -rf ~/.pyicloud`

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

**API Method:** 
- Remove password from `config.yaml`
- Delete `~/.pyicloud` directory to clear cookies

## Best Practices

1. **Use the setup wizard** for easiest experience
2. **Use PhotoKit method** (`--use-sync`) on macOS for best security
3. **Keep `token.json` and `config.yaml` private** (don't commit to git)
4. **Revoke access** if you stop using the tool
5. **Use separate Google Cloud project** for production use

## Summary

- **Google Drive**: OAuth 2.0, one-time setup, secure
- **Apple/iCloud (PhotoKit)**: No auth needed, uses system account
- **Apple/iCloud (API)**: Requires password, less secure, not recommended

For the best experience, use the setup wizard and PhotoKit method!

