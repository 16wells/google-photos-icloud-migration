"""
Test utilities and helper functions.
"""
import json
import zipfile
from pathlib import Path
from typing import Dict, List


def create_test_zip(zip_path: Path, files: Dict[str, str]) -> None:
    """
    Create a test zip file with specified files.
    
    Args:
        zip_path: Path where zip file should be created
        files: Dictionary mapping file paths within zip to content (str)
    """
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file_path, content in files.items():
            zf.writestr(file_path, content)


def create_test_json(json_path: Path, data: Dict) -> None:
    """
    Create a test JSON file.
    
    Args:
        json_path: Path where JSON file should be created
        data: Dictionary to serialize to JSON
    """
    with open(json_path, 'w') as f:
        json.dump(data, f)


def create_test_image(image_path: Path, size: int = 100) -> None:
    """
    Create a fake image file for testing.
    
    Args:
        image_path: Path where image file should be created
        size: Size of fake image data in bytes
    """
    image_path.write_bytes(b'\xff' * size)


def create_test_video(video_path: Path, size: int = 1000) -> None:
    """
    Create a fake video file for testing.
    
    Args:
        video_path: Path where video file should be created
        size: Size of fake video data in bytes
    """
    video_path.write_bytes(b'\x00' * size)

