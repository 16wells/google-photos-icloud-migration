# Web Interface - Proof of Concept

This is a proof-of-concept web interface for the Google Photos to iCloud migration tool. It provides a simplified, user-friendly way to migrate photos without requiring command-line setup.

## Features

- **Web-based Google Drive authentication** - No need to download credentials.json
- **Web form for iCloud login** - Simple form-based authentication
- **Real-time progress dashboard** - See migration progress in real-time
- **One-click setup** - No terminal commands required

## Quick Start

### Option 1: Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements-web.txt
   ```

2. **Set environment variables:**
   ```bash
   export GOOGLE_CLIENT_ID="your-google-client-id"
   export GOOGLE_CLIENT_SECRET="your-google-client-secret"
   export GOOGLE_REDIRECT_URI="http://localhost:5000/auth/google/callback"
   export SECRET_KEY="your-secret-key-here"
   ```

3. **Run the application:**
   ```bash
   cd web
   python app.py
   ```

4. **Visit:** http://localhost:5000

### Option 2: Docker

1. **Create `.env` file:**
   ```bash
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
   SECRET_KEY=your-secret-key
   ```

2. **Run with Docker Compose:**
   ```bash
   cd docker
   docker-compose up
   ```

3. **Visit:** http://localhost:5000

## Setup Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing
3. Enable Google Drive API
4. Go to "APIs & Services" > "Credentials"
5. Click "Create Credentials" > "OAuth client ID"
6. Choose "Web application"
7. Add authorized redirect URI: `http://localhost:5000/auth/google/callback`
8. Copy Client ID and Client Secret
9. Set as environment variables (see above)

## Current Limitations (POC)

- Session storage is file-based (use Redis/database in production)
- iCloud credentials stored in session (should be encrypted)
- Background tasks run in threads (use Celery/Redis in production)
- No user accounts/multi-user support
- Status tracking is basic (file-based)

## Production Considerations

Before deploying to production:

1. **Use HTTPS** - Set `SESSION_COOKIE_SECURE = True`
2. **Encrypt iCloud credentials** - Use cryptography library
3. **Use Redis/database** - For session and status storage
4. **Use Celery** - For background task processing
5. **Add authentication** - User accounts/login system
6. **Add error recovery** - Resume capability
7. **Add logging** - Proper logging system
8. **Add monitoring** - Health checks and metrics

## Architecture

```
User Browser
    ↓
Flask Web App (web/app.py)
    ↓
Routes (web/routes/)
    ├── auth.py (Google/iCloud authentication)
    ├── migration.py (Start/stop migration)
    └── status.py (Progress updates)
    ↓
Services (web/services/)
    └── migration_worker.py (Background worker)
    ↓
Core Modules (existing)
    ├── drive_downloader.py
    ├── extractor.py
    ├── metadata_merger.py
    └── icloud_uploader.py
```

## Development

To extend the POC:

1. Add more robust error handling
2. Implement proper status tracking (Redis)
3. Add resume capability
4. Improve UI/UX
5. Add folder picker UI
6. Add batch processing controls
7. Add email notifications

## Notes

This is a proof of concept. For production use, significant improvements are needed in:
- Security (encryption, HTTPS, secure storage)
- Scalability (background jobs, database)
- User experience (better UI, error messages)
- Reliability (error recovery, retries)

