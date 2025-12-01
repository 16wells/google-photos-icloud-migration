"""
Process monitoring service to detect if migration is running.
"""
import os
import psutil
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def find_migration_process() -> Optional[Dict]:
    """
    Find if a migration process is currently running.
    
    Returns:
        Dictionary with process info if found, None otherwise
    """
    try:
        current_pid = os.getpid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                
                cmdline = proc.info.get('cmdline', [])
                if not cmdline:
                    continue
                
                # Check if this is a Python process running migration
                cmdline_str = ' '.join(cmdline).lower()
                
                # Look for migration-related commands
                migration_keywords = [
                    'main.py',
                    'google_photos_icloud_migration',
                    'migration',
                    'python -m google_photos_icloud_migration'
                ]
                
                if any(keyword in cmdline_str for keyword in migration_keywords):
                    # Make sure it's actually a Python process
                    if 'python' in cmdline[0].lower() or 'python3' in cmdline[0].lower():
                        return {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': ' '.join(cmdline),
                            'status': proc.info['status'],
                            'create_time': proc.info['create_time']
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                logger.debug(f"Error checking process {proc.info.get('pid')}: {e}")
                continue
        
        return None
    except Exception as e:
        logger.warning(f"Error finding migration process: {e}")
        return None


def is_migration_running() -> bool:
    """Check if migration process is running."""
    return find_migration_process() is not None







