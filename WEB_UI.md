# Web UI Guide

The Google Photos to iCloud Migration tool now includes a modern web-based user interface built with Flask and Tailwind CSS.

## Features

- **Modern, responsive design** using Tailwind CSS
- **Real-time progress updates** via WebSocket connections
- **Live statistics** showing migration progress
- **Activity logs** with real-time streaming
- **Configuration management** through the web interface
- **Failed uploads tracking** and management

## Getting Started

### Prerequisites

Make sure you have all dependencies installed:

```bash
pip install -r requirements.txt
```

This will install Flask, Flask-SocketIO, and other web dependencies.

### Starting the Web Server

1. **Start the web server:**

```bash
python web_server.py
```

2. **Open your browser:**

Navigate to `http://localhost:5001` in your web browser.

> **Note:** Port 5001 is used instead of 5000 because macOS often uses port 5000 for AirPlay Receiver.

The web UI will automatically connect and display the current migration status.

## Using the Web UI

![Web UI Dashboard](docs/images/web-ui-dashboard.png)

*Main dashboard showing the migration interface*

### Dashboard Overview

The main dashboard shows:

- **Migration Status**: Current status badge (Idle, Running, Completed, Error)
- **Progress Bar**: Visual progress indicator with percentage
- **Statistics Cards**: Real-time statistics including:
  - Total ZIP files
  - Processed files
  - Media files found
  - Files uploaded
  - Albums identified
  - Failed uploads
  - Corrupted ZIPs
  - Elapsed time

### Starting a Migration

1. **Configure Settings:**
   - Enter the path to your `config.yaml` file
   - "Use PhotoKit Sync Method" is selected by default (recommended for macOS)
   - Click "Load Configuration" to verify settings

2. **Start Migration:**
   - Click the "Start Migration" button
   - The status will change to "Running"
   - Progress updates will appear in real-time

### Monitoring Progress

![Migration in Progress](docs/images/web-ui-running.png)

*Real-time progress tracking during migration*

- **Progress Bar**: Shows overall progress percentage
- **Activity Log**: Real-time log messages appear in the Activity Log panel
- **Statistics**: Update automatically as the migration progresses

### Stopping a Migration

- Click the "Stop Migration" button to gracefully stop the current migration
- The migration will complete the current operation before stopping

### Viewing and Retrying Failed Uploads

![Failed Uploads View](docs/images/web-ui-failed-uploads.png)

*Failed uploads list showing files that need retry*

- Click "View Failed Uploads" in the Quick Actions panel
- Failed uploads are displayed with file names, album information, and retry counts
- **Individual Retry**: Click the "Retry" button next to any failed upload to retry just that file
- **Retry All**: Click the "Retry All" button in the Failed Uploads header to retry all failed uploads at once
- The UI will show loading states and update automatically after retries complete

### Activity Log and Log Levels

The Activity Log shows detailed information about the migration process:

- **Log Level Selector**: Choose the verbosity level (DEBUG, INFO, WARNING, ERROR)
  - DEBUG: Most detailed, shows all log messages
  - INFO: Standard level, shows important information (default)
  - WARNING: Shows warnings and errors only
  - ERROR: Shows only errors
- You can change the log level at any time, even during migration
- Log entries include timestamps, logger names, and full context

### Paused for Retries

If any files fail to upload during migration:

- The migration will automatically pause before cleanup
- Downloaded zip files are preserved to allow retries
- A "Proceed with Cleanup" button will appear
- Use the retry buttons to retry failed uploads
- Once all retries are complete (or you're ready to proceed), click "Proceed with Cleanup"
- The migration will then complete cleanup and finish

### Configuration

The web UI allows you to:

- Load and view your current configuration
- Change configuration file path
- Toggle PhotoKit sync method (enabled by default)

## Architecture

### Backend (Flask)

- **`web/app.py`**: Main Flask application with API endpoints
- **WebSocket Support**: Real-time communication via Flask-SocketIO
- **Progress Tracking**: Integrates with MigrationOrchestrator for progress updates

### Frontend

- **`web/templates/index.html`**: Main HTML template with Tailwind CSS
- **`web/static/js/app.js`**: JavaScript for UI interactivity and WebSocket handling

### API Endpoints

- `GET /api/status` - Get current migration status
- `GET /api/config` - Get configuration
- `POST /api/config` - Save configuration
- `POST /api/migration/start` - Start migration
- `POST /api/migration/stop` - Stop migration
- `POST /api/migration/log-level` - Update log level
- `POST /api/migration/proceed-after-retries` - Proceed with cleanup after retries
- `GET /api/statistics` - Get migration statistics
- `GET /api/failed-uploads` - Get list of failed uploads
- `POST /api/failed-uploads/retry` - Retry all failed uploads
- `POST /api/failed-uploads/retry-single` - Retry a single failed upload

### WebSocket Events

- `status_update` - Migration status changes
- `progress_update` - Progress updates
- `statistics_update` - Statistics updates
- `log_message` - New log messages

## Troubleshooting

### Web Server Won't Start

- Ensure all dependencies are installed: `pip3 install -r requirements.txt`
- Use `pip3` instead of `pip` on macOS
- Check if port 5001 is already in use (try a different port if needed)
- Verify Python version is 3.11 or higher

### No Progress Updates

- Check browser console for WebSocket connection errors
- Ensure WebSocket connections are not blocked by firewall
- Verify the migration is actually running (check logs)

### Configuration Not Loading

- Verify the config file path is correct
- Check file permissions
- Ensure the config file is valid YAML

## Browser Compatibility

The web UI works best in modern browsers:

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Security Notes

- The web server runs on `127.0.0.1:5001` by default, making it accessible only from localhost
- For production use, consider:
  - Adding authentication
  - Using HTTPS
  - Restricting access with a firewall
  - Running behind a reverse proxy (nginx, Apache)

## Development

To modify the web UI:

1. **Backend changes**: Edit `web/app.py`
2. **Frontend HTML**: Edit `web/templates/index.html`
3. **Frontend JavaScript**: Edit `web/static/js/app.js`
4. **Styling**: Tailwind CSS is loaded via CDN - modify classes in HTML or add custom CSS

After making changes, restart the web server.

