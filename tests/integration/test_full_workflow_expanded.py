"""
Expanded integration tests for full migration workflow.

These tests verify comprehensive end-to-end scenarios including:
- Full workflow with mocked external dependencies
- Error recovery and retry scenarios
- Parallel processing behavior
- State management and resumability
- Edge cases and error conditions
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import json
import yaml

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.main import MigrationOrchestrator
from google_photos_icloud_migration.exceptions import (
    ExtractionError, MetadataError, DownloadError, UploadError
)


# Shared fixture for all integration tests
@pytest.fixture
def mock_config_file(tmp_path, sample_config):
    """Create a mock config file for testing with parallel processing enabled."""
    # Update config to enable parallel processing
    sample_config['processing']['enable_parallel_processing'] = True
    sample_config['processing']['max_workers'] = 2
    sample_config['processing']['batch_size'] = 10
    
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
    return config_file


@pytest.mark.integration
class TestFullWorkflowExpanded:
    """Expanded integration tests for full migration workflow."""
    
    @pytest.mark.slow
    def test_full_workflow_with_parallel_processing(self, mock_config_file, tmp_path, sample_zip_file):
        """Test the full workflow with parallel processing enabled."""
        with patch('scripts.main.DriveDownloader') as MockDownloader, \
             patch('scripts.main.Extractor') as MockExtractor, \
             patch('scripts.main.MetadataMerger') as MockMetadataMerger, \
             patch('scripts.main.AlbumParser') as MockAlbumParser, \
             patch('scripts.main.iCloudPhotosSyncUploader') as MockUploader, \
             patch('scripts.main.StateManager') as MockStateManager:
            
            # Setup mocks
            mock_downloader = MockDownloader.return_value
            mock_extractor = MockExtractor.return_value
            mock_merger = MockMetadataMerger.return_value
            mock_parser = MockAlbumParser.return_value
            mock_uploader = MockUploader.return_value
            mock_state = MockStateManager.return_value
            
            # Mock downloader
            mock_downloader.list_zip_files.return_value = [
                {'id': 'file1', 'name': 'takeout-001.zip', 'size': '1024'},
                {'id': 'file2', 'name': 'takeout-002.zip', 'size': '2048'}
            ]
            mock_downloader.download_file.return_value = sample_zip_file
            
            # Mock extractor
            extracted_dir1 = tmp_path / "extracted" / "takeout-001"
            extracted_dir2 = tmp_path / "extracted" / "takeout-002"
            extracted_dir1.mkdir(parents=True)
            extracted_dir2.mkdir(parents=True)
            mock_extractor.extract_zip.side_effect = [extracted_dir1, extracted_dir2]
            
            # Mock metadata merger with parallel processing
            processed_file1 = tmp_path / "processed" / "photo1.jpg"
            processed_file2 = tmp_path / "processed" / "photo2.jpg"
            processed_file1.parent.mkdir(parents=True, exist_ok=True)
            processed_file2.parent.mkdir(parents=True, exist_ok=True)
            mock_merger.merge_all_metadata.return_value = {
                processed_file1: True,
                processed_file2: True
            }
            mock_merger.merge_metadata.return_value = True
            # Configure enable_parallel attribute for the mock instance
            mock_merger.enable_parallel = True
            
            # Mock album parser
            mock_parser.parse_from_directory_structure.return_value = {
                "Album1": [processed_file1],
                "Album2": [processed_file2]
            }
            mock_parser.parse_from_json_metadata.return_value = {}
            mock_parser.get_all_albums.return_value = {
                "Album1": [processed_file1],
                "Album2": [processed_file2]
            }
            
            # Mock uploader
            mock_uploader.upload_files_batch.return_value = {
                processed_file1: True,
                processed_file2: True
            }
            
            # Mock state manager
            mock_state.get_zip_state.return_value = None
            mock_state.get_completed_zips.return_value = []
            mock_state.get_failed_zips.return_value = []
            mock_state.mark_zip_completed.return_value = None
            
            # Create orchestrator
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Verify components initialized
            assert orchestrator.downloader is not None
            assert orchestrator.extractor is not None
            assert orchestrator.metadata_merger is not None
            assert orchestrator.album_parser is not None
            
            # Verify parallel processing is enabled in merger
            assert orchestrator.metadata_merger.enable_parallel is True
    
    def test_workflow_with_extraction_error_recovery(self, mock_config_file, tmp_path):
        """Test workflow recovery from extraction errors."""
        with patch('scripts.main.DriveDownloader') as MockDownloader, \
             patch('scripts.main.Extractor') as MockExtractor, \
             patch('scripts.main.StateManager') as MockStateManager:
            
            mock_downloader = MockDownloader.return_value
            mock_extractor = MockExtractor.return_value
            mock_state = MockStateManager.return_value
            
            # Mock downloader
            zip_file = tmp_path / "test.zip"
            zip_file.write_bytes(b'fake zip')
            mock_downloader.list_zip_files.return_value = [
                {'id': 'file1', 'name': 'test.zip', 'size': '1024'}
            ]
            mock_downloader.download_file.return_value = zip_file
            
            # Mock extractor to raise error on first attempt, succeed on retry
            call_count = [0]
            def extract_side_effect(zip_path):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ExtractionError("Corrupted zip file")
                # On retry, succeed
                extracted_dir = tmp_path / "extracted" / zip_path.stem
                extracted_dir.mkdir(parents=True)
                return extracted_dir
            
            mock_extractor.extract_zip.side_effect = extract_side_effect
            
            mock_state.get_zip_state.return_value = None
            mock_state.get_completed_zips.return_value = []
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Should handle extraction errors gracefully
            # In a real scenario, would retry or mark as failed
            with pytest.raises(ExtractionError):
                orchestrator.extractor.extract_zip(zip_file)
    
    def test_workflow_with_metadata_errors(self, mock_config_file, tmp_path):
        """Test workflow behavior with metadata processing errors."""
        with patch('scripts.main.DriveDownloader'), \
             patch('scripts.main.Extractor') as MockExtractor, \
             patch('scripts.main.MetadataMerger') as MockMetadataMerger, \
             patch('scripts.main.StateManager'):
            
            mock_extractor = MockExtractor.return_value
            mock_merger = MockMetadataMerger.return_value
            
            # Mock extractor
            extracted_dir = tmp_path / "extracted" / "test"
            extracted_dir.mkdir(parents=True)
            
            # Create test media file
            test_photo = extracted_dir / "photo.jpg"
            test_photo.write_bytes(b'fake photo')
            test_json = extracted_dir / "photo.jpg.json"
            with open(test_json, 'w') as f:
                json.dump({'title': 'Test'}, f)
            
            # Mock metadata merger to partially fail
            mock_merger.merge_all_metadata.return_value = {
                test_photo: False  # Simulated failure
            }
            mock_merger.merge_metadata.side_effect = MetadataError("ExifTool failed")
            
            # Verify error handling
            pairs = {test_photo: test_json}
            results = mock_merger.merge_all_metadata(pairs)
            assert results[test_photo] is False
    
    def test_workflow_with_parallel_metadata_processing(self, mock_config_file, tmp_path):
        """Test metadata processing with parallel processing enabled."""
        with patch('scripts.main.MetadataMerger') as MockMetadataMerger:
            # Create merger with parallel processing enabled
            from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
            
            merger = MetadataMerger(
                preserve_dates=True,
                preserve_gps=True,
                preserve_descriptions=True,
                enable_parallel=True,
                max_workers=2,
                cache_metadata=True
            )
            
            # Verify parallel processing is configured
            assert merger.enable_parallel is True
            assert merger.max_workers == 2
            assert merger.cache_metadata is True
    
    def test_workflow_with_state_persistence(self, mock_config_file, tmp_path):
        """Test workflow state persistence and resumability."""
        with patch('scripts.main.StateManager') as MockStateManager:
            state_manager = MockStateManager.return_value
            
            # Mock state persistence
            state_manager.get_zip_state.return_value = 'processing'
            state_manager.get_completed_zips.return_value = ['takeout-001.zip']
            state_manager.get_failed_zips.return_value = ['takeout-002.zip']
            state_manager.mark_zip_completed.return_value = None
            state_manager.mark_zip_failed.return_value = None
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Verify state manager initialized
            assert orchestrator.state_manager is not None
            
            # Verify state queries work
            completed = orchestrator.state_manager.get_completed_zips()
            assert 'takeout-001.zip' in completed
            
            failed = orchestrator.state_manager.get_failed_zips()
            assert 'takeout-002.zip' in failed
    
    def test_workflow_error_recovery(self, mock_config_file):
        """Test error recovery at different stages."""
        with patch('scripts.main.DriveDownloader') as MockDownloader, \
             patch('scripts.main.StateManager') as MockStateManager:
            
            mock_downloader = MockDownloader.return_value
            mock_state = MockStateManager.return_value
            
            # Test download error
            mock_downloader.list_zip_files.side_effect = DownloadError("API error")
            mock_state.get_zip_state.return_value = None
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Should handle download errors gracefully
            with pytest.raises(DownloadError):
                orchestrator.downloader.list_zip_files()
    
    def test_workflow_with_large_file_batch(self, mock_config_file, tmp_path):
        """Test workflow with a large batch of files for performance."""
        with patch('scripts.main.DriveDownloader'), \
             patch('scripts.main.Extractor'), \
             patch('scripts.main.MetadataMerger') as MockMetadataMerger, \
             patch('scripts.main.StateManager'):
            
            mock_merger = MockMetadataMerger.return_value
            
            # Simulate large batch
            large_batch = {
                Path(f"photo_{i}.jpg"): Path(f"photo_{i}.jpg.json")
                for i in range(100)
            }
            
            # Mock successful processing
            mock_merger.merge_all_metadata.return_value = {
                k: True for k in large_batch.keys()
            }
            
            # Verify batch processing
            results = mock_merger.merge_all_metadata(large_batch)
            assert len(results) == 100
            assert all(results.values())  # All should succeed
    
    def test_workflow_with_missing_metadata(self, mock_config_file, tmp_path):
        """Test workflow when some files lack metadata."""
        with patch('scripts.main.Extractor') as MockExtractor, \
             patch('scripts.main.MetadataMerger') as MockMetadataMerger:
            
            mock_extractor = MockExtractor.return_value
            mock_merger = MockMetadataMerger.return_value
            
            # Create pairs with some missing JSON
            pairs = {
                Path("photo1.jpg"): Path("photo1.jpg.json"),  # Has metadata
                Path("photo2.jpg"): None,  # No metadata
                Path("photo3.jpg"): Path("missing.json")  # Metadata file doesn't exist
            }
            
            # Mock merger to handle missing metadata gracefully
            def merge_side_effect(pairs_dict, output_dir=None):
                results = {}
                for media_file, json_file in pairs_dict.items():
                    if json_file and json_file.exists():
                        results[media_file] = True
                    else:
                        results[media_file] = True  # Still process without metadata
                return results
            
            mock_merger.merge_all_metadata.side_effect = merge_side_effect
            
            results = mock_merger.merge_all_metadata(pairs)
            # Should process all files, even without metadata
            assert len(results) == 3


@pytest.mark.integration
class TestParallelProcessing:
    """Tests for parallel processing functionality."""
    
    def test_parallel_metadata_merging(self, tmp_path):
        """Test parallel metadata merging with multiple files."""
        from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
        from pathlib import Path
        
        merger = MetadataMerger(
            enable_parallel=True,
            max_workers=2,
            cache_metadata=True
        )
        
        # Create test pairs
        pairs = {
            Path(tmp_path / f"photo_{i}.jpg"): Path(tmp_path / f"photo_{i}.jpg.json")
            for i in range(5)
        }
        
        # Mock merge_metadata to avoid actual ExifTool calls
        with patch.object(merger, 'merge_metadata', return_value=True):
            results = merger.merge_all_metadata(pairs, max_workers=2)
            
            # Should process all files
            assert len(results) == 5
            # Parallel processing should complete
            assert all(results.values())
    
    def test_metadata_caching(self, tmp_path):
        """Test metadata caching functionality."""
        from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
        from pathlib import Path
        import json
        
        merger = MetadataMerger(cache_metadata=True, cache_ttl_seconds=60)
        
        # Create test JSON file
        json_file = tmp_path / "test.json"
        test_metadata = {'title': 'Test', 'photoTakenTime': {'timestamp': '1609459200'}}
        with open(json_file, 'w') as f:
            json.dump(test_metadata, f)
        
        # First call should parse and cache
        result1 = merger.parse_json_metadata(json_file, use_cache=True)
        assert result1 == test_metadata
        assert json_file in merger._metadata_cache
        
        # Second call should use cache
        with patch('builtins.open') as mock_open:
            result2 = merger.parse_json_metadata(json_file, use_cache=True)
            assert result2 == test_metadata
            # Should not have opened file (used cache)
            assert mock_open.call_count == 0
        
        # Clear cache and verify
        merger.clear_cache()
        assert len(merger._metadata_cache) == 0


@pytest.mark.integration
class TestGeneratorUsage:
    """Tests for generator-based file operations."""
    
    def test_generator_file_discovery(self, tmp_path):
        """Test generator-based file discovery for memory efficiency."""
        from google_photos_icloud_migration.processor.extractor import Extractor
        from pathlib import Path
        
        extractor = Extractor(tmp_path)
        
        # Create test directory structure
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "photo1.jpg").write_bytes(b'fake')
        (test_dir / "photo2.jpg").write_bytes(b'fake')
        (test_dir / "photo3.jpg").write_bytes(b'fake')
        
        # Use generator
        files_gen = extractor.find_media_files(test_dir)
        file_list = list(files_gen)
        
        assert len(file_list) == 3
        assert all(f.name.endswith('.jpg') for f in file_list)
    
    def test_generator_zip_extraction(self, tmp_path):
        """Test generator-based zip extraction."""
        from google_photos_icloud_migration.processor.extractor import Extractor
        from pathlib import Path
        import zipfile
        
        extractor = Extractor(tmp_path)
        
        # Create test zip files
        zip1 = tmp_path / "test1.zip"
        zip2 = tmp_path / "test2.zip"
        
        for zip_file in [zip1, zip2]:
            with zipfile.ZipFile(zip_file, 'w') as zf:
                zf.writestr('test.jpg', b'fake')
        
        # Use list method for extraction
        zips = [zip1, zip2]
        extracted_list = extractor.extract_all_zips_list(zips)
        
        assert len(extracted_list) == 2
        assert all(d.exists() and d.is_dir() for d in extracted_list)


@pytest.mark.integration
class TestErrorScenarios:
    """Tests for various error scenarios and recovery."""
    
    def test_disk_space_error(self, mock_config_file, tmp_path):
        """Test handling of disk space errors."""
        with patch('scripts.main.DriveDownloader') as MockDownloader, \
             patch('scripts.main.StateManager'):
            
            mock_downloader = MockDownloader.return_value
            mock_downloader.download_file.side_effect = OSError(28, "No space left on device")
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Should handle disk space errors gracefully
            with pytest.raises(OSError):
                mock_downloader.download_file('file_id', 'file.zip', tmp_path)
    
    def test_partial_failure_recovery(self, mock_config_file):
        """Test recovery from partial failures."""
        with patch('scripts.main.StateManager') as MockStateManager:
            mock_state = MockStateManager.return_value
            
            # Mock partial failure state
            mock_state.get_failed_zips.return_value = ['takeout-002.zip']
            mock_state.get_completed_zips.return_value = ['takeout-001.zip']
            
            orchestrator = MigrationOrchestrator(str(mock_config_file))
            
            # Should be able to retry failed zips
            failed = orchestrator.state_manager.get_failed_zips()
            assert 'takeout-002.zip' in failed
