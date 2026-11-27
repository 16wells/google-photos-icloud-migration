"""
Tests for DriveDownloader.list_zip_files query building and pagination.

The downloader is created without running its OAuth step, so these tests never
reach Google or write a token file.
"""
from unittest.mock import MagicMock

from google_photos_icloud_migration.downloader.drive_downloader import DriveDownloader


def make_downloader(pages):
    """Build a DriveDownloader whose Drive service returns the given result pages."""
    downloader = DriveDownloader.__new__(DriveDownloader)
    downloader.credentials_file = "unused.json"
    service = MagicMock()
    service.files.return_value.list.return_value.execute.side_effect = pages
    downloader.service = service
    return downloader, service


def list_calls(service):
    return service.files.return_value.list.call_args_list


def test_folder_filter_applies_to_every_zip_type():
    downloader, service = make_downloader([{"files": []}])

    downloader.list_zip_files(folder_id="FOLDER123")

    query = list_calls(service)[0].kwargs["q"]
    or_group_end = query.index(")")
    assert query.startswith("(")
    assert " or " not in query[or_group_end:]
    assert query.index("'FOLDER123' in parents") > or_group_end


def test_query_includes_x_zip_type_used_by_google_takeout():
    downloader, service = make_downloader([{"files": []}])

    downloader.list_zip_files()

    query = list_calls(service)[0].kwargs["q"]
    assert "mimeType='application/x-zip'" in query


def test_query_excludes_trashed_files():
    downloader, service = make_downloader([{"files": []}])

    downloader.list_zip_files(folder_id="FOLDER123")

    assert "trashed=false" in list_calls(service)[0].kwargs["q"]


def test_follows_next_page_token_until_last_page():
    page_one = {"files": [{"id": "1", "name": "takeout-001.zip"}], "nextPageToken": "TOKEN2"}
    page_two = {"files": [{"id": "2", "name": "takeout-002.zip"}]}
    downloader, service = make_downloader([page_one, page_two])

    files = downloader.list_zip_files(folder_id="FOLDER123")

    assert [f["id"] for f in files] == ["1", "2"]
    calls = list_calls(service)
    assert "nextPageToken" in calls[0].kwargs["fields"]
    assert calls[1].kwargs["pageToken"] == "TOKEN2"


def test_pattern_keeps_only_matching_names():
    page = {"files": [{"id": "1", "name": "takeout-001.zip"}, {"id": "2", "name": "wallpapers.zip"}]}
    downloader, _ = make_downloader([page])

    files = downloader.list_zip_files(pattern="takeout-*.zip")

    assert [f["name"] for f in files] == ["takeout-001.zip"]
