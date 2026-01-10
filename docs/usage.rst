Usage Guide
============

This guide covers how to use the Google Photos to iCloud Migration tool.

Basic Usage
-----------

**Process local zip files:**

.. code-block:: bash

   python3 process_local_zips.py --takeout-dir "/path/to/your/zips"

**Download from Google Drive and process:**

.. code-block:: bash

   python3 main.py --config config.yaml

Command Line Options
--------------------

**main.py options:**

.. code-block:: bash

   python3 main.py --config config.yaml [OPTIONS]

   Options:
     --config PATH              Path to config file (required)
     --retry-failed             Retry previously failed uploads
     --retry-failed-extractions Retry failed extractions
     --redownload-zips          Re-download zip files for failed uploads

**process_local_zips.py options:**

.. code-block:: bash

   python3 process_local_zips.py [OPTIONS]

   Options:
     --takeout-dir PATH         Directory containing zip files (required)
     --config PATH              Path to config file (default: config.yaml)
     --skip-processed           Skip already-processed zip files
     --retry-failed             Retry previously failed uploads
     --no-cleanup               Don't clean up extracted files after processing

Migration Process
-----------------

The migration process consists of several phases:

1. **Phase 1: Download** (if using Google Drive)
   - Lists zip files from Google Drive
   - Downloads zip files matching the pattern

2. **Phase 2: Extract**
   - Extracts zip files maintaining directory structure
   - Organizes files for processing

3. **Phase 3: Process Metadata**
   - Merges JSON metadata into media files using ExifTool
   - Preserves dates, GPS coordinates, and descriptions

4. **Phase 4: Parse Albums**
   - Extracts album structure from directory hierarchy
   - Maps files to album names

5. **Phase 5: Upload**
   - Uploads files to iCloud Photos using PhotoKit
   - Organizes files into albums

6. **Phase 6: Cleanup** (if enabled)
   - Removes temporary extracted files
   - Frees up disk space

Progress Tracking
-----------------

The tool automatically tracks progress using a state file (``zip_processing_state.json``). This allows:

* **Resuming** after interruptions
* **Skipping** already-processed files
* **Retrying** failed uploads without re-processing

Error Handling
--------------

The tool includes comprehensive error handling:

* **Automatic retries** for transient failures
* **State tracking** to resume from last successful point
* **Detailed logging** for troubleshooting
* **Verification** after upload (optional)

For troubleshooting, see the error messages and check ``migration.log``.

Monitoring Progress
-------------------

View progress in real-time:

.. code-block:: bash

   tail -f migration.log

Or use the statistics report:

.. code-block:: bash

   python3 migration_statistics.py

Advanced Usage
--------------

For advanced usage patterns, see:
* :doc:`api` for API documentation
* Individual module documentation for detailed options
