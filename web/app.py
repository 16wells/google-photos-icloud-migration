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
from typing import Dict, Optional, Any
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
    'thread': None
}


def emit_progress_update():
    """Emit progress update to all connected clients."""
    socketio.emit('progress_update', migration_state['progress'])
    socketio.emit('statistics_update', migration_state['statistics'])


def emit_status_update():
    """Emit status update to all connected clients."""
    socketio.emit('status_update', {
        'status': migration_state['status'],
        'error': migration_state['error']
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


def run_migration(config_path: str, use_sync_method: bool = False):
    """
    Run migration in a separate thread.
    
    Args:
        config_path: Path to configuration file
        use_sync_method: Whether to use PhotoKit sync method
    """
    stats_thread = None
    try:
        migration_state['status'] = 'running'
        migration_state['error'] = None
        migration_state['statistics']['start_time'] = time.time()
        emit_status_update()
        
        # Create orchestrator
        orchestrator = MigrationOrchestrator(config_path)
        migration_state['orchestrator'] = orchestrator
        
        # Set up custom logging handler for web UI
        web_handler = WebProgressLogger()
        web_handler.setLevel(logging.INFO)
        web_handler.setFormatter(logging.Formatter('%(message)s'))
        web_logger = logging.getLogger()
        web_logger.addHandler(web_handler)
        
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
        
        # Run migration
        orchestrator.run(use_sync_method=use_sync_method, retry_failed=False)
        
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
        'error': migration_state['error']
    })


@app.route('/api/migration/start', methods=['POST'])
def start_migration():
    """Start migration."""
    if migration_state['status'] == 'running':
        return jsonify({'error': 'Migration is already running'}), 400
    
    data = request.json or {}
    config_path = data.get('config_path', 'config.yaml')
    use_sync_method = data.get('use_sync_method', False)
    
    if not Path(config_path).exists():
        return jsonify({'error': f'Configuration file not found: {config_path}'}), 404
    
    # Reset state
    migration_state['status'] = 'idle'
    migration_state['error'] = None
    migration_state['stop_requested'] = False
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
        args=(config_path, use_sync_method),
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

