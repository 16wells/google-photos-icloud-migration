# Screenshots Guide

This guide explains what screenshots are needed for the documentation and how to capture them.

## Required Screenshots

The following screenshots should be added to the `docs/images/` directory:

### 1. Web UI Dashboard (`web-ui-dashboard.png`)

**What to capture:**
- Full view of the main web UI dashboard
- Show the status badge (should show "Idle" or current status)
- Show all statistics cards (ZIP files, media files, albums, etc.)
- Show the progress bar section
- Show the configuration section
- Show the Activity Log panel

**When to capture:**
- When the web UI is first loaded (idle state)
- Make sure all UI elements are visible

**How to capture:**
1. Open `http://localhost:5001` in your browser
2. Use browser zoom to make sure everything fits on screen (80-90% zoom often works well)
3. Take a full-page screenshot (use browser dev tools or a screenshot tool)
4. Crop to show just the relevant UI (remove browser chrome if desired)
5. Save as `docs/images/web-ui-dashboard.png`

### 2. Migration Running (`web-ui-running.png`)

**What to capture:**
- Dashboard during an active migration
- Status badge showing "Running" with animated indicator
- Progress bar with percentage (e.g., "45%")
- Statistics updating (showing non-zero values)
- Activity log with recent log messages
- Progress message showing current phase

**When to capture:**
- After starting a migration and letting it run for a few seconds
- Should show active progress (not 0% or 100%)

**How to capture:**
1. Start a migration from the web UI
2. Wait until progress starts showing
3. Take a screenshot showing the active migration state
4. Save as `docs/images/web-ui-running.png`

### 3. Migration Completed (`web-ui-completed.png`)

**What to capture:**
- Status badge showing "Completed"
- Progress bar at 100%
- Final statistics (total files, albums, etc.)
- Activity log showing completion messages
- Success indicators

**When to capture:**
- After a migration completes successfully
- Or you can simulate by setting status to completed (for demo purposes)

**How to capture:**
1. Wait for a migration to complete, or stop after partial completion
2. Take a screenshot of the completed state
3. Save as `docs/images/web-ui-completed.png`

### 4. Failed Uploads View (`web-ui-failed-uploads.png`)

**What to capture:**
- The "Failed Uploads" sidebar panel
- List of failed uploads with file names
- Album information for failed files
- Retry counts (if any)

**When to capture:**
- When there are failed uploads to display
- Or capture the empty state ("No failed uploads")

**How to capture:**
1. Either have actual failed uploads, or capture the empty state
2. Click "View Failed Uploads" in Quick Actions
3. Take a screenshot of the failed uploads list
4. Save as `docs/images/web-ui-failed-uploads.png`

## Screenshot Specifications

### Technical Requirements

- **Format:** PNG (preferred) or JPEG
- **Size:** 1920x1080 or smaller (most screenshots will be much smaller)
- **Quality:** High quality, clear text, readable UI elements
- **Browser:** Chrome/Edge recommended for consistency

### Best Practices

1. **Use consistent browser zoom** - Use the same zoom level for all screenshots (80-90% works well)
2. **Remove personal information** - Blur or remove any personal data (emails, file paths, etc.)
3. **Keep UI elements visible** - Don't crop important UI elements
4. **Show realistic data** - Use sample data that makes sense (not all zeros)
5. **Consistent styling** - Use the same browser and theme for all screenshots

### Tools for Capturing

**macOS:**
- Built-in screenshot tool: `Cmd+Shift+4` (select area) or `Cmd+Shift+3` (full screen)
- Or use: `Cmd+Shift+4`, then press `Space` to capture a window

**Browser Extensions:**
- Full Page Screen Capture (Chrome)
- FireShot (Chrome/Firefox)
- Awesome Screenshot (Chrome/Firefox)

**Professional Tools:**
- Snagit
- CleanShot X
- Skitch

## Adding Screenshots to Documentation

Once screenshots are added to `docs/images/`, they're automatically referenced in the documentation:

- `WEB_UI.md` - References all screenshots
- README.md - Can reference screenshots if needed
- Other guides - Can reference screenshots as needed

The markdown image syntax is already in place:
```markdown
![Web UI Dashboard](docs/images/web-ui-dashboard.png)
```

## Alternative: Screenshot Placeholders

If you can't capture screenshots immediately, you can:

1. Use placeholder images (colored boxes with text)
2. Add a note in documentation: "Screenshots coming soon"
3. Use ASCII art or diagrams as temporary placeholders

But real screenshots are much better for user understanding!














