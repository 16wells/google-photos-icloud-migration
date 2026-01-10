# Web UI Directory (Deprecated)

⚠️ **This directory contains deprecated web UI code.**

The web UI was removed because it was unreliable for long-running migrations (timeouts, connection issues). The tool now runs **terminal-only** for better stability and reliability.

## Status

- **Current Status:** Deprecated / Not Maintained
- **Reason:** Terminal-only approach is more stable for long-running migrations
- **Last Updated:** See git history

## Contents

- `services/log_monitor.py` - Log file monitoring service (unused)
- `services/process_monitor.py` - Process monitoring service (unused)

## Recommendation

This directory can be safely removed if you don't plan to revive the web UI. The core functionality works entirely through terminal scripts:

- `scripts/process_local_zips.py` - Process local zip files
- `scripts/main.py` - Download from Google Drive and process

If you want to remove this directory:
```bash
rm -rf web/
```

