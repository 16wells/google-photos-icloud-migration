# How to Set GitHub Repository Description and Topics

## Quick Steps (Web UI - Easiest Method)

### Step 1: Go to Your Repository
Navigate to: https://github.com/16wells/google-photos-icloud-migration

### Step 2: Find the "About" Section
- Look on the right side of the repository page
- You'll see an "About" section (usually below the "Releases" section)
- If you don't see it, scroll down a bit on the right sidebar

### Step 3: Click the Gear Icon
- Next to the "About" heading, there's a small ⚙️ gear/settings icon
- Click on it to edit

### Step 4: Enter Description
Copy and paste this description:
```
Migrate photos from Google Photos (Takeout) to iCloud Photos on macOS. Preserves metadata, albums, and includes a modern web UI with real-time progress tracking.
```

### Step 5: Add Topics
In the "Topics" field, add these one by one (press Enter after each):
- google-photos
- icloud-photos
- photo-migration
- macos
- python
- photokit
- exiftool
- metadata-preservation
- google-takeout
- photo-sync
- album-migration
- web-ui
- flask
- socketio

### Step 6: Save
Click "Save changes" button

---

## Alternative: Using the Python Script (Automated)

If you prefer to automate it, you can use the script I created:

### Step 1: Create a GitHub Personal Access Token
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "Repo Description Updater"
4. Select the `repo` scope (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

### Step 2: Store Your Token (Recommended: Use .env file)

**Option A: Use .env file (Recommended - persists across sessions)**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your token
# GITHUB_TOKEN=your_actual_token_here
```

Then just run:
```bash
python3 scripts/set_github_repo_info.py
```

**Option B: Set environment variable (for current session only)**
```bash
export GITHUB_TOKEN=your_token_here
python3 scripts/set_github_repo_info.py
```

**Option C: Pass token directly**
```bash
python3 scripts/set_github_repo_info.py --token your_token_here
```

The script will automatically set both the description and all topics.

---

## Visual Guide

The "About" section looks like this on GitHub:

```
┌─────────────────────────────┐
│ About                       │ ⚙️  ← Click this gear icon
├─────────────────────────────┤
│ [No description]            │
│                             │
│ [Add topics]                │
└─────────────────────────────┘
```

After clicking the gear icon, you'll see:

```
┌─────────────────────────────┐
│ Edit repository details     │
├─────────────────────────────┤
│ Description:                │
│ [Text field - paste here]   │
│                             │
│ Topics:                     │
│ [Add topics - type & Enter] │
│                             │
│ [Cancel]  [Save changes]    │
└─────────────────────────────┘
```

---

## Troubleshooting

**Can't find the "About" section?**
- Make sure you're on the main repository page (not a subdirectory)
- Try refreshing the page
- The About section is always on the right sidebar, below the repository stats

**Description too long?**
Use this shorter version (120 chars):
```
macOS tool to migrate Google Photos to iCloud Photos with metadata preservation and modern web UI
```

**Topics not saving?**
- Make sure you press Enter after each topic
- Topics should appear as small pills/chips as you add them
- GitHub has a limit of 20 topics per repository

