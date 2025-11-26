"""
Backward-compatible entry point for the migration tool.

This file imports from the package structure to maintain compatibility
with existing scripts and documentation.
"""
from google_photos_icloud_migration.cli.main import main

if __name__ == '__main__':
    main()
