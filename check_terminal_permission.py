#!/usr/bin/env python3
"""
Check which terminal application is being used and provide permission instructions.
"""

import os
import sys
import platform
import subprocess

def get_terminal_app():
    """Detect which terminal application is being used."""
    # Check environment variables that indicate the terminal
    term_program = os.environ.get('TERM_PROGRAM', '')
    term_program_version = os.environ.get('TERM_PROGRAM_VERSION', '')
    
    # Check parent process
    try:
        # Get parent process name
        if platform.system() == 'Darwin':
            # Use ps to get parent process
            ppid = os.getppid()
            result = subprocess.run(
                ['ps', '-p', str(ppid), '-o', 'comm='],
                capture_output=True,
                text=True
            )
            parent_process = result.stdout.strip()
            
            # Also check via launchctl
            try:
                result2 = subprocess.run(
                    ['ps', '-p', str(ppid), '-o', 'command='],
                    capture_output=True,
                    text=True
                )
                parent_command = result2.stdout.strip()
            except:
                parent_command = ''
        else:
            parent_process = ''
            parent_command = ''
    except:
        parent_process = ''
        parent_command = ''
    
    # Determine terminal app
    if 'Cursor' in term_program or 'Cursor' in parent_process or 'Cursor' in parent_command:
        return 'Cursor'
    elif 'Code' in term_program or 'code' in parent_process or 'Visual Studio Code' in parent_command:
        return 'Visual Studio Code'
    elif 'iTerm' in term_program or 'iTerm' in parent_process:
        return 'iTerm2'
    elif 'Terminal' in term_program or 'Terminal.app' in parent_process or 'Terminal' in parent_command:
        return 'Terminal'
    else:
        # Try to detect from parent process path
        if 'cursor' in parent_command.lower():
            return 'Cursor'
        elif 'code' in parent_command.lower():
            return 'Visual Studio Code'
        elif 'iterm' in parent_command.lower():
            return 'iTerm2'
        else:
            return 'Unknown'

def check_photos_permission():
    """Check Photos permission status."""
    try:
        from Photos import (
            PHPhotoLibrary, PHAuthorizationStatus,
            PHAuthorizationStatusAuthorized, PHAuthorizationStatusLimited,
            PHAuthorizationStatusDenied, PHAuthorizationStatusNotDetermined
        )
        
        status = PHPhotoLibrary.authorizationStatus()
        
        if status == PHAuthorizationStatusAuthorized:
            return 'granted'
        elif status == PHAuthorizationStatusLimited:
            return 'limited'
        elif status == PHAuthorizationStatusDenied:
            return 'denied'
        elif status == PHAuthorizationStatusNotDetermined:
            return 'not_determined'
        else:
            return 'unknown'
    except ImportError:
        return 'error'
    except Exception as e:
        print(f"Error checking permission: {e}")
        return 'error'

def main():
    print("=" * 60)
    print("Terminal and Photos Permission Checker")
    print("=" * 60)
    print()
    
    # Detect terminal
    terminal_app = get_terminal_app()
    print(f"Detected terminal application: {terminal_app}")
    print()
    
    # Check permission
    if platform.system() != 'Darwin':
        print("❌ This script requires macOS")
        sys.exit(1)
    
    permission_status = check_photos_permission()
    
    print("Photos Permission Status:")
    if permission_status == 'granted':
        print("  ✓ Permission granted!")
        print()
        print("You're all set! You can run the migration script.")
        sys.exit(0)
    elif permission_status == 'limited':
        print("  ✓ Limited permission granted (sufficient)")
        print()
        print("You're all set! You can run the migration script.")
        sys.exit(0)
    elif permission_status == 'denied':
        print("  ❌ Permission denied")
    elif permission_status == 'not_determined':
        print("  ⚠️  Permission not yet requested")
    elif permission_status == 'error':
        print("  ❌ Error checking permission")
        print("  Please install: pip install pyobjc-framework-Photos")
        sys.exit(1)
    else:
        print(f"  ⚠️  Unknown status: {permission_status}")
    
    print()
    print("=" * 60)
    print("HOW TO FIX:")
    print("=" * 60)
    print()
    print(f"Since you're using {terminal_app}, you need to grant Photos permission")
    print(f"to {terminal_app} specifically (not just Terminal.app).")
    print()
    print("Steps:")
    print("1. Open System Settings > Privacy & Security > Photos")
    print(f"2. Look for '{terminal_app}' in the list of apps")
    print("3. If not listed:")
    print("   - Click the '+' button to add it (if available)")
    print("   - Or run: sudo tccutil reset Photos")
    print("   - Then run: python3 request_photos_permission.py")
    print("4. Enable 'Add Photos Only' or 'Read and Write' permission")
    print()
    print("Alternative: If {terminal_app} doesn't appear, try:")
    print("  - Grant permission to 'Python' instead")
    print("  - Or use Terminal.app to run the migration script")
    print()
    
    # Try to open System Settings
    try:
        subprocess.run(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Photos'])
        print("Opening System Settings to Photos privacy...")
    except:
        pass
    
    sys.exit(1)

if __name__ == "__main__":
    main()

