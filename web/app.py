"""
Flask web application for Google Photos to iCloud Photos Migration Tool.
Provides a modern web UI with real-time progress updates.
"""
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import yaml

from google_photos_icloud_migration.cli.main import MigrationOrchestrator, MigrationStoppedException
from google_photos_icloud_migration.exceptions import ConfigurationError

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
        'message': ''
    },
    'statistics': {
        'zip_files_total': 0,
        'zip_files_processed': 0,
        'media_files_found': 0,
        'media_files_uploaded': 0,
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
    'log_level': 'INFO',
    'web_handler': None,
    'proceed_after_retries': False,
    'paused_for_retries': False
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
        'log_level': migration_state.get('log_level', 'INFO'),
        'paused_for_retries': migration_state.get('paused_for_retries', False)
    })


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
            'message': message
        }
        migration_state['statistics']['zip_files_processed'] = current
        migration_state['statistics']['zip_files_total'] = total
        emit_progress_update()
        emit_progress_update()  # Also emit statistics
        return
    
    # Example: "Uploaded 150/200 files"
    upload_progress = re.search(r'Uploaded (\d+)/(\d+)', message)
    if upload_progress:
        current = int(upload_progress.group(1))
        total = int(upload_progress.group(2))
        migration_state['progress'] = {
            'phase': 'Uploading to iCloud',
            'current': current,
            'total': total,
            'percentage': int((current / total * 100)) if total > 0 else 0,
            'message': message
        }
        migration_state['statistics']['media_files_uploaded'] = current
        emit_progress_update()
        return
    
    # Update phase from log message
    if 'Phase 1' in message or 'Downloading' in message:
        migration_state['progress']['phase'] = 'Downloading ZIP Files'
        emit_progress_update()
    elif 'Phase 2' in message or 'Extracting' in message:
        migration_state['progress']['phase'] = 'Extracting Files'
        emit_progress_update()
    elif 'Phase 3' in message or 'Processing metadata' in message:
        migration_state['progress']['phase'] = 'Processing Metadata'
        emit_progress_update()
    elif 'Phase 4' in message or 'Parsing album' in message:
        migration_state['progress']['phase'] = 'Parsing Albums'
        emit_progress_update()
    elif 'Phase 5' in message or 'Uploading' in message:
        migration_state['progress']['phase'] = 'Uploading to iCloud'
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


def monitor_statistics(orchestrator):
    """Monitor orchestrator statistics and update state periodically."""
    while migration_state['status'] == 'running' and not migration_state['stop_requested']:
        try:
            if orchestrator and hasattr(orchestrator, 'statistics'):
                stats = orchestrator.statistics
                
                # Update statistics from orchestrator
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
                
                # Update elapsed time
                if hasattr(stats, 'start_time') and stats.start_time:
                    elapsed = (time.time() - stats.start_time.timestamp()) if hasattr(stats.start_time, 'timestamp') else 0
                    migration_state['statistics']['elapsed_time'] = elapsed
                
                emit_progress_update()
            
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            logger.warning(f"Error monitoring statistics: {e}")
            time.sleep(5)  # Wait longer on error


def run_migration(config_path: str, use_sync_method: bool = False, log_level: str = 'INFO'):
    """
    Run migration in a separate thread.
    
    Args:
        config_path: Path to configuration file
        use_sync_method: Whether to use PhotoKit sync method
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    stats_thread = None
    try:
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
        log_level_constant = level_map.get(log_level.upper(), logging.INFO)
        web_handler.setLevel(log_level_constant)
        # Include timestamp, logger name, and level for better context
        web_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        web_logger = logging.getLogger()
        web_logger.addHandler(web_handler)
        migration_state['web_handler'] = web_handler
        
        # Start statistics monitoring thread
        stats_thread = threading.Thread(
            target=monitor_statistics,
            args=(orchestrator,),
            daemon=True
        )
        stats_thread.start()
        
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
        
    except MigrationStoppedException:
        migration_state['status'] = 'stopped'
        emit_status_update()
    except Exception as e:
        logger.exception("Migration failed")
        migration_state['status'] = 'error'
        migration_state['error'] = str(e)
        emit_status_update()
    finally:
        # Clean up logging handler
        web_logger = logging.getLogger()
        for handler in web_logger.handlers[:]:
            if isinstance(handler, WebProgressLogger):
                web_logger.removeHandler(handler)
        
        migration_state['thread'] = None
        migration_state['stop_requested'] = False
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
    return jsonify({
        'status': migration_state['status'],
        'progress': migration_state['progress'],
        'statistics': migration_state['statistics'],
        'error': migration_state['error'],
        'log_level': migration_state.get('log_level', 'INFO'),
        'paused_for_retries': migration_state.get('paused_for_retries', False)
    })


@app.route('/api/migration/start', methods=['POST'])
def start_migration():
    """Start migration."""
    if migration_state['status'] == 'running':
        return jsonify({'error': 'Migration is already running'}), 400
    
    data = request.json or {}
    config_path = data.get('config_path', 'config.yaml')
    use_sync_method = data.get('use_sync_method', False)
    log_level = data.get('log_level', 'INFO')
    
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
        'message': ''
    }
    migration_state['statistics'] = {
        'zip_files_total': 0,
        'zip_files_processed': 0,
        'media_files_found': 0,
        'media_files_uploaded': 0,
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
    log_level = data.get('log_level', 'INFO')
    
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
        log_level_constant = level_map.get(log_level.upper(), logging.INFO)
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
    import psutil
    import os
    
    try:
        # Get current process info
        current_process = psutil.Process(os.getpid())
        process_info = {
            'pid': current_process.pid,
            'status': current_process.status(),
            'memory_mb': current_process.memory_info().rss / (1024 * 1024),
            'cpu_percent': current_process.cpu_percent(interval=0.1),
            'uptime_seconds': time.time() - current_process.create_time()
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

