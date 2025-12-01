"""
Log file monitoring service for watching terminal migration process.
"""
import os
import re
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, List
from collections import deque

logger = logging.getLogger(__name__)


class LogFileMonitor:
    """Monitors a log file and extracts progress information."""
    
    def __init__(self, log_file_path: Path, on_update: Optional[Callable] = None):
        """
        Initialize log file monitor.
        
        Args:
            log_file_path: Path to the log file to monitor
            on_update: Callback function called when new log entries are found
        """
        self.log_file_path = Path(log_file_path)
        self.on_update = on_update
        self.running = False
        self.thread = None
        self.last_position = 0
        self.buffer = deque(maxlen=1000)  # Keep last 1000 log entries in memory
        self.lock = threading.Lock()
        
        # State extracted from logs
        self.state = {
            'status': 'idle',  # idle, running, paused, stopped, error, completed
            'progress': {
                'phase': None,
                'current': 0,
                'total': 0,
                'percentage': 0,
                'message': '',
                'current_activity': None,
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
            'last_log_time': None
        }
        
        # Initialize last position if file exists
        if self.log_file_path.exists():
            self.last_position = self.log_file_path.stat().st_size
    
    def start(self):
        """Start monitoring the log file."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started monitoring log file: {self.log_file_path}")
    
    def stop(self):
        """Stop monitoring the log file."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Stopped monitoring log file")
    
    def _monitor_loop(self):
        """Main monitoring loop that tails the log file."""
        while self.running:
            try:
                if not self.log_file_path.exists():
                    time.sleep(1)
                    continue
                
                # Open file and seek to last position
                with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to last known position
                    f.seek(self.last_position)
                    
                    # Read new lines
                    new_lines = f.readlines()
                    
                    if new_lines:
                        # Update position
                        self.last_position = f.tell()
                        
                        # Process new lines
                        for line in new_lines:
                            self._process_log_line(line.strip())
                    
                    # If we're at the end of file, wait a bit before checking again
                    if not new_lines:
                        time.sleep(0.5)
                    else:
                        # If we got new lines, process them quickly
                        time.sleep(0.1)
                        
            except Exception as e:
                logger.warning(f"Error monitoring log file: {e}")
                time.sleep(1)
    
    def _process_log_line(self, line: str):
        """Process a single log line and extract information."""
        if not line:
            return
        
        current_time = time.time()
        self.state['last_log_time'] = current_time
        
        # Add to buffer
        with self.lock:
            self.buffer.append({
                'line': line,
                'timestamp': current_time
            })
        
        # Parse log line for progress information
        self._parse_progress_from_log(line)
        
        # Call update callback if provided
        if self.on_update:
            try:
                self.on_update(line, self.state)
            except Exception:
                pass
    
    def _parse_progress_from_log(self, message: str):
        """Parse progress information from log messages."""
        current_time = time.time()
        
        # Detect if migration is running based on log activity
        if self.state['status'] == 'idle' and any(keyword in message for keyword in [
            'Processing zip', 'Extracting', 'Processing metadata', 'Uploading', 'Downloading',
            'Found', 'Processing batch', 'Identified', 'Listing zip files', 'Phase'
        ]):
            self.state['status'] = 'running'
            if not self.state['statistics']['start_time']:
                self.state['statistics']['start_time'] = current_time
        
        # Track current activity
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
            self.state['progress']['current_activity'] = current_activity
            self.state['progress']['last_update_time'] = current_time
        
        # Extract statistics from log messages
        
        # "Found X zip files total to process" or "Found X zip files total"
        zip_total_match = re.search(r'Found (\d+) zip files? (?:total to process|total|to process)', message, re.IGNORECASE)
        if zip_total_match:
            total = int(zip_total_match.group(1))
            self.state['statistics']['zip_files_total'] = total
        
        # "Found X media files in this zip" or "Found X media files to process"
        media_found_match = re.search(r'Found (\d+) media files?', message, re.IGNORECASE)
        if media_found_match:
            found = int(media_found_match.group(1))
            current_found = self.state['statistics'].get('media_files_found', 0)
            self.state['statistics']['media_files_found'] = current_found + found
        
        # "Identified X albums" or "Found X albums"
        albums_match = re.search(r'(?:Identified|Found) (\d+) albums?', message, re.IGNORECASE)
        if albums_match:
            albums = int(albums_match.group(1))
            self.state['statistics']['albums_identified'] = albums
        
        # Track uploaded files
        uploaded_match = re.search(r'(?:Uploaded|uploaded) (\d+)(?: files?| photos?| videos?)', message, re.IGNORECASE)
        if uploaded_match and 'successfully' in message.lower():
            uploaded = int(uploaded_match.group(1))
            current_uploaded = self.state['statistics'].get('media_files_uploaded', 0)
            if uploaded > current_uploaded:
                self.state['statistics']['media_files_uploaded'] = uploaded
        
        # Extract progress information from log messages
        # Example: "Processing zip 5/10: filename.zip"
        zip_progress = re.search(r'Processing zip (\d+)/(\d+)', message)
        if zip_progress:
            current = int(zip_progress.group(1))
            total = int(zip_progress.group(2))
            self.state['progress'] = {
                'phase': 'Processing ZIP Files',
                'current': current,
                'total': total,
                'percentage': int((current / total * 100)) if total > 0 else 0,
                'message': message,
                'current_activity': self.state['progress'].get('current_activity', current_activity),
                'last_update_time': current_time
            }
            self.state['statistics']['zip_files_processed'] = current
            self.state['statistics']['zip_files_total'] = total
            return
        
        # "Processing existing zip X/Y: filename.zip"
        existing_zip_progress = re.search(r'Processing existing zip (\d+)/(\d+)', message)
        if existing_zip_progress:
            current = int(existing_zip_progress.group(1))
            total = int(existing_zip_progress.group(2))
            self.state['progress'] = {
                'phase': 'Processing ZIP Files',
                'current': current,
                'total': total,
                'percentage': int((current / total * 100)) if total > 0 else 0,
                'message': message,
                'current_activity': self.state['progress'].get('current_activity', current_activity),
                'last_update_time': current_time
            }
            self.state['statistics']['zip_files_processed'] = current
            self.state['statistics']['zip_files_total'] = total
            return
        
        # "Downloading zip X/Y: filename.zip"
        downloading_zip_progress = re.search(r'Downloading zip (\d+)/(\d+)', message)
        if downloading_zip_progress:
            current = int(downloading_zip_progress.group(1))
            total = int(downloading_zip_progress.group(2))
            self.state['progress'] = {
                'phase': 'Downloading ZIP Files',
                'current': current,
                'total': total,
                'percentage': int((current / total * 100)) if total > 0 else 0,
                'message': message,
                'current_activity': self.state['progress'].get('current_activity', current_activity),
                'last_update_time': current_time
            }
            self.state['statistics']['zip_files_total'] = total
            return
        
        # Example: "Uploaded 150/200 files"
        upload_progress = re.search(r'Uploaded (\d+)/(\d+) files?', message)
        if upload_progress:
            current = int(upload_progress.group(1))
            total = int(upload_progress.group(2))
            self.state['progress'] = {
                'phase': 'Uploading to iCloud',
                'current': current,
                'total': total,
                'percentage': int((current / total * 100)) if total > 0 else 0,
                'message': message,
                'current_activity': self.state['progress'].get('current_activity', current_activity),
                'last_update_time': current_time
            }
            self.state['statistics']['media_files_uploaded'] = current
            return
        
        # Update phase from log message
        if 'Phase 1' in message or ('Downloading' in message and 'zip' in message.lower()):
            self.state['progress']['phase'] = 'Downloading ZIP Files'
            self.state['progress']['last_update_time'] = current_time
        elif 'Phase 2' in message or 'Extracting' in message:
            self.state['progress']['phase'] = 'Extracting Files'
            self.state['progress']['last_update_time'] = current_time
        elif 'Phase 3' in message or 'Processing metadata' in message:
            self.state['progress']['phase'] = 'Processing Metadata'
            self.state['progress']['last_update_time'] = current_time
        elif 'Phase 4' in message or 'Parsing album' in message:
            self.state['progress']['phase'] = 'Parsing Albums'
            self.state['progress']['last_update_time'] = current_time
        elif 'Phase 5' in message or ('Uploading' in message and 'iCloud' in message):
            self.state['progress']['phase'] = 'Uploading to iCloud'
            self.state['progress']['last_update_time'] = current_time
        
        # Detect completion
        if 'Migration completed' in message or 'completed!' in message.lower():
            self.state['status'] = 'completed'
            if self.state['statistics']['start_time']:
                self.state['statistics']['elapsed_time'] = current_time - self.state['statistics']['start_time']
        
        # Detect errors
        if 'ERROR' in message or 'Error' in message or 'Failed' in message:
            if 'status' not in self.state or self.state['status'] != 'completed':
                self.state['status'] = 'error'
                self.state['error'] = message
    
    def get_recent_logs(self, count: int = 100) -> List[Dict]:
        """Get recent log entries from buffer."""
        with self.lock:
            return list(self.buffer)[-count:]
    
    def get_state(self) -> Dict:
        """Get current state."""
        # Update elapsed time if running
        if self.state['status'] == 'running' and self.state['statistics']['start_time']:
            self.state['statistics']['elapsed_time'] = time.time() - self.state['statistics']['start_time']
        
        return self.state.copy()







