Quick Start Guide
==================

Get started with the Google Photos to iCloud migration in 5 minutes.

Prerequisites Checklist
-----------------------

* [ ] Python 3.11+ installed
* [ ] ExifTool installed (``brew install exiftool`` on macOS)
* [ ] Google Drive API credentials (``credentials.json``)
* [ ] macOS with iCloud Photos enabled (no credentials needed)

Setup (5 minutes)
-----------------

1. **Install dependencies:**

   .. code-block:: bash

      pip install -r requirements.txt

2. **Run the Authentication Setup Wizard (Recommended):**

   .. code-block:: bash

      python3 auth_setup.py

   This will guide you through Google Drive OAuth setup and create your ``config.yaml`` file automatically.

   **OR** configure manually:

   .. code-block:: bash

      cp config.yaml.example config.yaml
      # Edit config.yaml with your settings

3. **Run the migration:**

   **Option A: Process local zip files (if you already have Google Takeout zips):**

   .. code-block:: bash

      python3 process_local_zips.py --takeout-dir "/path/to/your/zips"

   **Option B: Download from Google Drive and process:**

   .. code-block:: bash

      python3 main.py --config config.yaml

   Both methods use Apple's PhotoKit framework to save photos directly to your Photos library, which then syncs to iCloud Photos automatically.

Configuration Essentials
------------------------

Minimum required settings in ``config.yaml``:

.. code-block:: yaml

   google_drive:
     credentials_file: "credentials.json"
     zip_file_pattern: "takeout-*.zip"

   icloud:
     # No credentials needed - uses your macOS iCloud account automatically via PhotoKit

   processing:
     base_dir: "/tmp/google-photos-migration"

Expected Timeline
-----------------

* **Small library** (<10GB): 1-2 hours
* **Medium library** (10-100GB): 4-8 hours
* **Large library** (100GB+): 1-3 days

For more details, see the full :doc:`configuration` guide.
