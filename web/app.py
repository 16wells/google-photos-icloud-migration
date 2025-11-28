"""
Flask web application for Google Photos to iCloud Photos Migration Tool.
Provides a modern web UI with real-time progress updates.
"""
import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import yaml

from google_photos_icloud_migration.cli.main import MigrationOrchestrator, MigrationStoppedException
from google_photos_icloud_migration.exceptions import ConfigurationError, CorruptedZipException

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global state
migration_state = {
    'status': 'idle',  # idle, running, paused, stopped, error, completed
    'progress': {
        'phase': None,
        'current': 0,
        'total': 0,
        'percentage': 0,
        'message': '',
        'current_activity': None,  # Current operation happening now
        'last_update_time': None
    },
            'statistics': {
                'zip_files_total': 0,
                'zip_files_processed': 0,
                'media_files_found': 0,
                'media_files_uploaded': 0,
                'media_files_awaiting_upload': 0,
                'albums_identified': 0,
                'failed_uploads': 0,
                'corrupted_zips': 0,
                'start_time': None,
                'elapsed_time': 0
            },
    'error': None,
    'orchestrator': None,
    'stop_requested': False,
    'thread': None,
    'log_level': 'DEBUG',
    'web_handler': None,
    'proceed_after_retries': False,
    'paused_for_retries': False,
    'corrupted_zip_redownloaded': False,
    'waiting_for_corrupted_zip_redownload': False,
    'skip_corrupted_zip': False
}


def emit_progress_update():
    """Emit progress update to all connected clients."""
    socketio.emit('progress_update', migration_state['progress'])
    socketio.emit('statistics_update', migration_state['statistics'])


def emit_status_update():
    """Emit status update to all connected clients."""
    socketio.emit('status_update', {
        'status': migration_state['status'],
        'error': migration_state['error'],
        'log_level': migration_state.get('log_level', 'DEBUG'),
        'paused_for_retries': migration_state.get('paused_for_retries', False)
    })


class TerminalStreamCapture:
    """Captures stdout/stderr and streams to WebSocket clients."""
    
    def __init__(self, original_stream, stream_name='stdout'):
        self.original_stream = original_stream
        self.stream_name = stream_name
        self.lock = threading.Lock()
    
    def write(self, data):
        """Write to original stream and emit via WebSocket."""
        # Write to original stream (so it still appears in console)
        with self.lock:
            self.original_stream.write(data)
            self.original_stream.flush()
            
            # Emit to WebSocket clients
            try:
                socketio.emit('terminal_output', {
                    'data': data,
                    'stream': self.stream_name,
                    'timestamp': time.time()
                })
            except Exception:
                pass  # Don't break if WebSocket fails
    
    def flush(self):
        """Flush the original stream."""
        self.original_stream.flush()
    
    def isatty(self):
        """Return True to make tqdm and other tools think this is a terminal."""
        # This makes tqdm output progress bars with ANSI codes
        return True
    
    def __getattr__(self, name):
        """Delegate other attributes to original stream."""
        return getattr(self.original_stream, name)


class WebProgressLogger(logging.Handler):
    """Custom logging handler that sends log messages to web clients."""
    
    def emit(self, record):
        """Emit a log record."""
        try:
            log_entry = {
                'level': record.levelname,
                'message': self.format(record),
                'timestamp': time.time()
            }
            socketio.emit('log_message', log_entry)
        except Exception:
            pass  # Don't break logging if WebSocket fails


