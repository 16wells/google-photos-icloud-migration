"""
Tests for state manager utilities.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from google_photos_icloud_migration.utils.state_manager import (
    StateManager,
    ZipProcessingState,
)


class TestZipProcessingState:
    """Tests for ZipProcessingState enum."""
    
    def test_state_enum_values(self):
        """Test that all expected states exist."""
        assert ZipProcessingState.PENDING.value == "pending"
        assert ZipProcessingState.DOWNLOADED.value == "downloaded"
        assert ZipProcessingState.EXTRACTED.value == "extracted"
        assert ZipProcessingState.CONVERTED.value == "converted"
        assert ZipProcessingState.UPLOADED.value == "uploaded"
        assert ZipProcessingState.FAILED_EXTRACTION.value == "failed_extraction"
        assert ZipProcessingState.FAILED_UPLOAD.value == "failed_upload"


class TestStateManager:
    """Tests for StateManager class."""
    
    def test_state_manager_initialization(self, tmp_path):
        """Test initializing state manager."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        assert manager.state_file == state_file
        assert isinstance(manager._zip_state, dict)
    
    def test_load_state_nonexistent_file(self, tmp_path):
        """Test loading state from nonexistent file."""
        state_file = tmp_path / "nonexistent_state.json"
        manager = StateManager(state_file)
        
        # Should initialize empty state
        assert isinstance(manager._zip_state, dict)
        assert len(manager._zip_state) == 0
    
    def test_load_state_existing_file(self, tmp_path):
        """Test loading state from existing file."""
        state_file = tmp_path / "state.json"
        state_data = {
            "zip_files": {
                "test.zip": {
                    "state": "uploaded",
                    "files": {}
                }
            }
        }
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f)
        
        manager = StateManager(state_file)
        assert "test.zip" in manager._zip_state
        assert manager._zip_state["test.zip"]["state"] == "uploaded"
    
    def test_save_state(self, tmp_path):
        """Test saving state to file."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.UPLOADED)
        manager.save_state()
        
        assert state_file.exists()
        with open(state_file, 'r') as f:
            saved_data = json.load(f)
        
        assert "test.zip" in saved_data["zip_files"]
        assert saved_data["zip_files"]["test.zip"]["state"] == "uploaded"
    
    def test_set_zip_state(self, tmp_path):
        """Test setting zip file state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.EXTRACTED)
        
        assert "test.zip" in manager._zip_state
        assert manager._zip_state["test.zip"]["state"] == "extracted"
    
    def test_get_zip_state(self, tmp_path):
        """Test getting zip file state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.CONVERTED)
        state = manager.get_zip_state("test.zip")
        
        assert state == ZipProcessingState.CONVERTED
    
    def test_get_zip_state_nonexistent(self, tmp_path):
        """Test getting state for nonexistent zip."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        state = manager.get_zip_state("nonexistent.zip")
        assert state == ZipProcessingState.PENDING
    
    def test_set_file_state(self, tmp_path):
        """Test setting individual file state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.EXTRACTED)
        manager.set_file_state("test.zip", "photo.jpg", "processed")
        
        zip_data = manager._zip_state["test.zip"]
        assert "files" in zip_data
        assert zip_data["files"]["photo.jpg"] == "processed"
    
    def test_get_file_state(self, tmp_path):
        """Test getting individual file state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.EXTRACTED)
        manager.set_file_state("test.zip", "photo.jpg", "uploaded")
        
        file_state = manager.get_file_state("test.zip", "photo.jpg")
        assert file_state == "uploaded"
    
    def test_get_file_state_nonexistent(self, tmp_path):
        """Test getting state for nonexistent file."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("test.zip", ZipProcessingState.EXTRACTED)
        file_state = manager.get_file_state("test.zip", "nonexistent.jpg")
        
        assert file_state is None
    
    def test_get_completed_zips(self, tmp_path):
        """Test getting list of completed zip files."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("completed1.zip", ZipProcessingState.UPLOADED)
        manager.set_zip_state("completed2.zip", ZipProcessingState.UPLOADED)
        manager.set_zip_state("in_progress.zip", ZipProcessingState.EXTRACTED)
        
        completed = manager.get_completed_zips()
        
        assert "completed1.zip" in completed
        assert "completed2.zip" in completed
        assert "in_progress.zip" not in completed
    
    def test_get_failed_zips(self, tmp_path):
        """Test getting list of failed zip files."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)
        
        manager.set_zip_state("failed1.zip", ZipProcessingState.FAILED_EXTRACTION)
        manager.set_zip_state("failed2.zip", ZipProcessingState.FAILED_UPLOAD)
        manager.set_zip_state("success.zip", ZipProcessingState.UPLOADED)
        
        failed = manager.get_failed_zips()
        
        assert "failed1.zip" in failed
        assert "failed2.zip" in failed
        assert "success.zip" not in failed
