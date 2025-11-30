# Config Editor Feature - Release Notes

## New Features Added

### 1. **Expandable Config Editor** 
Located in the web interface at `http://localhost:5001`

#### Features:
- **Collapsible Section**: Click "▼ Edit Config" to expand, "▲ Hide Config" to collapse
- **Organized Categories**: Settings grouped into logical sections:
  - 🔵 **Google Drive**: Credentials file path
  - 🔵 **iCloud**: Apple ID and password
  - 🟢 **Processing**: Base directory, parallel limits, verification options
  - 🟡 **Logging**: Log level and file settings

### 2. **Password Visibility Toggle**
- 👁️ **Show/Hide Button**: Click the eye icon to toggle password visibility
- **Security**: Password hidden by default
- **Convenient**: No need to remember what you typed

### 3. **Live Configuration Editing**
- ✏️ **Edit Directly in UI**: No need to edit YAML files manually
- 💾 **Save Button**: Saves changes to `config.yaml`
- 🔄 **Reset Button**: Restore current saved values
- ⚠️ **Auto-notification**: Shows success/error messages

### 4. **Form Validation & Defaults**
- Number inputs for parallel operations (1-10)
- Checkboxes for boolean options
- Pre-filled with current configuration
- Tooltips and help text

## How to Use

### Step 1: Open Config Editor
1. Navigate to `http://localhost:5001`
2. Scroll to the "Configuration" card
3. Click **"▼ Edit Config"** button

### Step 2: Edit Settings
1. **Google Drive Section**:
   - Set path to your `credentials.json` file

2. **iCloud Section**:
   - Enter your Apple ID (email)
   - Enter your app-specific password
   - Click the 👁️ icon to show/hide password

3. **Processing Section**:
   - Set base directory for migration files
   - Adjust max parallel downloads (1-10)
   - Adjust max parallel uploads (1-10)
   - Toggle verification and cleanup options

4. **Logging Section**:
   - Choose log level (DEBUG, INFO, WARNING, ERROR)
   - Set log file name

### Step 3: Save Configuration
1. Click **"Save Configuration"** button
2. Wait for success notification
3. **Important**: Restart migration for changes to take effect

## Technical Details

### Files Modified
- `/web/templates/index.html` - Added HTML for config editor
- `/web/static/js/app.js` - Added JavaScript functions

### JavaScript Functions
- `toggleConfigEditor()` - Show/hide editor
- `togglePasswordVisibility()` - Toggle password field
- `loadConfigForEditing()` - Load current config into form
- `saveConfig()` - Save form data to config.yaml
- `showNotification()` - Display success/error messages

### API Endpoints Used
- `GET /api/config?config_path=config.yaml` - Load configuration
- `POST /api/config` - Save configuration

## Security Notes

### Password Handling
- ✅ Passwords hidden by default
- ✅ Toggle visibility only when needed
- ✅ config.yaml in .gitignore (not committed to Git)
- ⚠️ Config file stored as plain text locally

### Best Practices
1. **Use App-Specific Passwords**: Generate at appleid.apple.com
2. **Don't Share Screenshots**: Passwords may be visible
3. **Secure Your Mac**: Use FileVault and strong login password
4. **Regular Backups**: Keep config.yaml backed up securely

## Validation

### Required Fields
- All fields are validated before saving
- Empty fields use defaults from config schema
- Invalid numbers default to safe values (3 downloads, 5 uploads)

### Automatic Checks
- Base directory creation on save
- Credentials file existence check
- Valid email format for Apple ID
- Log level must be DEBUG/INFO/WARNING/ERROR

## Troubleshooting

### Config Won't Save
- Check that `config.yaml` is not read-only
- Ensure base directory path is valid
- Look for error messages in the notification

### Changes Not Taking Effect
- **Restart migration** - Stop and start migration for new settings
- **Check config.yaml** - Verify file was updated
- **Refresh page** - Reload browser if UI is stale

### Password Not Working
- Use **app-specific password**, not regular password
- Generate at: https://appleid.apple.com/
- Enable two-factor authentication first

## Examples

### Example 1: Change Base Directory
```
Before: /tmp/google-photos-migration
After:  /Users/skipshean/google-photos-migration
```
1. Click "Edit Config"
2. Find "Base Directory" field
3. Enter new path: `/Users/skipshean/google-photos-migration`
4. Click "Save Configuration"

### Example 2: Increase Upload Speed
```
Default: 5 parallel uploads
Fast:    8 parallel uploads
```
1. Click "Edit Config"
2. Find "Max Uploads" field
3. Change from 5 to 8
4. Click "Save Configuration"
5. Restart migration

### Example 3: Enable Debug Logging
```
Default: INFO
Debug:   DEBUG
```
1. Click "Edit Config"
2. Find "Log Level" dropdown
3. Select "DEBUG"
4. Click "Save Configuration"

## Future Enhancements

Potential improvements for next version:
- [ ] Real-time validation as you type
- [ ] Import/export config as JSON
- [ ] Multiple config file profiles
- [ ] Test connection buttons (Google Drive, iCloud)
- [ ] Encrypted password storage
- [ ] Config change history/undo

## Release Info

- **Version**: 1.0.0
- **Date**: 2025-11-29
- **Requires**: Web server restart
- **Compatible**: macOS 10.15+
- **Browser**: Chrome, Firefox, Safari, Edge

---

**Enjoy the new config editor!** 🎉

For issues or suggestions, see CONTRIBUTING.md or open a GitHub issue.