def update_progress_from_log(message: str):
    """Parse progress information from log messages and update state."""
    import time
    current_time = time.time()
    
    # Ensure status is 'running' when we see activity
    if migration_state['status'] == 'idle' and any(keyword in message for keyword in [
        'Processing zip', 'Extracting', 'Processing metadata', 'Uploading', 'Downloading',
        'Found', 'Processing batch', 'Identified', 'Listing zip files'
    ]):
        migration_state['status'] = 'running'
        emit_status_update()
    
    # Track current activity from log messages
    current_activity = None
    if 'Extracting' in message and 'to' in message:
        current_activity = 'Unzipping files (this can take several minutes for large archives)'
    elif 'Processing metadata batch' in message or 'Processing metadata' in message:
        current_activity = 'Processing metadata and applying timestamps'
    elif 'Uploading album' in message or 'Uploading to iCloud' in message:
        current_activity = 'Uploading files to iCloud Photos'
    elif 'Processing zip' in message:
        current_activity = 'Processing ZIP file (extract → metadata → upload → cleanup)'
    elif 'Downloading zip' in message:
        current_activity = 'Downloading ZIP file from Google Drive'
    elif 'Found' in message and 'media files' in message:
        current_activity = 'Scanning for photos and videos'
    elif 'Identified' in message and 'albums' in message:
        current_activity = 'Organizing photos into albums'
    elif 'Listing zip files' in message:
        current_activity = 'Discovering ZIP files to process'
    
    if current_activity:
        migration_state['progress']['current_activity'] = current_activity
        migration_state['progress']['last_update_time'] = current_time
    
    # Extract statistics from log messages
    
    # "Found X zip files total to process" or "Found X zip files total"
    zip_total_match = re.search(r'Found (\d+) zip files? (?:total to process|total|to process)', message, re.IGNORECASE)
    if zip_total_match:
        total = int(zip_total_match.group(1))
        migration_state['statistics']['zip_files_total'] = total
        emit_progress_update()
    
    # "Found X media files in this zip" or "Found X media files to process"
    # Note: This is cumulative - each zip adds to the total
    media_found_match = re.search(r'Found (\d+) media files?', message, re.IGNORECASE)
    if media_found_match:
        found = int(media_found_match.group(1))
        current_found = migration_state['statistics'].get('media_files_found', 0)
        migration_state['statistics']['media_files_found'] = current_found + found
        emit_progress_update()
    
    # "Identified X albums" or "Found X albums"
    albums_match = re.search(r'(?:Identified|Found) (\d+) albums?', message, re.IGNORECASE)
    if albums_match:
        albums = int(albums_match.group(1))
        migration_state['statistics']['albums_identified'] = albums
        emit_progress_update()
    
    # Track uploaded files - look for "Uploaded" or "successfully uploaded"
    uploaded_match = re.search(r'(?:Uploaded|uploaded) (\d+)(?: files?| photos?| videos?)', message, re.IGNORECASE)
    if uploaded_match and 'successfully' in message.lower():
        uploaded = int(uploaded_match.group(1))
        current_uploaded = migration_state['statistics'].get('media_files_uploaded', 0)
        # Only update if this is a new higher number (avoid double-counting)
        if uploaded > current_uploaded:
            migration_state['statistics']['media_files_uploaded'] = uploaded
            emit_progress_update()
    
    # Try to extract progress information from log messages
    # Example: "Processing zip 5/10: filename.zip"
    zip_progress = re.search(r'Processing zip (\d+)/(\d+)', message)
    if zip_progress:
        current = int(zip_progress.group(1))
        total = int(zip_progress.group(2))
        migration_state['progress'] = {
            'phase': 'Processing ZIP Files',
            'current': current,
            'total': total,
            'percentage': int((current / total * 100)) if total > 0 else 0,
            'message': message,
            'current_activity': migration_state['progress'].get('current_activity', current_activity),
            'last_update_time': current_time
        }
        migration_state['statistics']['zip_files_processed'] = current
        migration_state['statistics']['zip_files_total'] = total
        emit_progress_update()
        emit_progress_update()  # Also emit statistics
        return
    
    # "Processing existing zip X/Y: filename.zip"
    existing_zip_progress = re.search(r'Processing existing zip (\d+)/(\d+)', message)
    if existing_zip_progress:
        current = int(existing_zip_progress.group(1))
        total = int(existing_zip_progress.group(2))
        migration_state['progress'] = {
            'phase': 'Processing ZIP Files',
            'current': current,
            'total': total,
            'percentage': int((current / total * 100)) if total > 0 else 0,
            'message': message,
            'current_activity': migration_state['progress'].get('current_activity', current_activity),
            'last_update_time': current_time
        }
        migration_state['statistics']['zip_files_processed'] = current
        migration_state['statistics']['zip_files_total'] = total
        emit_progress_update()
        return
    
    # "Downloading zip X/Y: filename.zip"
    downloading_zip_progress = re.search(r'Downloading zip (\d+)/(\d+)', message)
    if downloading_zip_progress:
        current = int(downloading_zip_progress.group(1))
        total = int(downloading_zip_progress.group(2))
        migration_state['progress'] = {
            'phase': 'Downloading ZIP Files',
            'current': current,
            'total': total,
            'percentage': int((current / total * 100)) if total > 0 else 0,
            'message': message,
            'current_activity': migration_state['progress'].get('current_activity', current_activity),
            'last_update_time': current_time
        }
        migration_state['statistics']['zip_files_total'] = total
        emit_progress_update()
        return
    
    # Example: "Uploaded 150/200 files"
    upload_progress = re.search(r'Uploaded (\d+)/(\d+) files?', message)
    if upload_progress:
        current = int(upload_progress.group(1))
        total = int(upload_progress.group(2))
        migration_state['progress'] = {
            'phase': 'Uploading to iCloud',
            'current': current,
            'total': total,
            'percentage': int((current / total * 100)) if total > 0 else 0,
            'message': message,
            'current_activity': migration_state['progress'].get('current_activity', current_activity),
            'last_update_time': current_time
        }
        migration_state['statistics']['media_files_uploaded'] = current
        emit_progress_update()
        return
    
    # Update phase from log message
    if 'Phase 1' in message or ('Downloading' in message and 'zip' in message.lower()):
        migration_state['progress']['phase'] = 'Downloading ZIP Files'
        migration_state['progress']['last_update_time'] = current_time
        emit_progress_update()
    elif 'Phase 2' in message or 'Extracting' in message:
        migration_state['progress']['phase'] = 'Extracting Files'
        migration_state['progress']['last_update_time'] = current_time
        emit_progress_update()
    elif 'Phase 3' in message or 'Processing metadata' in message:
        migration_state['progress']['phase'] = 'Processing Metadata'
        migration_state['progress']['last_update_time'] = current_time
        emit_progress_update()
    elif 'Phase 4' in message or 'Parsing album' in message:
        migration_state['progress']['phase'] = 'Parsing Albums'
        migration_state['progress']['last_update_time'] = current_time
        emit_progress_update()
    elif 'Phase 5' in message or ('Uploading' in message and 'iCloud' in message):
        migration_state['progress']['phase'] = 'Uploading to iCloud'
        migration_state['progress']['last_update_time'] = current_time
        emit_progress_update()


