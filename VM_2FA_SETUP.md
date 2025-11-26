# Setting Up 2FA on VM (Non-Interactive Mode)

When running the migration script on a VM or in a non-interactive environment, 2FA (two-factor authentication) requires special handling since you cannot interactively enter the verification code.

## Quick Start (Recommended)

**For easiest setup, use the helper script:**

```bash
bash setup-vm-2fa.sh
```

This interactive script will:
1. Guide you through finding your trusted device ID
2. Help you request a verification code
3. Set up environment variables
4. Create a reusable setup script for your VM

**To request a verification code (and get setup instructions):**

```bash
python3 request-2fa-code.py
```

**Or check your current authentication status:**

```bash
python3 check-auth-status.py
```

This will show you:
- Whether authentication cookies exist and are valid
- What environment variables are set
- Configuration status
- Recommendations for next steps

---

## Helper Scripts

Three helper scripts are available to simplify VM 2FA setup:

1. **`setup-vm-2fa.sh`** - Interactive setup wizard (recommended for first-time setup)
2. **`request-2fa-code.py`** - Request a verification code and get setup instructions
3. **`check-auth-status.py`** - Check authentication status and cookie validity

---

## Option 1: Use Environment Variables (Recommended for VMs)

This method allows you to run the script non-interactively by providing the 2FA device ID and code via environment variables.

### Step 1: Find Your Trusted Device ID

First, run the script interactively once to see your trusted devices:

```bash
python3 main.py --config config.yaml
```

When prompted, the script will list your trusted devices:
```
Available trusted devices:
  0: iPhone (iPhone)
  1: MacBook Pro (Mac)
```

Note the device number you want to use (e.g., `0` for iPhone).

### Step 2: Set Environment Variables

```bash
# Set the device ID (the number from the list)
export ICLOUD_2FA_DEVICE_ID=0

# Request a verification code (the script will send it to your device)
# Wait for the code to arrive, then set it:
export ICLOUD_2FA_CODE=123456
```

### Step 3: Run the Script

```bash
python3 main.py --config config.yaml
```

The script will automatically use the environment variables for authentication.

## Option 2: Use Config File

Alternatively, you can set these values in `config.yaml`:

```yaml
icloud:
  apple_id: "your-apple-id@example.com"
  password: "your-password"
  trusted_device_id: "0"  # Device number from trusted devices list
  two_fa_code: "123456"   # Verification code (expires quickly!)
```

**Note:** Codes expire quickly (typically 10 minutes), so this method is only useful if you can update the config file immediately before running the script.

## Option 3: Pre-Authenticate and Copy Cookies

If you can authenticate interactively on your local machine first, you can copy the cookies to the VM:

### On Your Local Machine:

1. Run the authentication script interactively:
   ```bash
   python3 authenticate_icloud.py your-apple-id@example.com
   ```
   Enter your password and 2FA code when prompted.

2. The cookies will be saved to `~/.pyicloud/`

3. Copy the cookie directory to your VM:
   ```bash
   scp -r ~/.pyicloud user@vm-hostname:~/
   ```

### On the VM:

The cookies should now be available, and the script might bypass 2FA if the session is still valid.

**Note:** Cookies may expire, so this is only a temporary solution. You may need to refresh them periodically.

## Troubleshooting

### Error: "Non-interactive mode detected"

This means the script detected it's running without a terminal. Set the environment variables as described in Option 1.

### Error: "No trusted devices found"

1. Go to https://appleid.apple.com
2. Sign in with your Apple ID
3. Go to "Sign-In and Security" → "Two-Factor Authentication"
4. Make sure you have at least one trusted device listed

### Error: "Invalid 2FA code"

2FA codes expire quickly (usually within 10 minutes). Request a new code and try again:

```bash
# Re-run the script to request a new code
python3 main.py --config config.yaml
# Wait for the code, then set it again:
export ICLOUD_2FA_CODE=NEW_CODE
# Run again
python3 main.py --config config.yaml
```

### Cookies Not Working

If cookies exist but authentication still fails:

```bash
# Clear cookies and re-authenticate
rm -rf ~/.pyicloud
python3 main.py --config config.yaml
```

## Alternative: Use Sync Method (Bypasses 2FA)

If 2FA continues to be problematic, you can use the sync method which bypasses API authentication:

```bash
python3 main.py --config config.yaml --use-sync
```

This method copies files directly to a Photos library directory instead of using the iCloud API.

