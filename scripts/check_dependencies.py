#!/usr/bin/env python3
"""
Check dependencies for known security vulnerabilities using pip-audit.

This script checks the installed packages (or requirements.txt) for known
CVEs and security issues.

Requirements:
    pip install pip-audit

Usage:
    python scripts/check_dependencies.py
    python scripts/check_dependencies.py --requirements requirements.txt
"""
import sys
import subprocess
import argparse
from pathlib import Path


def check_pip_audit_installed():
    """Check if pip-audit is installed."""
    try:
        subprocess.run(['pip-audit', '--version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pip_audit():
    """Install pip-audit if not available."""
    print("Installing pip-audit...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pip-audit'],
                      check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install pip-audit. Please install manually:")
        print("   pip install pip-audit")
        return False


def run_pip_audit(requirements_file=None, fix=False):
    """Run pip-audit to check for vulnerabilities."""
    args = ['pip-audit']
    
    if requirements_file:
        args.extend(['-r', str(requirements_file)])
    
    if fix:
        args.append('--fix')
    
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("❌ pip-audit not found. Installing...")
        if install_pip_audit():
            return run_pip_audit(requirements_file, fix)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Check Python dependencies for security vulnerabilities'
    )
    parser.add_argument(
        '--requirements',
        '-r',
        type=Path,
        default=Path(__file__).parent.parent / 'requirements.txt',
        help='Path to requirements.txt file (default: requirements.txt)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Automatically fix vulnerabilities where possible (updates packages)'
    )
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install pip-audit if not available'
    )
    
    args = parser.parse_args()
    
    # Check if pip-audit is installed
    if not check_pip_audit_installed():
        if args.install:
            if not install_pip_audit():
                sys.exit(1)
        else:
            print("❌ pip-audit is not installed.")
            print("\nTo install:")
            print("   pip install pip-audit")
            print("\nOr run with --install flag:")
            print(f"   python {__file__} --install")
            sys.exit(1)
    
    # Check if requirements file exists
    if args.requirements and not args.requirements.exists():
        print(f"⚠️  Requirements file not found: {args.requirements}")
        print("Running pip-audit on installed packages...")
        requirements_file = None
    else:
        requirements_file = args.requirements
        print(f"Checking dependencies from: {requirements_file}")
    
    print()
    
    # Run pip-audit
    success = run_pip_audit(requirements_file, fix=args.fix)
    
    if success:
        print("\n✅ Dependency check complete")
        sys.exit(0)
    else:
        print("\n⚠️  Vulnerabilities found or check failed")
        print("\nTo fix vulnerabilities automatically (updates packages):")
        print(f"   python {__file__} --fix")
        print("\nNote: Always test after updating packages!")
        sys.exit(1)


if __name__ == '__main__':
    main()

