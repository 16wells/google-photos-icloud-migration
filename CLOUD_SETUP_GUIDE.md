# Google Cloud OAuth Setup Guide

This guide explains how to set up Google Cloud OAuth credentials (sometimes called "cloud agents") for the Google Photos to iCloud migration tool.

## What Are "Cloud Agents"?

"Cloud agents" in this context refers to **Google Cloud OAuth credentials** - the authentication mechanism that allows the tool to access your Google Drive to download Google Takeout zip files.

## Current Status

To check your current setup status, run:

```bash
python3 verify-cloud-setup.py
```

This will show you:
- ✅ Whether your credentials file is valid
- ✅ Whether you've authenticated (token.json exists)
- ✅ Whether you can connect to Google Drive API

## Quick Setup

### Step 1: Verify Credentials File

Your `credentials.json` file should already exist. Verify it's valid:

```bash
python3 verify-cloud-setup.py
```

If it shows "✓ Credentials file is valid", you're good to go!

### Step 2: Authenticate

You need to authenticate with Google Drive. This is a one-time process that creates a `token.json` file.

**Option A: Interactive Setup (Recommended)**
```bash
python3 auth_setup.py
```

This will:
- Guide you through the authentication process
- Open a browser for you to sign in
- Create the `token.json` file automatically

**Option B: Authenticate via Main Script**
```bash
python3 main.py --config config.yaml
```

The script will automatically prompt you to authenticate on first run.

### Step 3: Test Connection

Verify everything is working:

```bash
python3 verify-cloud-setup.py --test-connection
```

This will test the actual connection to Google Drive API.

## Troubleshooting

### Problem: "Credentials file not found"

**Solution:** You need to create Google Cloud OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable Google Drive API:
   - Go to **APIs & Services → Library**
   - Search for "Google Drive API"
   - Click **Enable**
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services → Credentials**
   - Click **+ CREATE CREDENTIALS → OAuth client ID**
   - Configure OAuth consent screen (if prompted):
     - Choose "External"
     - Fill in app name and your email
     - Add your email as a test user
   - Back at Credentials, create OAuth client ID:
     - Application type: **Desktop app**
     - Name: "Photos Migration Desktop Client"
     - Click **Create**
   - Download the JSON file
5. Save the downloaded file as `credentials.json` in this directory

### Problem: "Authentication failed" or "Token not found"

**Solution:** You need to authenticate:

```bash
python3 auth_setup.py
```

Or run the main script - it will prompt for authentication automatically.

### Problem: "Google Drive API connection failed"

**Possible causes:**
1. Google Drive API not enabled in your project
   - Go to [Google Cloud Console APIs](https://console.cloud.google.com/apis/library)
   - Search for "Google Drive API"
   - Make sure it's enabled

2. Invalid credentials
   - Verify credentials file: `python3 verify-cloud-setup.py`
   - Make sure you downloaded the correct file (Desktop app type)

3. Network issues
   - Check your internet connection
   - Try again later

### Problem: "Browser doesn't open" (headless environment)

**Solution:** The script will provide a URL for manual authentication:

1. Copy the authorization URL shown in the terminal
2. Open it in a browser
3. Sign in and authorize
4. Copy the redirect URL (or just the code parameter)
5. Paste it back into the terminal

## What Gets Created

- **`credentials.json`**: OAuth client ID **and client secret** (one-time setup). **Treat this as sensitive** (don’t commit to git; don’t share publicly).
- **`token.json`**: Your access token (auto-generated, keep private)

The `token.json` file allows the tool to access your Google Drive without asking for your password every time.

## Security Notes

- ✅ OAuth 2.0 is secure and industry-standard
- ✅ Your Google password is never stored
- ✅ Tokens can be revoked at any time
- ✅ Access is limited to Google Drive read-only
- ⚠️ `credentials.json` contains an OAuth **client secret**. **Keep it private** and **never commit it**.
- ⚠️ `token.json` contains your access token (keep private)

## Revoking Access

To revoke access:
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Click "Third-party apps with account access"
3. Find your app and click "Remove access"

Or delete `token.json` to force re-authentication.

## Next Steps

Once your cloud setup is complete:

1. **Verify setup:**
   ```bash
   python3 verify-cloud-setup.py --test-connection
   ```

2. **Run the migration:**
   ```bash
   python3 main.py --config config.yaml --use-sync
   ```

## Summary

- **"Cloud agents"** = Google Cloud OAuth credentials
- **Setup:** Create credentials in Google Cloud Console
- **Authentication:** One-time process via `auth_setup.py` or main script
- **Verification:** Use `verify-cloud-setup.py` to check status

For more details, see [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md).





