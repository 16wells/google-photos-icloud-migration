"""
Statistics tracking for migration process.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class MigrationStatistics:
    """Tracks statistics throughout the migration process."""
    
    def __init__(self):
        """Initialize statistics tracker."""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Phase 1: Download
        self.zip_files_total = 0
        self.zip_files_downloaded = 0
        self.zip_files_skipped_existing = 0
        self.zip_files_failed_download = 0
        self.zip_download_errors: List[Dict] = []
        self.zip_files_corrupted = 0
        
        # Phase 2: Extraction
        self.zip_files_extracted = 0
        self.zip_files_extraction_failed = 0
        self.extraction_errors: List[Dict] = []
        
        # Phase 3: Metadata Processing
        self.media_files_found = 0
        self.media_files_with_metadata = 0
        self.media_files_processed = 0
        self.media_files_processing_failed = 0
        self.metadata_errors: List[Dict] = []
        
        # Phase 4: Album Parsing
        self.albums_identified = 0
        self.albums_from_structure = 0
        self.albums_from_json = 0
        
        # Phase 5: Upload
        self.files_uploaded_successfully = 0
        self.files_upload_failed = 0
        self.files_verification_failed = 0
        self.upload_errors: List[Dict] = []
        self.verification_errors: List[Dict] = []
        
        # Overall
        self.zip_files_processed_successfully = 0
        self.zip_files_processed_failed = 0
        
        # File sizes (in bytes)
        self.total_downloaded_size = 0
        self.total_uploaded_size = 0
        
        # Albums
        self.albums_created = 0
        self.albums_upload_errors: List[Dict] = []
        
    def start(self):
        """Mark the start of migration."""
        self.start_time = datetime.now()
    
    def finish(self):
        """Mark the end of migration."""
        self.end_time = datetime.now()
    
    def get_duration(self) -> Optional[float]:
        """Get migration duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def record_zip_download(self, file_name: str, size: int = 0, success: bool = True, error: Optional[str] = None):
        """Record a zip file download."""
        if success:
            self.zip_files_downloaded += 1
            self.total_downloaded_size += size
        else:
            self.zip_files_failed_download += 1
            if error:
                self.zip_download_errors.append({
                    'file': file_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
    
    def record_zip_corrupted(self, file_name: str, error: str):
        """Record a corrupted zip file."""
        self.zip_files_corrupted += 1
        self.zip_download_errors.append({
            'file': file_name,
            'error': f'Corrupted: {error}',
            'timestamp': datetime.now().isoformat()
        })
    
    def record_zip_extraction(self, file_name: str, success: bool = True, error: Optional[str] = None):
        """Record a zip file extraction."""
        if success:
            self.zip_files_extracted += 1
        else:
            self.zip_files_extraction_failed += 1
            if error:
                self.extraction_errors.append({
                    'file': file_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
    
    def record_media_files(self, count: int, with_metadata: int):
        """Record media files found."""
        self.media_files_found += count
        self.media_files_with_metadata += with_metadata
    
    def record_metadata_processing(self, success: bool = True, error: Optional[str] = None, file_name: Optional[str] = None):
        """Record metadata processing."""
        if success:
            self.media_files_processed += 1
        else:
            self.media_files_processing_failed += 1
            if error and file_name:
                self.metadata_errors.append({
                    'file': file_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
    
    def record_albums(self, count: int, from_structure: int = 0, from_json: int = 0):
        """Record albums identified."""
        self.albums_identified += count
        self.albums_from_structure += from_structure
        self.albums_from_json += from_json
    
    def record_upload(self, file_name: str, size: int = 0, success: bool = True, error: Optional[str] = None):
        """Record a file upload."""
        if success:
            self.files_uploaded_successfully += 1
            self.total_uploaded_size += size
        else:
            self.files_upload_failed += 1
            if error:
                self.upload_errors.append({
                    'file': file_name,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                })
    
    def record_verification_failure(self, file_name: str, error: Optional[str] = None):
        """Record a verification failure."""
        self.files_verification_failed += 1
        if error:
            self.verification_errors.append({
                'file': file_name,
                'error': error,
                'timestamp': datetime.now().isoformat()
            })
    
    def record_zip_processed(self, success: bool = True):
        """Record a zip file as fully processed."""
        if success:
            self.zip_files_processed_successfully += 1
        else:
            self.zip_files_processed_failed += 1
    
    def to_dict(self) -> Dict:
        """Convert statistics to dictionary."""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.get_duration(),
            'download': {
                'zip_files_total': self.zip_files_total,
                'zip_files_downloaded': self.zip_files_downloaded,
                'zip_files_skipped_existing': self.zip_files_skipped_existing,
                'zip_files_failed_download': self.zip_files_failed_download,
                'zip_files_corrupted': self.zip_files_corrupted,
                'total_downloaded_size_bytes': self.total_downloaded_size,
                'errors': self.zip_download_errors
            },
            'extraction': {
                'zip_files_extracted': self.zip_files_extracted,
                'zip_files_extraction_failed': self.zip_files_extraction_failed,
                'errors': self.extraction_errors
            },
            'metadata': {
                'media_files_found': self.media_files_found,
                'media_files_with_metadata': self.media_files_with_metadata,
                'media_files_processed': self.media_files_processed,
                'media_files_processing_failed': self.media_files_processing_failed,
                'errors': self.metadata_errors
            },
            'albums': {
                'albums_identified': self.albums_identified,
                'albums_from_structure': self.albums_from_structure,
                'albums_from_json': self.albums_from_json
            },
            'upload': {
                'files_uploaded_successfully': self.files_uploaded_successfully,
                'files_upload_failed': self.files_upload_failed,
                'files_verification_failed': self.files_verification_failed,
                'total_uploaded_size_bytes': self.total_uploaded_size,
                'errors': self.upload_errors,
                'verification_errors': self.verification_errors
            },
            'overall': {
                'zip_files_processed_successfully': self.zip_files_processed_successfully,
                'zip_files_processed_failed': self.zip_files_processed_failed
            }
        }
    
    def save(self, file_path: Path):
        """Save statistics to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

