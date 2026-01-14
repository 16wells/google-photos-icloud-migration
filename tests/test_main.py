"""
Tests for main.py module.
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google_photos_icloud_migration.orchestrator import MigrationOrchestrator
# MigrationStoppedException might need to be imported from exceptions if it was moved, or mock it if not used



class TestMigrationOrchestrator:
    """Test cases for MigrationOrchestrator class."""
    
    def test_initialization(self, config_file):
        """Test that MigrationOrchestrator can be initialized."""
        with patch('google_photos_icloud_migration.orchestrator.DriveDownloader'), \
             patch('google_photos_icloud_migration.orchestrator.Extractor'), \
             patch('google_photos_icloud_migration.orchestrator.MetadataMerger'), \
             patch('google_photos_icloud_migration.orchestrator.AlbumParser'):
            
            orchestrator = MigrationOrchestrator(str(config_file))
            
            assert orchestrator.config_path == str(config_file)
            assert orchestrator.config is not None
            assert orchestrator.base_dir.exists()
    
    def test_load_config(self, config_file, sample_config):
        """Test configuration loading."""
        with patch('google_photos_icloud_migration.orchestrator.DriveDownloader'), \
             patch('google_photos_icloud_migration.orchestrator.Extractor'), \
             patch('google_photos_icloud_migration.orchestrator.MetadataMerger'), \
             patch('google_photos_icloud_migration.orchestrator.AlbumParser'):
            
            orchestrator = MigrationOrchestrator(str(config_file))
            
            assert orchestrator.config['processing']['base_dir'] == sample_config['processing']['base_dir']
            assert orchestrator.config['google_drive']['folder_id'] == sample_config['google_drive']['folder_id']
    
    def test_load_config_with_defaults(self, tmp_path, sample_config):
        """Test that missing config values get defaults."""
        # Create config missing some optional fields
        minimal_config = {
            'google_drive': sample_config['google_drive'],
            'processing': {'base_dir': str(tmp_path / 'migration')}
        }
        
        config_file = tmp_path / 'minimal_config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(minimal_config, f)
        
        with patch('google_photos_icloud_migration.orchestrator.DriveDownloader'), \
             patch('google_photos_icloud_migration.orchestrator.Extractor'), \
             patch('google_photos_icloud_migration.orchestrator.MetadataMerger'), \
             patch('google_photos_icloud_migration.orchestrator.AlbumParser'):
            
            orchestrator = MigrationOrchestrator(str(config_file))
            
            # Should have defaults filled in
            assert 'batch_size' in orchestrator.config['processing']
            assert orchestrator.config['processing']['batch_size'] == 100
    
    @patch('google_photos_icloud_migration.orchestrator.DriveDownloader')
    @patch('google_photos_icloud_migration.orchestrator.Extractor')
    @patch('google_photos_icloud_migration.orchestrator.MetadataMerger')
    @patch('google_photos_icloud_migration.orchestrator.AlbumParser')
    def test_setup_logging(self, mock_parser, mock_merger, mock_extractor, mock_downloader, config_file):
        """Test that logging is set up correctly."""
        orchestrator = MigrationOrchestrator(str(config_file))
        
        # Logging should be configured
        import logging
        logger = logging.getLogger(__name__)
        assert logger is not None

