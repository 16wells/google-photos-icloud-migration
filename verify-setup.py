#!/usr/bin/env python3
"""
Verification script to check if the MacBook is properly set up for migration.
Run this after completing the setup steps.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python():
    """Check Python version."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ⚠️  Warning: Python 3.8+ recommended")
        return False
    return True

def check_package(package_name, import_name=None):
    """Check if a Python package is installed."""
    if import_name is None:
        import_name = package_name
    try:
        __import__(import_name)
        print(f"  ✓ {package_name} installed")
        return True
    except ImportError:
        print(f"  ✗ {package_name} missing (pip3 install {package_name})")
        return False

def check_command(command, name=None):
    """Check if a system command is available."""
    if name is None:
        name = command
    result = subprocess.run(['which', command], capture_output=True)
    if result.returncode == 0:
        print(f"  ✓ {name} installed")
        return True
    else:
        print(f"  ✗ {name} not found in PATH")
        return False

def check_file(filepath, description=None):
    """Check if a file exists."""
    if description is None:
        description = filepath
    if os.path.exists(filepath):
        print(f"  ✓ {description} found")
        return True
    else:
        print(f"  ✗ {description} missing")
        return False

def main():
    print("=" * 60)
    print("MacBook Setup Verification")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Check Python
    print("Python:")
    if not check_python():
        all_ok = False
    print()
    
    # Check Python packages
    print("Python Packages:")
    packages = [
        ('google-api-python-client', 'google.auth'),
        ('pyicloud', 'pyicloud'),
        ('Pillow', 'PIL'),
        ('PyYAML', 'yaml'),
        ('tqdm', 'tqdm'),
        ('python-dateutil', 'dateutil'),
    ]
    for package, import_name in packages:
        if not check_package(package, import_name):
            all_ok = False
    print()
    
    # Check system tools
    print("System Tools:")
    
    # Check Xcode Command Line Tools
    result = subprocess.run(['xcode-select', '-p'], capture_output=True)
    if result.returncode == 0:
        print("  ✓ Xcode Command Line Tools installed")
    else:
        print("  ✗ Xcode Command Line Tools not found")
        print("    → Install with: xcode-select --install")
        all_ok = False
    
    # Check git (comes with Command Line Tools)
    if not check_command('git', 'Git'):
        print("    → Git should be installed with Xcode Command Line Tools")
        all_ok = False
    
    if not check_command('exiftool', 'ExifTool'):
        all_ok = False
    print()
    
    # Check configuration files
    print("Configuration Files:")
    if not check_file('credentials.json', 'credentials.json'):
        all_ok = False
        print("    → Copy this file from your current machine")
    if not check_file('config.yaml', 'config.yaml'):
        all_ok = False
        print("    → Copy this file from your current machine")
    print()
    
    # Check if we're on macOS
    print("System:")
    if sys.platform == 'darwin':
        print("  ✓ Running on macOS")
        
        # Check if Photos app is available
        photos_path = Path('/Applications/Photos.app')
        if photos_path.exists():
            print("  ✓ Photos app found")
        else:
            print("  ⚠️  Photos app not found (unusual on macOS)")
    else:
        print("  ⚠️  Not running on macOS (--use-sync requires macOS)")
        all_ok = False
    print()
    
    # Summary
    print("=" * 60)
    if all_ok:
        print("✓ All checks passed! You're ready to run the migration.")
        print()
        print("Next steps:")
        print("1. Sign into iCloud with your Apple ID")
        print("2. Enable iCloud Photos in System Settings")
        print("3. Run: python3 main.py --config config.yaml --use-sync")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("- Missing packages: pip3 install -r requirements.txt")
        print("- Missing ExifTool: brew install exiftool")
        print("- Missing config files: Copy credentials.json and config.yaml")
    print("=" * 60)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())

