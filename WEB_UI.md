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

Navigate to `http://localhost:5000` in your web browser.

The web UI will automatically connect and display the current migration status.

## Using the Web UI

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
   - Select "Use PhotoKit Sync Method" if desired (recommended for macOS)
   - Click "Load Configuration" to verify settings

2. **Start Migration:**
   - Click the "Start Migration" button
   - The status will change to "Running"
   - Progress updates will appear in real-time

### Monitoring Progress

- **Progress Bar**: Shows overall progress percentage
- **Activity Log**: Real-time log messages appear in the Activity Log panel
- **Statistics**: Update automatically as the migration progresses

### Stopping a Migration

- Click the "Stop Migration" button to gracefully stop the current migration
- The migration will complete the current operation before stopping

### Viewing Failed Uploads

- Click "View Failed Uploads" in the Quick Actions panel
- Failed uploads are displayed with file names, album information, and retry counts
- You can retry failed uploads using the CLI with `--retry-failed` flag

### Configuration

The web UI allows you to:

- Load and view your current configuration
- Change configuration file path
- Toggle PhotoKit sync method

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
- `GET /api/statistics` - Get migration statistics
- `GET /api/failed-uploads` - Get list of failed uploads

### WebSocket Events

- `status_update` - Migration status changes
- `progress_update` - Progress updates
- `statistics_update` - Statistics updates
- `log_message` - New log messages

## Troubleshooting

### Web Server Won't Start

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 5000 is already in use
- Verify Python version is 3.9 or higher

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

- The web server runs on `0.0.0.0:5000` by default, making it accessible from any network interface
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

