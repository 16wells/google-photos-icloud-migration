#!/usr/bin/env python3
"""
Main script for migrating Google Photos to iCloud Photos.

Runs the same migration as the `photo-migrate` command, so both entry points
use one orchestrator (google_photos_icloud_migration.cli.main).
"""
import sys
from pathlib import Path

# Add project root to python path to allow imports from package
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google_photos_icloud_migration.cli.main import main


if __name__ == '__main__':
    main()
