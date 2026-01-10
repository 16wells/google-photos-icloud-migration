Google Photos to iCloud Migration Documentation
==================================================

Welcome to the Google Photos to iCloud Migration tool documentation!

This tool helps you migrate photos and videos from Google Photos (exported via Google Takeout) to iCloud Photos, preserving metadata and album structures.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   configuration
   usage
   api
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Overview
--------

The Google Photos to iCloud Migration tool is a comprehensive solution for transferring your photo library from Google Photos to Apple iCloud Photos. It handles:

* **Downloading** Google Takeout zip files from Google Drive
* **Extracting** and organizing photos and videos
* **Processing metadata** to preserve dates, GPS coordinates, and descriptions
* **Uploading** to iCloud Photos using PhotoKit framework (macOS only)
* **Album organization** to maintain your album structure

Key Features
------------

* ✅ **Metadata Preservation**: Maintains photo dates, GPS coordinates, and descriptions
* ✅ **Album Support**: Preserves your album organization
* ✅ **PhotoKit Integration**: Uses Apple's native PhotoKit framework (macOS only)
* ✅ **Progress Tracking**: Resume capability and detailed progress reporting
* ✅ **Error Recovery**: Retry failed uploads without re-processing
* ✅ **Security**: Secure credential storage with macOS Keychain support

Requirements
------------

* Python 3.11 or higher
* macOS with iCloud Photos enabled
* ExifTool installed (`brew install exiftool`)
* Google Drive API credentials (OAuth 2.0)

Quick Start
-----------

.. code-block:: bash

   # Install dependencies
   pip install -r requirements.txt

   # Run authentication setup
   python3 auth_setup.py

   # Run migration
   python3 main.py --config config.yaml

For more details, see :doc:`quickstart`.

Installation
------------

See :doc:`installation` for detailed installation instructions.

Configuration
-------------

See :doc:`configuration` for configuration options and examples.

API Reference
-------------

See :doc:`api` for detailed API documentation.

Contributing
------------

See :doc:`contributing` for development guidelines and contribution process.
