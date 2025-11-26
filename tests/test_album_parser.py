"""
Tests for album_parser.py module.
"""
from pathlib import Path

import pytest

from album_parser import AlbumParser


class TestAlbumParser:
    """Test cases for AlbumParser class."""
    
    def test_initialization(self):
        """Test that AlbumParser can be initialized."""
        parser = AlbumParser()
        
        assert parser.albums == {}
        assert parser.file_to_album == {}
    
    def test_parse_from_directory_structure(self, tmp_path):
        """Test parsing album structure from directory hierarchy."""
        parser = AlbumParser()
        
        # Create directory structure simulating Google Takeout
        album1_dir = tmp_path / 'Album1'
        album1_dir.mkdir()
        (album1_dir / 'photo1.jpg').write_bytes(b'fake image')
        (album1_dir / 'photo2.jpg').write_bytes(b'fake image')
        
        album2_dir = tmp_path / 'Album2'
        album2_dir.mkdir()
        (album2_dir / 'photo3.jpg').write_bytes(b'fake image')
        
        albums = parser.parse_from_directory_structure(tmp_path)
        
        assert 'Album1' in albums
        assert 'Album2' in albums
        assert len(albums['Album1']) == 2
        assert len(albums['Album2']) == 1
    
    def test_parse_from_directory_structure_case_insensitive(self, tmp_path):
        """Test that album parsing is case-insensitive."""
        parser = AlbumParser()
        
        # Create directories with different cases
        album1_dir = tmp_path / 'Album1'
        album1_dir.mkdir()
        (album1_dir / 'photo1.jpg').write_bytes(b'fake image')
        
        albums = parser.parse_from_directory_structure(tmp_path)
        
        # Should find album regardless of case
        assert len(albums) > 0
    
    def test_clean_album_name(self, tmp_path):
        """Test album name cleaning."""
        parser = AlbumParser()
        
        # Test cleaning common prefixes
        test_names = [
            ('Google Photos/Album1', 'Album1'),
            ('Takeout/Album2', 'Album2'),
        ]
        
        for input_name, expected in test_names:
            cleaned = parser._clean_album_name(input_name)
            # Should remove common prefixes
            assert cleaned == expected or expected in cleaned
    
    def test_file_to_album_mapping(self, tmp_path):
        """Test that file_to_album mapping is created correctly."""
        parser = AlbumParser()
        
        album_dir = tmp_path / 'TestAlbum'
        album_dir.mkdir()
        photo1 = album_dir / 'photo1.jpg'
        photo2 = album_dir / 'photo2.jpg'
        photo1.write_bytes(b'fake image')
        photo2.write_bytes(b'fake image')
        
        parser.parse_from_directory_structure(tmp_path)
        
        assert photo1 in parser.file_to_album
        assert photo2 in parser.file_to_album
        assert parser.file_to_album[photo1] == 'TestAlbum'
        assert parser.file_to_album[photo2] == 'TestAlbum'
    
    def test_parse_ignores_non_media_files(self, tmp_path):
        """Test that non-media files are ignored."""
        parser = AlbumParser()
        
        album_dir = tmp_path / 'Album'
        album_dir.mkdir()
        (album_dir / 'photo.jpg').write_bytes(b'fake image')
        (album_dir / 'readme.txt').write_text('not an image')
        
        albums = parser.parse_from_directory_structure(tmp_path)
        
        # Should only include media files
        assert len(albums['Album']) == 1
        assert (album_dir / 'photo.jpg') in albums['Album']

