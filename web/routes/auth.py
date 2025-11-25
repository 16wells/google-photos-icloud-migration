"""
Authentication routes for Google Drive and iCloud.
"""
from flask import Blueprint, redirect, url_for, session, request, jsonify, render_template
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# OAuth 2.0 configuration - these should be set as environment variables
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

CLIENT_CONFIG = {
    "web": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI]
    }
}
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


@auth_bp.route('/google')
def google_auth():
    """Initiate Google OAuth flow"""
    if not CLIENT_ID or not CLIENT_SECRET:
        return jsonify({'error': 'Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.'}), 500
    
    flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
    flow.redirect_uri = url_for('auth.google_callback', _external=True)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['oauth_state'] = state
    return redirect(authorization_url)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    state = session.get('oauth_state')
    if not state:
        return redirect(url_for('index'))
    
    flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES, state=state)
    flow.redirect_uri = url_for('auth.google_callback', _external=True)
    
    authorization_response = request.url
    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return f"Authentication failed: {e}", 400
    
    # Store credentials in session (in production, encrypt these)
    credentials = flow.credentials
    session['google_credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    session['google_authenticated'] = True
    
    return redirect(url_for('migration.setup'))


@auth_bp.route('/icloud', methods=['GET', 'POST'])
def icloud_auth():
    """Handle iCloud authentication"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST - receive credentials
    apple_id = request.form.get('apple_id')
    password = request.form.get('password')
    
    if not apple_id or not password:
        return jsonify({'error': 'Apple ID and password required'}), 400
    
    # Store in session (TODO: Encrypt in production!)
    session['icloud_credentials'] = {
        'apple_id': apple_id,
        'password': password  # WARNING: Encrypt this in production!
    }
    
    # Test authentication
    try:
        from pyicloud import PyiCloudService
        api = PyiCloudService(apple_id, password)
        
        if api.requires_2fa:
            # Store devices for 2FA selection
            session['icloud_devices'] = [
                {'id': i, 'name': d.get('deviceName', 'Unknown')}
                for i, d in enumerate(api.trusted_devices)
            ]
            return jsonify({
                'requires_2fa': True,
                'devices': session['icloud_devices']
            })
        
        session['icloud_authenticated'] = True
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/icloud/2fa', methods=['POST'])
def icloud_2fa():
    """Handle iCloud 2FA verification"""
    device_id = request.json.get('device_id')
    code = request.json.get('code')
    
    if not device_id or not code:
        return jsonify({'error': 'Device ID and code required'}), 400
    
    icloud_creds = session.get('icloud_credentials')
    if not icloud_creds:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from pyicloud import PyiCloudService
        api = PyiCloudService(icloud_creds['apple_id'], icloud_creds['password'])
        
        devices = api.trusted_devices
        device = devices[int(device_id)]
        
        if not api.send_verification_code(device):
            return jsonify({'error': 'Failed to send verification code'}), 500
        
        if not api.validate_verification_code(device, code):
            return jsonify({'error': 'Invalid verification code'}), 401
        
        session['icloud_authenticated'] = True
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

