"""
Flask web application for Google Photos to iCloud Photos migration.
Proof of concept - simplified web-based interface.
"""
from flask import Flask, render_template, session, redirect, url_for
from flask_session import Session
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True

Session(app)

# Import routes
try:
    from routes.auth import auth_bp
    from routes.migration import migration_bp
    from routes.status import status_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(migration_bp)
    app.register_blueprint(status_bp)
except ImportError:
    # Routes not created yet, will be added
    pass

@app.route('/')
def index():
    """Main setup wizard page - public access"""
    return render_template('index.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

