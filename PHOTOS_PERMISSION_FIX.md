# Fixing Photos Permission Issues on macOS

## The Problem

macOS sometimes doesn't show permission dialogs when running Python scripts from Terminal. This is a known limitation of macOS's TCC (Transparency, Consent, and Control) system.

## Solution 1: Manual Permission Grant (Recommended)

1. **Open System Settings**
   - Click the Apple menu → System Settings
   - Or run: `open "x-apple.systempreferences:com.apple.preference.security?Privacy_Photos"`

2. **Navigate to Photos Privacy**
   - Go to: **Privacy & Security** → **Photos**

3. **Add Terminal or Python**
   - Look for "Terminal" or "Python" in the list
   - If not listed:
     - Click the **"+"** button (if available) to add Terminal
     - Or use Solution 2 below

4. **Enable Permission**
   - Check the box next to Terminal/Python
   - Select **"Add Photos Only"** (sufficient) or **"Read and Write"**

## Solution 2: Reset Permissions

If Terminal/Python doesn't appear in the list:

```bash
# Reset Photos permissions (requires password)
sudo tccutil reset Photos

# Then run the permission helper
python3 request_photos_permission.py
```

## Solution 3: Use Python Directly

Instead of granting permission to Terminal, grant it to Python:

1. Find your Python path:
   ```bash
   which python3
   ```

2. In System Settings > Privacy & Security > Photos:
   - Look for "Python" (may show as the full path)
   - Enable "Add Photos Only" permission

3. Run migration with full Python path:
   ```bash
   /usr/bin/python3 process_local_zips.py --use-sync /path/to/zips
   ```

## Solution 4: Create App Bundle (Advanced)

If none of the above work, you can create a proper macOS app bundle:

1. Run the helper script:
   ```bash
   ./grant_photos_permission.sh
   ```

2. This creates a temporary app that requests permission
3. Grant permission to the app when prompted
4. The app will appear in System Settings > Privacy & Security > Photos

## Verification

After granting permission, verify it worked:

```bash
python3 request_photos_permission.py
```

You should see: "✓ Photo library permission already granted!"

## Troubleshooting

### "No apps listed in Photos privacy settings"

This means no app has requested Photos permission yet. Try:
1. Run `python3 request_photos_permission.py`
2. If no dialog appears, use Solution 2 (reset permissions)
3. Or manually add Terminal using Solution 1

### "Permission denied" error

1. Check System Settings > Privacy & Security > Photos
2. Make sure Terminal/Python has permission enabled
3. Try resetting: `sudo tccutil reset Photos`
4. Re-run the permission request

### "Permission dialog never appears"

This is common with Terminal scripts. Use Solution 1 (manual grant) instead.

## Why This Happens

macOS's TCC system requires:
- Apps to be properly signed
- Info.plist with usage descriptions
- User interaction to grant permission

Terminal scripts don't always meet these requirements, so macOS may not show the permission dialog. The manual grant method (Solution 1) is the most reliable workaround.

