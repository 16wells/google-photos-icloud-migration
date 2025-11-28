#!/usr/bin/env python3
"""
Web server launcher for Google Photos to iCloud Photos Migration Tool.
Run this script to start the web UI.
"""
# Workaround for Python 3.9 compatibility with dependencies that use importlib.metadata.packages_distributions
import sys
if sys.version_info < (3, 10):
    try:
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            # Add a dummy function to prevent AttributeError
            def _packages_distributions():
                """Compatibility shim for Python < 3.10"""
                return {}
            importlib.metadata.packages_distributions = _packages_distributions
    except (ImportError, AttributeError):
        pass

from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.app import create_app, socketio

if __name__ == '__main__':
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = create_app()
    
    # Try port 5001 first (5000 is often used by macOS AirPlay Receiver)
    port = 5001
    print("=" * 60)
    print("Google Photos to iCloud Migration - Web UI")
    print("=" * 60)
    print(f"Starting web server on http://localhost:{port}")
    print(f"Open your browser and navigate to the URL above")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    
    socketio.run(app, host='127.0.0.1', port=port, debug=True, allow_unsafe_werkzeug=True)

