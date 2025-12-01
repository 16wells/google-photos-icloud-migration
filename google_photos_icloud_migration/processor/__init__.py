"""File processing modules (extraction and metadata merging)."""

from google_photos_icloud_migration.processor.extractor import Extractor
from google_photos_icloud_migration.processor.metadata_merger import MetadataMerger
from google_photos_icloud_migration.processor.video_converter import VideoConverter

__all__ = ['Extractor', 'MetadataMerger', 'VideoConverter']

