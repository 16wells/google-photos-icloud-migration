"""
Migration control routes.
"""
from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from services.migration_worker import MigrationWorker
import threading
import uuid

migration_bp = Blueprint('migration', __name__, url_prefix='/migration')


@migration_bp.route('/setup')
def setup():
    """Migration setup page - requires authentication"""
    if 'google_authenticated' not in session:
        return redirect(url_for('auth.google_auth'))
    if 'icloud_authenticated' not in session:
        return redirect(url_for('auth.icloud_auth'))
    
    # Generate session ID for tracking
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('dashboard.html')


@migration_bp.route('/start', methods=['POST'])
def start_migration():
    """Start migration process"""
    # Check authentication
    if 'google_authenticated' not in session:
        return jsonify({'error': 'Google Drive not authenticated'}), 401
    if 'icloud_authenticated' not in session:
        return jsonify({'error': 'iCloud not authenticated'}), 401
    
    data = request.json or {}
    folder_id = data.get('folder_id', '')
    zip_pattern = data.get('zip_pattern', 'takeout-*.zip')
    
    # Get credentials from session
    google_creds = session.get('google_credentials')
    icloud_creds = session.get('icloud_credentials')
    
    if not google_creds or not icloud_creds:
        return jsonify({'error': 'Credentials not found in session'}), 401
    
    # Initialize migration status
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['migration_status'] = {
        'status': 'starting',
        'phase': 'Initializing',
        'progress': 0,
        'current_file': '',
        'total_files': 0,
        'processed_files': 0
    }
    
    # Start migration in background thread
    try:
        worker = MigrationWorker(
            google_credentials=google_creds,
            icloud_credentials=icloud_creds,
            folder_id=folder_id if folder_id else None,
            zip_pattern=zip_pattern,
            session_id=session_id
        )
        
        thread = threading.Thread(target=worker.run)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'session_id': session_id,
            'message': 'Migration started successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@migration_bp.route('/stop', methods=['POST'])
def stop_migration():
    """Stop migration process"""
    session['migration_status'] = {
        'status': 'stopped',
        'phase': 'Stopped by user',
        'progress': session.get('migration_status', {}).get('progress', 0)
    }
    return jsonify({'status': 'stopped'})

