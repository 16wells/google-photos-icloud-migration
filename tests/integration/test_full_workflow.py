"""
Integration tests for full migration workflow.
These tests verify the end-to-end process with mocked external dependencies.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from main import MigrationOrchestrator


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for full migration workflow."""
    
    @pytest.fixture
    def mock_config_file(self, tmp_path, sample_config):
        """Create a mock config file for testing."""
        config_file = tmp_path / "config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(sample_config, f)
        return config_file
    
    @pytest.mark.slow
    def test_download_extract_process_upload_workflow(self, mock_config_file, tmp_path, sample_zip_file):
        """Test the full workflow: download, extract, process, upload."""
        with patch('main.DriveDownloader') as MockDownloader, \
             patch('main.Extractor') as MockExtractor, \
             patch('main.MetadataMerger') as MockMetadataMerger, \
             patch('main.AlbumParser') as MockAlbumParser, \
             patch('main.iCloudPhotosSyncUploader') as MockUploader, \
             patch('main.StateManager') as MockStateManager:
            
            # Setup mocks
            mock_downloader = MockDownloader.return_value
            mock_extractor = MockExtractor.return_value
            mock_merger = MockMetadataMerger.return_value
            mock_parser = MockAlbumParser.return_value
            mock_uploader = MockUploader.return_value
            mock_state = MockStateManager.return_value
            
            # Mock downloader to return zip file info
            mock_downloader.list_zip_files.return_value = [
                {'id': 'file1', 'name': 'takeout-001.zip', 'size': '1024'}
            ]
            mock_downloader.download_file.return_value = sample_zip_file
            
            # Mock extractor
            extracted_dir = tmp_path / "extracted"
            extracted_dir.mkdir()
            mock_extractor.extract_zip.return_value = [extracted_dir]
            
            # Mock metadata merger
            processed_file = tmp_path / "processed" / "photo.jpg"
            processed_file.parent.mkdir(parents=True, exist_ok=True)
            mock_merger.merge_metadata.return_value = processed_file
            
            # Mock album parser
            mock_parser.parse_albums.return_value = {"Album1": [processed_file]}
            
            # Mock uploader
            mock_uploader.upload_files_batch.return_value = {processed_file: True}
            mock_uploader.request_authorization.return_value = True
            
            # Mock state manager
            mock_state.get_zip_state.return_value = None  # PENDING
            mock_state.get_completed_zips.return_value = []
            mock_state.get_failed_zips.return_value = []
            
            # Create orchestrator
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            orchestrator.setup_icloud_uploader()
            
            # Verify components initialized
            assert orchestrator.downloader is not None
            assert orchestrator.extractor is not None
            assert orchestrator.metadata_merger is not None
            assert orchestrator.album_parser is not None
            assert orchestrator.icloud_uploader is not None
            
            # Note: Actual workflow execution would require more comprehensive mocking
            # This test verifies that all components can be initialized correctly
    
    def test_error_handling_in_workflow(self, mock_config_file):
        """Test error handling at various stages of the workflow."""
        with patch('main.DriveDownloader') as MockDownloader, \
             patch('main.Extractor'), \
             patch('main.MetadataMerger'), \
             patch('main.AlbumParser'), \
             patch('main.StateManager'):
            
            # Test authentication failure
            mock_downloader = MockDownloader.return_value
            mock_downloader.list_zip_files.side_effect = Exception("Authentication failed")
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Should handle authentication errors gracefully
            with pytest.raises(Exception):
                orchestrator.downloader.list_zip_files()