class WebProgressLogger(logging.Handler):
    """Custom logging handler that sends log messages to web clients."""
    
    def emit(self, record):
        """Emit a log record."""
        try:
            message = self.format(record)
            log_entry = {
                'level': record.levelname,
                'message': message,
                'timestamp': time.time()
            }
            socketio.emit('log_message', log_entry)
            
            # Try to extract progress information from log messages
            update_progress_from_log(message)
            
        except Exception:
            pass  # Don't break logging if WebSocket fails


def get_disk_space_info(path: Path) -> Dict[str, Any]:
    """
    Get disk space information for a given path.
    
    Args:
        path: Path to check disk space for
        
    Returns:
        Dictionary with disk space information
    """
    try:
        import shutil
        stat = shutil.disk_usage(path)
        
        total_gb = stat.total / (1024 ** 3)
        used_gb = (stat.total - stat.free) / (1024 ** 3)
        free_gb = stat.free / (1024 ** 3)
        used_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
        free_percent = (free_gb / total_gb * 100) if total_gb > 0 else 0
        
        return {
            'total_gb': round(total_gb, 2),
            'used_gb': round(used_gb, 2),
            'free_gb': round(free_gb, 2),
            'used_percent': round(used_percent, 1),
            'free_percent': round(free_percent, 1),
            'path': str(path),
            'status': 'low' if free_gb < 10 else 'ok' if free_gb < 50 else 'good'
        }
    except Exception as e:
        logger.warning(f"Error getting disk space info: {e}")
        return {
            'error': str(e),
            'status': 'error'
        }


def get_upload_tracking_count(orchestrator) -> int:
    """
    Get count of files already marked as uploaded in the tracking file.
    
    Returns:
        Number of files already uploaded (from tracking file)
    """
    if not orchestrator:
        return 0
    
    upload_tracking_file = None
    if hasattr(orchestrator, 'upload_tracking_file'):
        upload_tracking_file = orchestrator.upload_tracking_file
    elif hasattr(orchestrator, 'base_dir'):
        upload_tracking_file = orchestrator.base_dir / 'uploaded_files.json'
    
    if not upload_tracking_file or not upload_tracking_file.exists():
        return 0
    
    try:
        import json
        with open(upload_tracking_file, 'r') as f:
            tracking_data = json.load(f)
        # Count entries in tracking file (could be dict or list)
        if isinstance(tracking_data, dict):
            return len(tracking_data)
        elif isinstance(tracking_data, list):
            return len(tracking_data)
        return 0
    except Exception as e:
        logger.debug(f"Could not read upload tracking file: {e}")
        return 0


def get_photos_library_sync_status(orchestrator) -> Dict[str, int]:
    """
    Check Photos library to get sync status.
    When using PhotoKit sync method, files are saved to Photos library
    which then syncs to iCloud. This function checks how many are still syncing.
    
    Returns:
        Dictionary with 'total_in_photos', 'synced_to_icloud', 'pending_sync' counts
    """
    if not orchestrator:
        return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}
    
    # Check if using PhotoKit sync method
    if not hasattr(orchestrator, 'icloud_uploader'):
        return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}
    
    uploader = orchestrator.icloud_uploader
    uploader_class_name = type(uploader).__name__
    
    # Only check Photos library if using sync method
    if uploader_class_name != 'iCloudPhotosSyncUploader':
        return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}
    
    try:
        # Try to query Photos library for assets
        import platform
        if platform.system() != 'Darwin':
            return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}
        
        # Use PhotoKit to query recent assets
        # Note: PhotoKit doesn't directly expose iCloud sync status, but we can
        # count assets created recently (within last 24 hours) as potentially pending sync
        from Photos import PHAsset, PHFetchOptions, PHImageManager
        from Foundation import NSDate
        
        fetch_options = PHFetchOptions.alloc().init()
        # Fetch assets created in the last 24 hours (likely from our migration)
        # We'll use a simpler approach: count from upload tracking file
        # and note that Photos will show sync status in the UI
        
        # For now, return counts based on upload tracking file
        # The actual sync status is shown in Photos app itself
        uploaded_count = get_upload_tracking_count(orchestrator)
        
        # Note: We can't directly query iCloud sync status via PhotoKit
        # Photos app shows this info, but it's not easily accessible via API
        # The "awaiting upload" should be: files not yet in Photos library
        # Files "syncing" are already in Photos but not yet in iCloud
        
        return {
            'total_in_photos': uploaded_count,  # Best estimate
            'synced_to_icloud': 0,  # Can't determine directly
            'pending_sync': 0  # Can't determine directly - Photos app shows this
        }
    except ImportError:
        # PhotoKit not available
        return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}
    except Exception as e:
        logger.debug(f"Could not check Photos library sync status: {e}")
        return {'total_in_photos': 0, 'synced_to_icloud': 0, 'pending_sync': 0}


