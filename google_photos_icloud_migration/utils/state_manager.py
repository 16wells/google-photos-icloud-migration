"""
State management for migration process tracking and resumption.
"""
import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class FileProcessingState(Enum):
    """States a file can be in during processing."""
    PENDING = "pending"
    EXTRACTED = "extracted"
    CONVERTED = "converted"
    COPIED_TO_PHOTOS = "copied_to_photos"
    SYNCED_TO_ICLOUD = "synced_to_icloud"
    FAILED_EXTRACTION = "failed_extraction"
    FAILED_CONVERSION = "failed_conversion"
    FAILED_PHOTOS_COPY = "failed_photos_copy"
    FAILED_UPLOAD = "failed_upload"


class ZipProcessingState(Enum):
    """States a zip file can be in during processing."""
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    EXTRACTED = "extracted"
    CONVERTED = "converted"
    UPLOADED = "uploaded"
    FAILED_DOWNLOAD = "failed_download"
    FAILED_EXTRACTION = "failed_extraction"
    FAILED_CONVERSION = "failed_conversion"
    FAILED_UPLOAD = "failed_upload"


class StateManager:
    """Manages state tracking for migration process."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize state manager.
        
        Args:
            base_dir: Base directory for state files
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # State file paths
        self.zip_state_file = self.base_dir / 'zip_processing_state.json'
        self.file_state_file = self.base_dir / 'file_processing_state.json'
        self.checkpoint_file = self.base_dir / 'checkpoint.json'
        
        # In-memory state caches
        self._zip_state: Dict[str, Dict] = {}
        self._file_state: Dict[str, Dict] = {}
        self._checkpoint: Optional[Dict] = None
        
        # Load existing state
        self._load_state()
    
    def _load_state(self):
        """Load state from files."""
        # Load zip state
        if self.zip_state_file.exists():
            try:
                with open(self.zip_state_file, 'r') as f:
                    self._zip_state = json.load(f)
                logger.info(f"📂 Loaded state from: {self.zip_state_file}")
                logger.info(f"   Found {len(self._zip_state)} zip files in state")
                # Count completed zips
                completed_count = sum(1 for data in self._zip_state.values() 
                                    if data.get('state') == ZipProcessingState.UPLOADED.value)
                if completed_count > 0:
                    logger.info(f"   ✓ {completed_count} zip files already marked as completed")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"⚠️  Could not load zip state from {self.zip_state_file}: {e}")
                logger.warning("   Starting with empty state (will reprocess all files)")
                self._zip_state = {}
        else:
            logger.info(f"📂 No existing state file found at: {self.zip_state_file}")
            logger.info("   Starting fresh (all zip files will be processed)")
            self._zip_state = {}
        
        # Load file state
        if self.file_state_file.exists():
            try:
                with open(self.file_state_file, 'r') as f:
                    self._file_state = json.load(f)
                logger.debug(f"Loaded {len(self._file_state)} file states from {self.file_state_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load file state: {e}")
                self._file_state = {}
        else:
            self._file_state = {}
        
        # Load checkpoint
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    self._checkpoint = json.load(f)
                logger.debug(f"Loaded checkpoint from {self.checkpoint_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load checkpoint: {e}")
                self._checkpoint = None
        else:
            self._checkpoint = None
    
    def _save_zip_state(self):
        """Save zip state to file."""
        try:
            with open(self.zip_state_file, 'w') as f:
                json.dump(self._zip_state, f, indent=2)
            logger.debug(f"State saved to: {self.zip_state_file}")
        except IOError as e:
            logger.error(f"❌ Could not save zip state to {self.zip_state_file}: {e}")
            logger.error("   State changes may be lost! Check file permissions and disk space.")
    
    def _save_file_state(self):
        """Save file state to file."""
        try:
            with open(self.file_state_file, 'w') as f:
                json.dump(self._file_state, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save file state: {e}")
    
    def _save_checkpoint(self):
        """Save checkpoint to file."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self._checkpoint, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save checkpoint: {e}")
    
    # Zip state methods
    def get_zip_state(self, zip_name: str) -> Optional[str]:
        """Get current state of a zip file."""
        if zip_name in self._zip_state:
            return self._zip_state[zip_name].get('state')
        return None
    
    def set_zip_state(self, zip_name: str, state: ZipProcessingState, 
                      metadata: Optional[Dict] = None):
        """
        Set state of a zip file.
        
        Args:
            zip_name: Name of zip file
            state: New state
            metadata: Optional metadata (file_id, size, error, etc.)
        """
        if zip_name not in self._zip_state:
            self._zip_state[zip_name] = {}
        
        self._zip_state[zip_name]['state'] = state.value
        self._zip_state[zip_name]['updated_at'] = datetime.now().isoformat()
        
        if metadata:
            self._zip_state[zip_name].update(metadata)
        
        self._save_zip_state()
        logger.debug(f"Updated zip state: {zip_name} -> {state.value}")
    
    def get_zips_by_state(self, state: ZipProcessingState) -> List[str]:
        """Get all zip names in a specific state."""
        return [
            zip_name for zip_name, data in self._zip_state.items()
            if data.get('state') == state.value
        ]
    
    def is_zip_complete(self, zip_name: str) -> bool:
        """Check if zip processing is complete."""
        state = self.get_zip_state(zip_name)
        return state == ZipProcessingState.UPLOADED.value
    
    def is_zip_extracted(self, zip_name: str) -> bool:
        """Check if zip has been extracted."""
        state = self.get_zip_state(zip_name)
        return state in [
            ZipProcessingState.EXTRACTED.value,
            ZipProcessingState.CONVERTED.value,
            ZipProcessingState.UPLOADED.value
        ]
    
    def is_zip_converted(self, zip_name: str) -> bool:
        """Check if zip has been converted."""
        state = self.get_zip_state(zip_name)
        return state in [
            ZipProcessingState.CONVERTED.value,
            ZipProcessingState.UPLOADED.value
        ]
    
    # File state methods
    def get_file_state(self, file_path: str) -> Optional[str]:
        """Get current state of a file."""
        if file_path in self._file_state:
            return self._file_state[file_path].get('state')
        return None
    
    def set_file_state(self, file_path: str, state: FileProcessingState,
                       metadata: Optional[Dict] = None):
        """
        Set state of a file.
        
        Args:
            file_path: Path to file (as string)
            state: New state
            metadata: Optional metadata (zip_name, album, error, etc.)
        """
        if file_path not in self._file_state:
            self._file_state[file_path] = {}
        
        self._file_state[file_path]['state'] = state.value
        self._file_state[file_path]['updated_at'] = datetime.now().isoformat()
        
        if metadata:
            self._file_state[file_path].update(metadata)
        
        self._save_file_state()
        logger.debug(f"Updated file state: {Path(file_path).name} -> {state.value}")
    
    def get_files_by_state(self, state: FileProcessingState) -> List[str]:
        """Get all file paths in a specific state."""
        return [
            file_path for file_path, data in self._file_state.items()
            if data.get('state') == state.value
        ]
    
    def get_files_by_zip(self, zip_name: str) -> List[str]:
        """Get all files associated with a zip."""
        return [
            file_path for file_path, data in self._file_state.items()
            if data.get('zip_name') == zip_name
        ]
    
    def is_file_complete(self, file_path: str) -> bool:
        """Check if file processing is complete."""
        state = self.get_file_state(file_path)
        return state == FileProcessingState.SYNCED_TO_ICLOUD.value
    
    # Checkpoint methods
    def set_checkpoint(self, step: str, zip_name: Optional[str] = None,
                      file_path: Optional[str] = None, metadata: Optional[Dict] = None):
        """
        Set a checkpoint.
        
        Args:
            step: Current step (e.g., 'extract', 'convert', 'upload')
            zip_name: Current zip being processed
            file_path: Current file being processed
            metadata: Optional additional metadata
        """
        self._checkpoint = {
            'step': step,
            'zip_name': zip_name,
            'file_path': file_path,
            'timestamp': datetime.now().isoformat(),
        }
        if metadata:
            self._checkpoint.update(metadata)
        
        self._save_checkpoint()
        logger.debug(f"Checkpoint set: {step} (zip: {zip_name}, file: {file_path})")
    
    def get_checkpoint(self) -> Optional[Dict]:
        """Get current checkpoint."""
        return self._checkpoint
    
    def clear_checkpoint(self):
        """Clear checkpoint."""
        self._checkpoint = None
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        logger.debug("Checkpoint cleared")
    
    # Batch operations
    def mark_zip_extracted(self, zip_name: str, extracted_dir: Optional[str] = None):
        """Mark zip as extracted."""
        metadata = {}
        if extracted_dir:
            metadata['extracted_dir'] = extracted_dir
        self.set_zip_state(zip_name, ZipProcessingState.EXTRACTED, metadata)
    
    def mark_zip_converted(self, zip_name: str):
        """Mark zip as converted."""
        self.set_zip_state(zip_name, ZipProcessingState.CONVERTED)
    
    def mark_zip_uploaded(self, zip_name: str):
        """Mark zip as uploaded."""
        self.set_zip_state(zip_name, ZipProcessingState.UPLOADED)
    
    def mark_file_extracted(self, file_path: str, zip_name: str):
        """Mark file as extracted."""
        self.set_file_state(
            file_path,
            FileProcessingState.EXTRACTED,
            {'zip_name': zip_name}
        )
    
    def mark_file_converted(self, file_path: str, zip_name: str):
        """Mark file as converted."""
        self.set_file_state(
            file_path,
            FileProcessingState.CONVERTED,
            {'zip_name': zip_name}
        )
    
    def mark_file_copied_to_photos(self, file_path: str, zip_name: str,
                                   asset_identifier: Optional[str] = None):
        """Mark file as copied to Photos library."""
        metadata = {'zip_name': zip_name}
        if asset_identifier:
            metadata['asset_identifier'] = asset_identifier
        self.set_file_state(
            file_path,
            FileProcessingState.COPIED_TO_PHOTOS,
            metadata
        )
    
    def mark_file_synced_to_icloud(self, file_path: str, zip_name: str):
        """Mark file as synced to iCloud."""
        self.set_file_state(
            file_path,
            FileProcessingState.SYNCED_TO_ICLOUD,
            {'zip_name': zip_name}
        )
    
    def mark_file_failed(self, file_path: str, zip_name: str,
                        failure_type: FileProcessingState, error: str):
        """Mark file as failed at a specific step."""
        self.set_file_state(
            file_path,
            failure_type,
            {
                'zip_name': zip_name,
                'error': error,
                'failed_at': datetime.now().isoformat()
            }
        )
    
    def mark_zip_failed(self, zip_name: str, failure_type: ZipProcessingState,
                       error: str):
        """Mark zip as failed at a specific step."""
        self.set_zip_state(
            zip_name,
            failure_type,
            {
                'error': error,
                'failed_at': datetime.now().isoformat()
            }
        )
    
    # Cleanup methods
    def clear_state(self):
        """Clear all state (for restart from scratch)."""
        self._zip_state = {}
        self._file_state = {}
        self._checkpoint = None
        
        if self.zip_state_file.exists():
            self.zip_state_file.unlink()
        if self.file_state_file.exists():
            self.file_state_file.unlink()
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        
        logger.info("Cleared all state files")
    
    def get_statistics(self) -> Dict:
        """Get statistics about current state."""
        zip_stats = {}
        for state in ZipProcessingState:
            zip_stats[state.value] = len(self.get_zips_by_state(state))
        
        file_stats = {}
        for state in FileProcessingState:
            file_stats[state.value] = len(self.get_files_by_state(state))
        
        return {
            'zip_states': zip_stats,
            'file_states': file_stats,
            'total_zips': len(self._zip_state),
            'total_files': len(self._file_state),
            'checkpoint': self._checkpoint
        }

