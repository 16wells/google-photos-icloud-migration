"""
Pytest configuration and shared fixtures.
"""
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

import pytest
import yaml


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def sample_config(tmp_path) -> Dict:
    """Fixture providing a sample configuration dictionary."""
    return {
        'google_drive': {
            'credentials_file': str(tmp_path / 'credentials.json'),
            'folder_id': 'test_folder_id',
            'zip_file_pattern': 'takeout-*.zip'
        },
        'icloud': {
            'apple_id': 'test@example.com',
            'password': '',
            'trusted_device_id': None,
            'two_fa_code': None
        },
        'processing': {
            'base_dir': str(tmp_path / 'migration'),
            'zip_dir': 'zips',
            'extracted_dir': 'extracted',
            'processed_dir': 'processed',
            'batch_size': 10,
            'cleanup_after_upload': False,
            'enable_parallel_processing': True,
            'max_workers': 2
        },
        'metadata': {
            'preserve_dates': True,
            'preserve_gps': True,
            'preserve_descriptions': True,
            'preserve_albums': True
        },
        'logging': {
            'level': 'INFO',
            'file': 'migration.log'
        }
    }


@pytest.fixture
def config_file(tmp_path, sample_config) -> Path:
    """Create a temporary config.yaml file."""
    config_path = tmp_path / 'config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def credentials_file(tmp_path) -> Path:
    """Create a mock credentials.json file."""
    creds_file = tmp_path / 'credentials.json'
    creds_data = {
        'installed': {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['http://localhost']
        }
    }
    with open(creds_file, 'w') as f:
        json.dump(creds_data, f)
    return creds_file


@pytest.fixture
def sample_metadata_json(tmp_path) -> Path:
    """Create a sample metadata JSON file."""
    metadata_file = tmp_path / 'sample.json'
    metadata = {
        'title': 'Test Photo',
        'photoTakenTime': {
            'timestamp': '1609459200',
            'formatted': '2021-01-01 00:00:00 UTC'
        },
        'geoData': {
            'latitude': 37.7749,
            'longitude': -122.4194
        },
        'description': 'Test description'
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f)
    return metadata_file


@pytest.fixture
def sample_zip_file(tmp_path) -> Path:
    """Create a sample zip file with test content."""
    zip_path = tmp_path / 'test.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Add a sample image file
        zf.writestr('Takeout/Photos/test.jpg', b'fake image data')
        # Add corresponding JSON metadata
        metadata = {
            'title': 'Test Photo',
            'photoTakenTime': {'timestamp': '1609459200'}
        }
        zf.writestr('Takeout/Photos/test.jpg.json', json.dumps(metadata))
        # Add another file
        zf.writestr('Takeout/Photos/test2.jpg', b'fake image data 2')
    return zip_path


@pytest.fixture
def mock_drive_service():
    """Create a mock Google Drive service."""
    service = Mock()
    
    # Mock files list response
    files_list = Mock()
    files_list.execute.return_value = {
        'files': [
            {
                'id': 'file1',
                'name': 'takeout-001.zip',
                'size': '1024000',
                'mimeType': 'application/zip'
            },
            {
                'id': 'file2',
                'name': 'takeout-002.zip',
                'size': '2048000',
                'mimeType': 'application/zip'
            }
        ],
        'nextPageToken': None
    }
    
    service.files.return_value.list.return_value = files_list
    return service


@pytest.fixture
def mock_photo_library():
    """Create a mock PhotoKit library for testing."""
    library = Mock()
    library.authorizationStatus.return_value = 3  # Authorized
    return library