def monitor_statistics(orchestrator):
    """Monitor orchestrator statistics and update state periodically."""
    # Initialize last disk update time
    if not hasattr(monitor_statistics, '_last_disk_update'):
        monitor_statistics._last_disk_update = 0
    
    # Monitor while migration is running, paused, or thread is still alive
    # This ensures we keep statistics updated even if status changes
    # Also continue monitoring briefly after thread ends to catch final statistics
    max_iterations_after_thread_end = 5  # Check 5 more times (10 seconds) after thread ends
    iterations_after_thread_end = 0
    
    while (migration_state['status'] in ['running', 'paused'] or 
           migration_state.get('thread') is not None or 
           iterations_after_thread_end < max_iterations_after_thread_end) and not migration_state['stop_requested']:
        
        # Track iterations after thread ends
        if migration_state.get('thread') is None:
            iterations_after_thread_end += 1
        else:
            iterations_after_thread_end = 0  # Reset if thread restarts
        try:
            if orchestrator and hasattr(orchestrator, 'statistics'):
                stats = orchestrator.statistics
                
                # Update statistics from orchestrator - always update, even if value is 0
                # This ensures the UI shows accurate counts as they change
                if hasattr(stats, 'zip_files_total'):
                    migration_state['statistics']['zip_files_total'] = stats.zip_files_total
                if hasattr(stats, 'zip_files_processed_successfully'):
                    migration_state['statistics']['zip_files_processed'] = stats.zip_files_processed_successfully
                if hasattr(stats, 'media_files_found'):
                    migration_state['statistics']['media_files_found'] = stats.media_files_found
                if hasattr(stats, 'files_uploaded_successfully'):
                    migration_state['statistics']['media_files_uploaded'] = stats.files_uploaded_successfully
                if hasattr(stats, 'albums_identified'):
                    migration_state['statistics']['albums_identified'] = stats.albums_identified
                if hasattr(stats, 'files_upload_failed'):
                    migration_state['statistics']['failed_uploads'] = stats.files_upload_failed
                if hasattr(stats, 'zip_files_corrupted'):
                    migration_state['statistics']['corrupted_zips'] = stats.zip_files_corrupted
            
            # Get count of files already uploaded (from tracking file)
            already_uploaded_count = get_upload_tracking_count(orchestrator)
            
            # Calculate files awaiting upload more accurately
            # This accounts for:
            # - Files found in current session
            # - Files uploaded in current session  
            # - Files already uploaded from previous sessions (in tracking file)
            # - Files that failed to upload
            media_found = migration_state['statistics'].get('media_files_found', 0)
            media_uploaded_this_session = migration_state['statistics'].get('media_files_uploaded', 0)
            failed_uploads = migration_state['statistics'].get('failed_uploads', 0)
            
            # Total uploaded = this session + previously uploaded (from tracking file)
            total_uploaded = media_uploaded_this_session + already_uploaded_count
            
            # Update the displayed uploaded count to show total
            if already_uploaded_count > 0:
                migration_state['statistics']['media_files_uploaded_total'] = total_uploaded
                migration_state['statistics']['media_files_uploaded_this_session'] = media_uploaded_this_session
                migration_state['statistics']['media_files_uploaded_previous'] = already_uploaded_count
            
            # Awaiting = found - total_uploaded - failed
            # But we should only count files found in THIS session, not previous
            # Actually, media_files_found is cumulative across all processed zips
            # So: awaiting = (found - already_uploaded) - uploaded_this_session - failed
            awaiting = max(0, media_found - total_uploaded - failed_uploads)
            migration_state['statistics']['media_files_awaiting_upload'] = awaiting
            
            # Update elapsed time
            start_time = migration_state['statistics'].get('start_time')
            if start_time:
                elapsed = time.time() - start_time
                migration_state['statistics']['elapsed_time'] = elapsed
            
            # Check if we're still actively processing (heartbeat mechanism)
            # If last update was recent, keep status as running
            last_update = migration_state['progress'].get('last_update_time')
            if last_update:
                time_since_update = time.time() - last_update
                # If we haven't seen activity in 30 seconds, but thread is still running,
                # add a "working" indicator
                if time_since_update > 30 and time_since_update < 120:
                    if not migration_state['progress'].get('current_activity'):
                        migration_state['progress']['current_activity'] = 'Processing... (long-running operation in progress)'
            
            # Update disk space every minute (60 seconds)
            # Check if we should update now (first time or 60+ seconds since last update)
            last_disk_update = getattr(monitor_statistics, '_last_disk_update', 0)
            current_time = time.time()
            if current_time - last_disk_update >= 60:
                if orchestrator and hasattr(orchestrator, 'base_dir') and orchestrator.base_dir:
                    disk_info = get_disk_space_info(orchestrator.base_dir)
                    migration_state['statistics']['disk_space'] = disk_info
                    socketio.emit('disk_space_update', disk_info)
                monitor_statistics._last_disk_update = current_time
            
            # Always emit progress update to keep UI updated, even during long operations
            # This ensures the UI reflects current state even if statistics haven't changed
            emit_progress_update()
            
            time.sleep(1)  # Update every 1 second for more responsive UI
        except Exception as e:
            logger.warning(f"Error monitoring statistics: {e}")
            time.sleep(5)  # Wait longer on error
        # Continue monitoring even if thread is not "running" - check if thread still exists
        if migration_state.get('thread') is None:
            # Thread ended, stop monitoring
            logger.debug("Migration thread ended, stopping statistics monitoring")
            break


