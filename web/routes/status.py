"""
Status and progress routes.
"""
from flask import Blueprint, session, jsonify
from pathlib import Path
import json

status_bp = Blueprint('status', __name__, url_prefix='/status')


@status_bp.route('/current')
def current_status():
    """Get current migration status"""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({
            'status': 'idle',
            'phase': 'Not started',
            'progress': 0,
            'current_file': '',
            'total_files': 0,
            'processed_files': 0,
            'log': []
        })
    
    # Read from file-based status storage
    status_file = Path(f'/tmp/migration_status_{session_id}.json')
    
    if status_file.exists():
        try:
            status_data = json.loads(status_file.read_text())
            return jsonify(status_data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'phase': 'Status read error',
                'progress': 0,
                'current_file': '',
                'total_files': 0,
                'processed_files': 0,
                'log': [f'Error reading status: {str(e)}']
            })
    else:
        # Return default status if file doesn't exist
        return jsonify({
            'status': 'idle',
            'phase': 'Not started',
            'progress': 0,
            'current_file': '',
            'total_files': 0,
            'processed_files': 0,
            'log': []
        })


@status_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'google_authenticated': session.get('google_authenticated', False),
        'icloud_authenticated': session.get('icloud_authenticated', False)
    })

