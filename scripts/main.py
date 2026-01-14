#!/usr/bin/env python3
"""
Main script for migrating Google Photos to iCloud Photos.
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to python path to allow imports from package
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from google_photos_icloud_migration.orchestrator import MigrationOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate Google Photos to iCloud Photos'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--retry-failed',
        action='store_true',
        help='Retry previously failed uploads (skips download/extract/process steps)'
    )
    parser.add_argument(
        '--redownload-zips',
        action='store_true',
        help='When used with --retry-failed, also re-download and re-process zip files containing failed uploads'
    )
    parser.add_argument(
        '--max-disk-space',
        type=float,
        default=None,
        metavar='GB',
        help='Maximum disk space to use in GB (overrides config file). Set to 0 for unlimited. Example: --max-disk-space 100'
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    try:
        orchestrator = MigrationOrchestrator(args.config)
        
        # Override max_disk_space_gb from command line if provided
        if args.max_disk_space is not None:
            if args.max_disk_space == 0:
                orchestrator.config.processing.max_disk_space_gb = None
                logger.info("Disk space limit: Unlimited (set via --max-disk-space 0)")
            else:
                orchestrator.config.processing.max_disk_space_gb = args.max_disk_space
                logger.info(f"Disk space limit: {args.max_disk_space} GB (set via --max-disk-space)")
        
        # Store redownload_zips flag in orchestrator for retry mode
        if args.retry_failed and args.redownload_zips:
            orchestrator._redownload_zips = True
        
        # Run migration
        orchestrator.run(retry_failed=args.retry_failed)
        
    except Exception as e:
        logger.error(f"Migration failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
