#!/usr/bin/env python3
"""
Generate a lock file with exact versions of all dependencies.

This script uses pip-tools to generate a requirements-lock.txt file
with exact pinned versions for reproducible builds.

Requirements:
    pip install pip-tools

Usage:
    python scripts/generate_lockfile.py
    python scripts/generate_lockfile.py --requirements requirements.txt
"""
import sys
import subprocess
import argparse
from pathlib import Path


def check_pip_tools_installed():
    """Check if pip-tools is installed."""
    try:
        subprocess.run(['pip-compile', '--version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pip_tools():
    """Install pip-tools if not available."""
    print("Installing pip-tools...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pip-tools'],
                      check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install pip-tools. Please install manually:")
        print("   pip install pip-tools")
        return False


def generate_lockfile(requirements_file, output_file=None):
    """Generate lock file from requirements.txt."""
    if output_file is None:
        output_file = requirements_file.parent / 'requirements-lock.txt'
    
    args = [
        'pip-compile',
        '--output-file', str(output_file),
        '--resolver', 'backtracking',  # Better dependency resolution
        str(requirements_file)
    ]
    
    try:
        print(f"Generating lock file: {output_file}")
        print(f"From requirements: {requirements_file}")
        print()
        
        result = subprocess.run(args, check=True, text=True)
        print(f"✅ Lock file generated: {output_file}")
        print("\nTo install from lock file:")
        print(f"   pip install -r {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate lock file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate a lock file with exact dependency versions'
    )
    parser.add_argument(
        '--requirements',
        '-r',
        type=Path,
        default=Path(__file__).parent.parent / 'requirements.txt',
        help='Path to requirements.txt file (default: requirements.txt)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=Path,
        help='Output lock file path (default: requirements-lock.txt)'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install pip-tools if not available'
    )
    
    args = parser.parse_args()
    
    # Check if requirements file exists
    if not args.requirements.exists():
        print(f"❌ Requirements file not found: {args.requirements}")
        sys.exit(1)
    
    # Check if pip-tools is installed
    if not check_pip_tools_installed():
        if args.install:
            if not install_pip_tools():
                sys.exit(1)
        else:
            print("❌ pip-tools is not installed.")
            print("\nTo install:")
            print("   pip install pip-tools")
            print("\nOr run with --install flag:")
            print(f"   python {__file__} --install")
            sys.exit(1)
    
    # Generate lock file
    success = generate_lockfile(args.requirements, args.output)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

