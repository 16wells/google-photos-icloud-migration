API Reference
==============

This document provides comprehensive API documentation for the Google Photos to iCloud Migration tool.

The API is organized into logical modules for easy navigation:

Core Modules
------------

.. toctree::
   :maxdepth: 2

   api/config
   api/exceptions
   api/downloader
   api/processor
   api/parser
   api/uploader
   api/utils

Main Orchestrator
-----------------

MigrationOrchestrator
~~~~~~~~~~~~~~~~~~~~~

The main orchestrator class that coordinates the entire migration process.

.. automodule:: main
   :members: MigrationOrchestrator
   :undoc-members:
   :show-inheritance:
   :member-order: bysource

Module Overview
---------------

**Configuration (api/config)**
    Configuration loading and validation with environment variable support

**Exceptions (api/exceptions)**
    Custom exception classes for different error scenarios

**Downloader (api/downloader)**
    Google Drive API integration for downloading zip files

**Processor (api/processor)**
    File extraction, metadata merging, and video conversion

**Parser (api/parser)**
    Album structure parsing from directory and JSON metadata

**Uploader (api/uploader)**
    iCloud Photos upload using PhotoKit framework

**Utilities (api/utils)**
    Parallel processing, state management, security, retry logic, metrics, and logging
