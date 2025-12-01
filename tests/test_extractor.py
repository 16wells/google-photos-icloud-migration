"""
Tests for extractor.py module.
"""
import zipfile
from pathlib import Path

import pytest

from google_photos_icloud_migration.processor.extractor import Extractor, MEDIA_EXTENSIONS


class TestExtractor:
    """Test cases for Extractor class."""
    
    def test_initialization(self, tmp_path):
        """Test that Extractor can be initialized."""
        extractor = Extractor(tmp_path)
        
        assert extractor.base_dir == tmp_path
        assert extractor.extracted_dir == tmp_path / "extracted"
        assert extractor.extracted_dir.exists()
    
    def test_extract_zip_file(self, sample_zip_file, tmp_path):
        """Test extracting a zip file."""
        extractor = Extractor(tmp_path)
        extracted_dir = extractor.extract_zip(sample_zip_file)
        
        assert extracted_dir.exists()
        assert (extracted_dir / 'Takeout' / 'Photos' / 'test.jpg').exists()
        assert (extracted_dir / 'Takeout' / 'Photos' / 'test.jpg.json').exists()
    
    def test_extract_invalid_zip(self, tmp_path):
        """Test that invalid zip files raise appropriate exceptions."""
        extractor = Extractor(tmp_path)
        invalid_zip = tmp_path / 'not-a-zip.txt'
        invalid_zip.write_text("This is not a zip file")
        
        with pytest.raises((zipfile.BadZipFile, ValueError)):
            extractor.extract_zip(invalid_zip)
    
    def test_identify_media_json_pairs(self, sample_zip_file, tmp_path):
        """Test identifying media file and JSON metadata pairs."""
        extractor = Extractor(tmp_path)
        extracted_dir = extractor.extract_zip(sample_zip_file)
        
        pairs = extractor.identify_media_json_pairs(extracted_dir)
        
        assert len(pairs) > 0
        # Check that pairs contain media files as keys
        assert all(media_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4', '.mov'] 
                  for media_file in pairs.keys())
        # Check that JSON files exist for each media file
        assert all(json_file.exists() for json_file in pairs.values() if json_file)
    
    def test_identify_media_files_no_json(self, tmp_path):
        """Test identifying media files without corresponding JSON."""
        extractor = Extractor(tmp_path)
        
        # Create a directory with media files but no JSON
        media_dir = tmp_path / 'media'
        media_dir.mkdir()
        (media_dir / 'photo1.jpg').write_bytes(b'fake image')
        (media_dir / 'photo2.png').write_bytes(b'fake image')
        
        pairs = extractor.identify_media_json_pairs(media_dir)
        
        assert len(pairs) == 2
        assert all(json_file is None for json_file in pairs.values())
    
    def test_media_extensions_constant(self):
        """Test that MEDIA_EXTENSIONS contains expected formats."""
        expected_extensions = {'.jpg', '.jpeg', '.heic', '.png', '.gif', '.bmp', '.tiff',
                              '.avi', '.mov', '.mp4', '.m4v', '.3gp', '.mkv'}
        
        assert MEDIA_EXTENSIONS == expected_extensions
    
    def test_extract_nested_structure(self, tmp_path):
        """Test extracting zip files with nested directory structure."""
        extractor = Extractor(tmp_path)
        
        # Create zip with nested structure
        zip_path = tmp_path / 'nested.zip'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('Takeout/Album1/photo1.jpg', b'image data')
            zf.writestr('Takeout/Album1/photo1.jpg.json', '{"title": "Photo 1"}')
            zf.writestr('Takeout/Album2/photo2.jpg', b'image data')
            zf.writestr('Takeout/Album2/photo2.jpg.json', '{"title": "Photo 2"}')
        
        extracted_dir = extractor.extract_zip(zip_path)
        
        assert (extracted_dir / 'Takeout' / 'Album1' / 'photo1.jpg').exists()
        assert (extracted_dir / 'Takeout' / 'Album2' / 'photo2.jpg').exists()

