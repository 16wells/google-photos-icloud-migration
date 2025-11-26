#!/usr/bin/env python3
"""
Verify that files on VM match expected versions.
Run this script on the VM to check if files are up to date.
"""
import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} - NOT FOUND")
        return False

def check_pattern_in_file(filepath, pattern, description, required=True):
    """Check if a pattern exists in a file."""
    if not os.path.exists(filepath):
        if required:
            print(f"✗ {description}: File not found - {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if pattern in content:
                print(f"✓ {description}: Found in {filepath}")
                return True
            else:
                if required:
                    print(f"✗ {description}: Pattern not found in {filepath}")
                return False
    except Exception as e:
        print(f"✗ Error reading {filepath}: {e}")
        return False

def verify_icloud_uploader():
    """Verify icloud_uploader.py has the latest 2FA fixes."""
    filepath = "icloud_uploader.py"
    checks = []
    
    print("\n" + "="*70)
    print("Verifying icloud_uploader.py")
    print("="*70)
    
    # Check file exists
    if not check_file_exists(filepath, "File exists"):
        return False
    
    # Key patterns that should be present in the updated version
    patterns = [
        # Variable initialization at method level
        ("manual_service_creation = False", 
         "manual_service_creation initialized at method level"),
        
        # Improved 2FA detection in PyiCloudFailedLoginException handler
        ("is_2fa = False", 
         "2FA detection variable initialization"),
        
        ("if not is_2fa and (\"PyiCloud2FARequiredException\" in tb_str", 
         "2FA detection from traceback"),
        
        # Manual service creation in exception handler
        ("self.api = PyiCloudService.__new__(PyiCloudService)", 
         "Manual service creation for 2FA"),
        
        # 2FA handling after exception handlers
        ("# If 2FA was detected in exception handler, handle it now", 
         "2FA handling after exception handlers"),
        
        ("if needs_2fa and hasattr(self, 'api') and self.api is not None:", 
         "2FA check after exception handlers"),
        
        # Trigger authentication to populate trusted devices
        ("if manual_service_creation:", 
         "Check for manual service creation flag"),
        
        ("self.api._authenticate()", 
         "Trigger authentication to populate devices"),
        
        # Device selection and code entry
        ("Available trusted devices:", 
         "Device selection prompt"),
        
        ("Enter 2FA code (attempt", 
         "2FA code entry prompt"),
    ]
    
    all_passed = True
    for pattern, description in patterns:
        result = check_pattern_in_file(filepath, pattern, description)
        checks.append((description, result))
        if not result:
            all_passed = False
    
    return all_passed

def verify_main_py():
    """Verify main.py has expected structure."""
    filepath = "main.py"
    
    print("\n" + "="*70)
    print("Verifying main.py")
    print("="*70)
    
    if not check_file_exists(filepath, "File exists"):
        return False
    
    # Check for key methods/patterns
    patterns = [
        ("def setup_icloud_uploader", "setup_icloud_uploader method"),
        ("def run", "run method"),
        ("iCloudUploader", "iCloudUploader import/usage"),
    ]
    
    all_passed = True
    for pattern, description in patterns:
        result = check_pattern_in_file(filepath, pattern, description)
        if not result:
            all_passed = False
    
    return all_passed

def get_file_checksum(filepath):
    """Get a simple checksum of file (first 1000 chars + size)."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            # Return size and first 1000 bytes hash
            import hashlib
            size = len(content)
            preview = content[:1000]
            hash_obj = hashlib.md5(preview)
            return f"{size}:{hash_obj.hexdigest()}"
    except Exception as e:
        return f"ERROR: {e}"

def main():
    """Main verification function."""
    print("="*70)
    print("VM File Verification Script")
    print("="*70)
    print("\nThis script verifies that files on the VM match expected versions.")
    print("Run this script on your VM to check file integrity.\n")
    
    # Change to home directory if files are there
    home = Path.home()
    if os.path.exists(home / "icloud_uploader.py"):
        os.chdir(home)
        print(f"Changed to directory: {home}")
    elif os.path.exists("icloud_uploader.py"):
        print(f"Using current directory: {os.getcwd()}")
    else:
        print(f"Warning: icloud_uploader.py not found in {home} or current directory")
        print(f"Current directory: {os.getcwd()}")
        print(f"Please run this script from the directory containing the files.")
    
    results = []
    
    # Verify icloud_uploader.py
    icloud_ok = verify_icloud_uploader()
    results.append(("icloud_uploader.py", icloud_ok))
    
    # Verify main.py
    main_ok = verify_main_py()
    results.append(("main.py", main_ok))
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    all_ok = True
    for filename, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {filename}")
        if not passed:
            all_ok = False
    
    print("\n" + "="*70)
    if all_ok:
        print("✓ All files verified successfully!")
        print("Your VM files match the expected versions.")
        return 0
    else:
        print("✗ Some files failed verification.")
        print("Please update the files on your VM using one of these methods:")
        print("  1. Run: ./sync-to-vm.sh photos-migration-vm")
        print("  2. Use: gcloud compute scp icloud_uploader.py main.py photos-migration-vm:~/")
        print("  3. Manually copy the files from your local machine")
        return 1

if __name__ == "__main__":
    sys.exit(main())

