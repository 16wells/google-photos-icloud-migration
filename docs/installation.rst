Installation Guide
===================

This guide covers the installation process for the Google Photos to iCloud Migration tool.

Prerequisites
-------------

* **macOS**: This tool requires macOS for PhotoKit integration
* **Python 3.11+**: Check your Python version with ``python3 --version``
* **ExifTool**: Install with ``brew install exiftool``
* **Google Drive API Credentials**: See :doc:`authentication` for setup instructions

Installation Steps
------------------

1. **Clone or download the repository**

   .. code-block:: bash

      git clone https://github.com/your-org/google-photos-icloud-migration.git
      cd google-photos-icloud-migration

2. **Create a virtual environment (recommended)**

   .. code-block:: bash

      python3 -m venv venv
      source venv/bin/activate

3. **Install dependencies**

   .. code-block:: bash

      pip install -r requirements.txt

   Or for development:

   .. code-block:: bash

      pip install -r requirements-dev.txt

4. **Verify installation**

   .. code-block:: bash

      python3 -c "from google_photos_icloud_migration import __version__; print(__version__)"
      exiftool -ver

Next Steps
----------

* See :doc:`quickstart` for getting started
* See :doc:`configuration` for configuration options
* See :doc:`authentication` for Google Drive API setup
