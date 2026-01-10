API Reference
==============

This document provides detailed API documentation for the Google Photos to iCloud Migration tool.

Core Modules
------------

.. toctree::
   :maxdepth: 2

   api/config
   api/exceptions
   api/downloader
   api/processor
   api/uploader
   api/utils

Main Classes
------------

MigrationOrchestrator
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: main.MigrationOrchestrator
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
~~~~~~~~~~~~~

.. automodule:: google_photos_icloud_migration.config
   :members:
   :undoc-members:
   :show-inheritance:

Exceptions
~~~~~~~~~~

.. automodule:: google_photos_icloud_migration.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

Downloader
~~~~~~~~~~

.. automodule:: google_photos_icloud_migration.downloader.drive_downloader
   :members:
   :undoc-members:
   :show-inheritance:

Processor
~~~~~~~~~

.. automodule:: google_photos_icloud_migration.processor.extractor
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: google_photos_icloud_migration.processor.metadata_merger
   :members:
   :undoc-members:
   :show-inheritance:

Uploader
~~~~~~~~

.. automodule:: google_photos_icloud_migration.uploader.icloud_uploader
   :members:
   :undoc-members:
   :show-inheritance:

Utils
~~~~~

.. automodule:: google_photos_icloud_migration.utils.health_check
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: google_photos_icloud_migration.utils.security
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: google_photos_icloud_migration.utils.state_manager
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: google_photos_icloud_migration.utils.logging_config
   :members:
   :undoc-members:
   :show-inheritance:
