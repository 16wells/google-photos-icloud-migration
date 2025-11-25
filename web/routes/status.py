"""
Status and progress routes.
"""
from flask import Blueprint, session, jsonify

status_bp = Blueprint('status', __name__, url_prefix='/status')


@status_bp.route('/current')
def current_status():
    """Get current migration status"""
    migration_status = session.get('migration_status', {
        'status': 'idle',
        'phase': 'Not started',
        'progress': 0,
        'current_file': '',
        'total_files': 0,
        'processed_files': 0,
        'log': []
    })
    
    return jsonify(migration_status)


@status_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'google_authenticated': session.get('google_authenticated', False),
        'icloud_authenticated': session.get('icloud_authenticated', False)
    })