def run_migration(config_path: str, use_sync_method: bool = False, log_level: str = 'DEBUG'):
    """
    Run migration in a separate thread.
    
    Args:
        config_path: Path to configuration file
        use_sync_method: Whether to use PhotoKit sync method
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    stats_thread = None
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    stdout_capture = None
    stderr_capture = None
    
    try:
        # Capture stdout/stderr for terminal display
        stdout_capture = TerminalStreamCapture(original_stdout, 'stdout')
        stderr_capture = TerminalStreamCapture(original_stderr, 'stderr')
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migration_state['status'] = 'running'
        migration_state['error'] = None
        migration_state['statistics']['start_time'] = time.time()
        migration_state['log_level'] = log_level
        emit_status_update()
        
        # Create orchestrator
        orchestrator = MigrationOrchestrator(config_path)
        migration_state['orchestrator'] = orchestrator
        
        # Set up custom logging handler for web UI
        web_handler = WebProgressLogger()
        # Convert string log level to logging constant
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        log_level_constant = level_map.get(log_level.upper(), logging.DEBUG)
        web_handler.setLevel(log_level_constant)
        # Include timestamp, logger name, and level for better context
        web_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        web_logger = logging.getLogger()
        web_logger.addHandler(web_handler)
        migration_state['web_handler'] = web_handler
        
        # Start statistics monitoring thread AFTER orchestrator is created
        # This ensures the orchestrator is available immediately for monitoring
        stats_thread = threading.Thread(
            target=monitor_statistics,
            args=(orchestrator,),
            daemon=True
        )
        stats_thread.start()
        
        # Give monitoring thread a moment to start before migration begins
        time.sleep(0.5)
        
        if migration_state['stop_requested']:
            migration_state['status'] = 'stopped'
            emit_status_update()
            return
        
        # Run migration in a thread-safe way
        # The orchestrator will pause if there are failed uploads
        orchestrator.run(use_sync_method=use_sync_method, retry_failed=False)
        
        # Check if migration paused for retries (set by orchestrator)
        if migration_state.get('paused_for_retries', False):
            migration_state['status'] = 'paused'
            emit_status_update()
            # Wait for proceed signal
            while not migration_state.get('proceed_after_retries', False):
                if migration_state.get('stop_requested', False):
                    migration_state['status'] = 'stopped'
                    orchestrator._stop_requested = True
                    emit_status_update()
                    return
                time.sleep(1)
            # Signal orchestrator to proceed
            orchestrator._proceed_after_retries = True
            migration_state['proceed_after_retries'] = False
            migration_state['paused_for_retries'] = False
            migration_state['status'] = 'running'
            emit_status_update()
            # Continue with cleanup (orchestrator will handle this)
            orchestrator._do_final_cleanup()
        
        migration_state['status'] = 'completed'
        if migration_state['statistics']['start_time']:
            migration_state['statistics']['elapsed_time'] = time.time() - migration_state['statistics']['start_time']
        emit_status_update()
        
    except CorruptedZipException as e:
        # Corrupted zip detected - pause migration and show modal
        migration_state['status'] = 'paused'
        migration_state['error'] = f"Corrupted zip file detected: {e.zip_path}"
        emit_status_update()
        # Emit socket event for frontend modal
        socketio.emit('corrupted_zip_detected', {
            'zip_path': e.zip_path,
            'file_name': e.file_info.get('name', Path(e.zip_path).name),
            'file_id': e.file_info.get('id', 'unknown'),
            'file_size_mb': e.file_size_mb,
            'error_message': str(e)
        })
        logger.error(f"Migration paused due to corrupted zip file: {e.zip_path}")
    except MigrationStoppedException:
        migration_state['status'] = 'stopped'
        emit_status_update()
    except Exception as e:
        logger.exception("Migration failed")
        migration_state['status'] = 'error'
        migration_state['error'] = str(e)
        emit_status_update()
    finally:
        # Restore original stdout/stderr
        if stdout_capture:
            sys.stdout = original_stdout
        if stderr_capture:
            sys.stderr = original_stderr
        
        # Don't reset statistics when thread ends - preserve them
        # Only reset thread tracking, not the statistics
        migration_state['thread'] = None
        migration_state['stop_requested'] = False
        
        # Only reset status to idle if it wasn't already set to completed/error/stopped
        if migration_state['status'] not in ['completed', 'error', 'stopped', 'paused']:
            # If we get here, something unexpected happened
            logger.warning("Migration thread ended unexpectedly. Status was: " + migration_state['status'])
            # Keep the status as-is, don't change to idle automatically
        
        # Clean up logging handler
        web_logger = logging.getLogger()
        for handler in web_logger.handlers[:]:
            if isinstance(handler, WebProgressLogger):
                web_logger.removeHandler(handler)
        
        migration_state['web_handler'] = None


@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    config_path = request.args.get('config_path', 'config.yaml')
    config_file = Path(config_path)
    
    if not config_file.exists():
        return jsonify({'error': 'Configuration file not found'}), 404
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration."""
    config_path = request.json.get('config_path', 'config.yaml')
    config_data = request.json.get('config', {})
    
    try:
        config_file = Path(config_path)
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        return jsonify({'success': True, 'message': 'Configuration saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current migration status."""
    # Update disk space if orchestrator is available
    disk_space_info = migration_state['statistics'].get('disk_space')
    if not disk_space_info and migration_state.get('orchestrator'):
        orchestrator = migration_state['orchestrator']
        if hasattr(orchestrator, 'base_dir') and orchestrator.base_dir:
            disk_space_info = get_disk_space_info(orchestrator.base_dir)
            migration_state['statistics']['disk_space'] = disk_space_info
    
    # Ensure progress includes all fields
    progress = migration_state.get('progress', {})
    if 'current_activity' not in progress:
        progress['current_activity'] = None
    if 'last_update_time' not in progress:
        progress['last_update_time'] = None
    
    return jsonify({
        'status': migration_state['status'],
        'progress': progress,
        'statistics': migration_state['statistics'],
        'error': migration_state['error'],
        'log_level': migration_state.get('log_level', 'DEBUG'),
        'paused_for_retries': migration_state.get('paused_for_retries', False)
    })


@app.route('/api/disk-space', methods=['GET'])
def get_disk_space():
    """Get disk space information."""
    config_path = request.args.get('config_path', 'config.yaml')
    base_dir = request.args.get('base_dir', None)
    
    # Try to get base_dir from config or orchestrator
    if not base_dir:
        if migration_state.get('orchestrator') and hasattr(migration_state['orchestrator'], 'base_dir'):
            base_dir = str(migration_state['orchestrator'].base_dir)
        else:
            # Try to load from config file
            try:
                config_file = Path(config_path)
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                    base_dir = config.get('processing', {}).get('base_dir')
            except Exception as e:
                logger.warning(f"Could not load config to get base_dir: {e}")
    
    if not base_dir:
        # Default to checking current directory
        base_dir = '.'
    
    disk_info = get_disk_space_info(Path(base_dir))
    
    # Update migration state if orchestrator is available
    if migration_state.get('orchestrator'):
        migration_state['statistics']['disk_space'] = disk_info
    
    return jsonify(disk_info)


@app.route('/api/migration/start', methods=['POST'])
def start_migration():
    """Start migration."""
    if migration_state['status'] == 'running':
        return jsonify({'error': 'Migration is already running'}), 400
    
    data = request.json or {}
    config_path = data.get('config_path', 'config.yaml')
    use_sync_method = data.get('use_sync_method', False)
    log_level = data.get('log_level', 'DEBUG')
    
    if not Path(config_path).exists():
        return jsonify({'error': f'Configuration file not found: {config_path}'}), 404
    
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if log_level.upper() not in valid_levels:
        return jsonify({'error': f'Invalid log level: {log_level}. Must be one of {valid_levels}'}), 400
    
    # Reset state
    migration_state['status'] = 'idle'
    migration_state['error'] = None
    migration_state['stop_requested'] = False
    migration_state['log_level'] = log_level.upper()
    migration_state['progress'] = {
        'phase': None,
        'current': 0,
        'total': 0,
        'percentage': 0,
        'message': '',
        'current_activity': None,
        'last_update_time': None
    }
    migration_state['statistics'] = {
        'zip_files_total': 0,
        'zip_files_processed': 0,
        'media_files_found': 0,
        'media_files_uploaded': 0,
        'media_files_awaiting_upload': 0,
        'albums_identified': 0,
        'failed_uploads': 0,
        'corrupted_zips': 0,
        'start_time': None,
        'elapsed_time': 0
    }
    
    # Start migration in background thread
    thread = threading.Thread(
        target=run_migration,
        args=(config_path, use_sync_method, log_level.upper()),
        daemon=True
    )
    thread.start()
    migration_state['thread'] = thread
    
    return jsonify({'success': True, 'message': 'Migration started'})


@app.route('/api/migration/stop', methods=['POST'])
def stop_migration():
    """Stop migration."""
    if migration_state['status'] != 'running':
        return jsonify({'error': 'No migration is currently running'}), 400
    
    migration_state['stop_requested'] = True
    if migration_state['orchestrator']:
        # Signal orchestrator to stop
        pass  # The orchestrator will check stop_requested flag
    
    return jsonify({'success': True, 'message': 'Stop request sent'})


@app.route('/api/migration/log-level', methods=['POST'])
def update_log_level():
    """Update log level for web UI logging."""
    data = request.json or {}
    log_level = data.get('log_level', 'DEBUG')
    
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    if log_level.upper() not in valid_levels:
        return jsonify({'error': f'Invalid log level: {log_level}. Must be one of {valid_levels}'}), 400
    
    # Update log level in state
    migration_state['log_level'] = log_level.upper()
    
    # Update handler level if it exists
    if migration_state['web_handler']:
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        log_level_constant = level_map.get(log_level.upper(), logging.DEBUG)
        migration_state['web_handler'].setLevel(log_level_constant)
        logger.info(f"Log level updated to {log_level.upper()}")
    
    return jsonify({'success': True, 'message': f'Log level updated to {log_level.upper()}'})


@app.route('/api/migration/proceed-after-retries', methods=['POST'])
def proceed_after_retries():
    """Signal to proceed with cleanup after retrying failed uploads."""
    if migration_state['status'] != 'paused':
        return jsonify({'error': 'Migration is not paused for retries'}), 400
    
    migration_state['proceed_after_retries'] = True
    logger.info("Proceed signal received - continuing with cleanup")
    
    return jsonify({'success': True, 'message': 'Proceeding with cleanup'})


@app.route('/api/server/status', methods=['GET'])
def get_server_status():
    """Get web server status and health information."""
    import os
    
    try:
        try:
            import psutil
            # Get current process info
            current_process = psutil.Process(os.getpid())
            process_info = {
                'pid': current_process.pid,
                'status': current_process.status(),
                'memory_mb': current_process.memory_info().rss / (1024 * 1024),
                'cpu_percent': current_process.cpu_percent(interval=0.1),
                'uptime_seconds': time.time() - current_process.create_time()
            }
        except ImportError:
            # psutil not available, provide basic info
            process_info = {
                'pid': os.getpid(),
                'status': 'running',
                'memory_mb': None,
                'cpu_percent': None,
                'uptime_seconds': None
            }
        
        # Check if migration is running
        migration_running = migration_state['status'] == 'running'
        
        return jsonify({
            'success': True,
            'server_status': 'running',
            'process_info': process_info,
            'migration_status': migration_state['status'],
            'migration_running': migration_running,
            'port': 5001
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({
            'success': False,
            'server_status': 'unknown',
            'error': str(e)
        }), 500


@app.route('/api/server/restart-instructions', methods=['GET'])
def get_restart_instructions():
    """Get instructions for restarting the web server."""
    import platform
    import sys
    
    # Detect the platform and Python command
    is_mac = platform.system() == 'Darwin'
    python_cmd = 'python3' if sys.executable.endswith('python3') else 'python'
    
    instructions = {
        'platform': platform.system(),
        'python_command': python_cmd,
        'steps': [
            {
                'step': 1,
                'title': 'Stop the current server',
                'description': 'In the terminal where the web server is running, press Ctrl+C (or Cmd+C on Mac)',
                'command': None
            },
            {
                'step': 2,
                'title': 'Restart the server',
                'description': 'Run the following command in your terminal:',
                'command': f'{python_cmd} web_server.py'
            },
            {
                'step': 3,
                'title': 'Refresh your browser',
                'description': 'Hard refresh your browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows/Linux)',
                'command': None
            }
        ],
        'alternative_method': {
            'title': 'Alternative: Restart via Terminal',
            'description': 'If you can\'t find the terminal window, you can restart from a new terminal:',
            'commands': [
                f'# Find and stop the web server process',
                f'pkill -f web_server.py',
                f'# Wait a moment, then restart',
                f'sleep 2',
                f'{python_cmd} web_server.py'
            ] if is_mac else [
                f'# Find and stop the web server process (Windows)',
                f'taskkill /F /IM python.exe /FI "WINDOWTITLE eq web_server.py*"',
                f'# Then restart:',
                f'{python_cmd} web_server.py'
            ]
        }
    }
    
    return jsonify(instructions)


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get migration statistics."""
    return jsonify(migration_state['statistics'])


@app.route('/api/corrupted-zip/skip', methods=['POST'])
def skip_corrupted_zip():
    """Skip a corrupted zip file and continue migration."""
    data = request.json or {}
    file_name = data.get('file_name')
    file_id = data.get('file_id')
    
    if not file_name:
        return jsonify({'success': False, 'error': 'file_name is required'}), 400
    
    # Set flag to skip the corrupted zip
    migration_state['skip_corrupted_zip'] = True
    migration_state['waiting_for_corrupted_zip_redownload'] = False
    migration_state['corrupted_zip_redownloaded'] = False
    
    logger.info(f"Skip requested for corrupted zip: {file_name}")
    
    # If migration is paused, resume it
    if migration_state['status'] == 'paused':
        migration_state['status'] = 'running'
        emit_status_update()
    
    return jsonify({
        'success': True,
        'message': f'Corrupted zip {file_name} will be skipped and migration will continue'
    })


@app.route('/api/failed-uploads', methods=['GET'])
def get_failed_uploads():
    """Get list of failed uploads."""
    if not migration_state['orchestrator']:
        return jsonify({'failed_uploads': []})
    
    base_dir = migration_state['orchestrator'].base_dir
    failed_uploads_file = base_dir / 'failed_uploads.json'
    
    if not failed_uploads_file.exists():
        return jsonify({'failed_uploads': []})
    
    try:
        with open(failed_uploads_file, 'r') as f:
            failed_data = json.load(f)
        return jsonify({'failed_uploads': list(failed_data.values())})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _retry_failed_uploads(files_to_retry: Optional[List[str]] = None, use_sync_method: bool = False, config_path: Optional[str] = None):
    """
    Retry failed uploads (all or specific files).
    
    Args:
        files_to_retry: List of file paths to retry (as strings). If None, retry all.
        use_sync_method: Whether to use Photos library sync method
        config_path: Path to config file (used if orchestrator not available)
    
    Returns:
        Dictionary with results
    """
    orchestrator = migration_state.get('orchestrator')
    
    # If no orchestrator, try to create one from config
    if not orchestrator:
        if not config_path:
            config_path = 'config.yaml'  # Default config path
        
        if not Path(config_path).exists():
            return {'error': 'No orchestrator available and config file not found. Please start a migration first or provide a config path.'}
        
        try:
            orchestrator = MigrationOrchestrator(config_path)
            migration_state['orchestrator'] = orchestrator
        except Exception as e:
            return {'error': f'Failed to create orchestrator: {e}'}
    base_dir = orchestrator.base_dir
    failed_uploads_file = base_dir / 'failed_uploads.json'
    
    if not failed_uploads_file.exists():
        return {'error': 'No failed uploads file found.'}
    
    try:
        with open(failed_uploads_file, 'r') as f:
            failed_data = json.load(f)
    except Exception as e:
        return {'error': f'Could not read failed uploads file: {e}'}
    
    if not failed_data:
        return {'error': 'No failed uploads to retry.'}
    
    # Filter to specific files if provided
    if files_to_retry:
        failed_data = {k: v for k, v in failed_data.items() if k in files_to_retry}
        if not failed_data:
            return {'error': 'None of the specified files were found in failed uploads.'}
    
    # Setup uploader if needed
    if orchestrator.icloud_uploader is None:
        try:
            orchestrator.setup_icloud_uploader(use_sync_method=use_sync_method)
        except Exception as e:
            return {'error': f'Failed to setup uploader: {e}'}
    
    # Group files by album
    from pathlib import Path
    files_by_album = {}
    file_to_album = {}
    for file_path_str, file_data in failed_data.items():
        file_path = Path(file_data['file'])
        album_name = file_data.get('album', '')
        
        if not file_path.exists():
            logger.warning(f"File no longer exists: {file_path}")
            continue
        
        if album_name not in files_by_album:
            files_by_album[album_name] = []
        files_by_album[album_name].append(file_path)
        file_to_album[file_path] = album_name
    
    if not files_by_album:
        return {'error': 'No valid files to retry (files may not exist).'}
    
    # Upload files
    from google_photos_icloud_migration.uploader.icloud_uploader import iCloudPhotosSyncUploader
    all_files = [f for files in files_by_album.values() for f in files]
    
    try:
        if isinstance(orchestrator.icloud_uploader, iCloudPhotosSyncUploader):
            results = orchestrator.icloud_uploader.upload_files_batch(
                all_files,
                albums=file_to_album,
                verify_after_upload=True
            )
        else:
            results = {}
            for album_name, files in files_by_album.items():
                album_results = orchestrator.icloud_uploader.upload_photos_batch(
                    files,
                    album_name=album_name if album_name else None,
                    verify_after_upload=True
                )
                results.update(album_results)
        
        # Update failed uploads file
        successful_files = {str(path) for path, success in results.items() if success}
        remaining_failed = {
            k: v for k, v in failed_data.items() 
            if k not in successful_files
        }
        
        # Increment retry count for still-failed files
        for file_path_str in remaining_failed:
            remaining_failed[file_path_str]['retry_count'] = \
                remaining_failed[file_path_str].get('retry_count', 0) + 1
        
        # Save updated failed uploads
        if remaining_failed:
            with open(failed_uploads_file, 'w') as f:
                json.dump(remaining_failed, f, indent=2)
        else:
            # All succeeded, remove the file
            if failed_uploads_file.exists():
                failed_uploads_file.unlink()
        
        successful = sum(1 for v in results.values() if v)
        return {
            'success': True,
            'message': f'Retried {successful}/{len(results)} files successfully',
            'successful_count': successful,
            'total_count': len(results),
            'remaining_failed': len(remaining_failed)
        }
    except Exception as e:
        logger.exception("Error retrying failed uploads")
        return {'error': f'Failed to retry uploads: {e}'}


@app.route('/api/failed-uploads/retry', methods=['POST'])
def retry_failed_uploads():
    """Retry all or specific failed uploads."""
    if migration_state['status'] == 'running':
        return jsonify({'error': 'Cannot retry uploads while migration is running'}), 400
    
    data = request.json or {}
    files_to_retry = data.get('files', None)  # List of file paths, or None for all
    use_sync_method = data.get('use_sync_method', False)
    config_path = data.get('config_path', 'config.yaml')
    
    result = _retry_failed_uploads(files_to_retry=files_to_retry, use_sync_method=use_sync_method, config_path=config_path)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route('/api/failed-uploads/retry-single', methods=['POST'])
def retry_single_failed_upload():
    """Retry a single failed upload."""
    if migration_state['status'] == 'running':
        return jsonify({'error': 'Cannot retry uploads while migration is running'}), 400
    
    data = request.json or {}
    file_path = data.get('file_path')
    use_sync_method = data.get('use_sync_method', False)
    config_path = data.get('config_path', 'config.yaml')
    
    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400
    
    result = _retry_failed_uploads(files_to_retry=[file_path], use_sync_method=use_sync_method, config_path=config_path)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)


@app.route('/api/corrupted-zip/redownload', methods=['POST'])
def redownload_corrupted_zip():
    """Redownload a corrupted zip file."""
    data = request.json or {}
    file_id = data.get('file_id')
    file_name = data.get('file_name')
    config_path = data.get('config_path', 'config.yaml')
    
    if not file_id or not file_name:
        return jsonify({'error': 'file_id and file_name are required'}), 400
    
    try:
        # Load config
        config_file = Path(config_path)
        if not config_file.exists():
            return jsonify({'error': 'Configuration file not found'}), 404
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Get orchestrator or create one
        orchestrator = migration_state.get('orchestrator')
        if not orchestrator:
            orchestrator = MigrationOrchestrator(config_path)
        
        # Get downloader
        downloader = orchestrator.downloader
        
        # Create file_info dict
        file_info = {
            'id': file_id,
            'name': file_name,
            'size': data.get('file_size', '0')
        }
        
        # Get zip directory from config
        base_dir = Path(config['processing']['base_dir'])
        zip_dir = base_dir / config['processing'].get('zip_dir', 'zips')
        zip_dir.mkdir(parents=True, exist_ok=True)
        
        # Delete corrupted file if it exists
        zip_path = zip_dir / file_name
        if zip_path.exists():
            zip_path.unlink()
            logger.info(f"Deleted corrupted file: {zip_path}")
        
        # Download the file
        logger.info(f"Redownloading corrupted zip: {file_name}")
        downloaded_path = downloader.download_single_zip(file_info, zip_dir)
        
        # Signal that corrupted zip has been redownloaded
        if migration_state.get('waiting_for_corrupted_zip_redownload', False):
            migration_state['corrupted_zip_redownloaded'] = True
            migration_state['status'] = 'running'
            emit_status_update()
            logger.info("Corrupted zip redownloaded, migration will continue")
        
        return jsonify({
            'success': True,
            'message': f'Successfully redownloaded {file_name}',
            'file_path': str(downloaded_path)
        })
        
    except Exception as e:
        logger.exception(f"Error redownloading corrupted zip: {e}")
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    emit_status_update()
    emit_progress_update()


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


def create_app():
    """Create and configure Flask app."""
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

