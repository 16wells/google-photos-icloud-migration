Configuration Guide
====================

This guide covers all configuration options for the Google Photos to iCloud Migration tool.

Configuration File
------------------

The tool uses a YAML configuration file (``config.yaml``) for settings. See ``config.yaml.example`` for a complete example.

Basic Structure
---------------

.. code-block:: yaml

   google_drive:
     # Google Drive API configuration
   
   icloud:
     # iCloud/PhotoKit configuration (macOS only)
   
   processing:
     # Processing configuration
   
   metadata:
     # Metadata preservation options
   
   logging:
     # Logging configuration

Google Drive Configuration
--------------------------

.. code-block:: yaml

   google_drive:
     credentials_file: "credentials.json"  # Required: Path to OAuth credentials
     folder_id: "optional_folder_id"       # Optional: Specific folder ID
     zip_file_pattern: "takeout-*.zip"     # Pattern to match zip files

iCloud Configuration
--------------------

.. code-block:: yaml

   icloud:
     # Note: No credentials needed for PhotoKit method
     # The tool uses your macOS iCloud account automatically
     photos_library_path: null  # Optional: Custom Photos library path
     method: "photokit"         # Only method: PhotoKit sync (macOS only)

Processing Configuration
------------------------

.. code-block:: yaml

   processing:
     base_dir: "/tmp/google-photos-migration"  # Required: Base directory
     zip_dir: "zips"                           # Zip files directory
     extracted_dir: "extracted"                # Extracted files directory
     processed_dir: "processed"                # Processed files directory
     batch_size: 100                           # Files per batch
     cleanup_after_upload: true                # Clean up after upload
     max_workers: null                         # Parallel workers (null = auto)
     enable_parallel_processing: true          # Enable parallel processing

Metadata Configuration
----------------------

.. code-block:: yaml

   metadata:
     preserve_dates: true        # Preserve photo dates
     preserve_gps: true          # Preserve GPS coordinates
     preserve_descriptions: true # Preserve descriptions/captions
     preserve_albums: true       # Preserve album organization

Logging Configuration
---------------------

.. code-block:: yaml

   logging:
     level: "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL
     file: "migration.log"   # Log file path

Environment Variables
---------------------

You can override configuration values using environment variables. Create a ``.env`` file:

.. code-block:: bash

   # Google Drive credentials
   GOOGLE_DRIVE_CREDENTIALS_FILE=path/to/credentials.json

   # Optional: GitHub token for repository scripts
   GITHUB_TOKEN=your_token_here

Environment variables take precedence over ``config.yaml`` values.

Configuration Validation
------------------------

The tool validates your configuration against a JSON schema. Invalid configurations will show clear error messages indicating what needs to be fixed.

For more details, see the API documentation on :class:`MigrationConfig`.
