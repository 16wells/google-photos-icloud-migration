#!/bin/bash
# Script to create a transferable update script for the VM
# This avoids heredoc truncation issues

echo "Creating transferable update script..."

# Create a Python script that reads base64 from stdin
cat > update-vm-files-transfer.py << 'SCRIPT_HEADER'
#!/usr/bin/env python3
"""
Update script for VM - Run this on your VM to update the files.
This script reads base64 encoded files from stdin or embedded data.
"""

import base64
import sys
from pathlib import Path

# The base64 data will be appended to this file
# Or you can pipe it: python3 update-vm-files-transfer.py < base64_data.txt

SCRIPT_HEADER

# Encode files and append to script
python3 << 'ENCODE_SCRIPT'
import base64
from pathlib import Path

drive_content = Path('drive_downloader.py').read_bytes()
main_content = Path('main.py').read_bytes()

drive_b64 = base64.b64encode(drive_content).decode('ascii')
main_b64 = base64.b64encode(main_content).decode('ascii')

# Append to the script
with open('update-vm-files-transfer.py', 'a') as f:
    f.write(f'''
# Base64 encoded drive_downloader.py
DRIVE_B64 = """{drive_b64}"""

# Base64 encoded main.py  
MAIN_B64 = """{main_b64}"""

def main():
    print("=" * 60)
    print("Updating files on VM...")
    print("=" * 60)
    print()
    
    # Backup existing files
    for fname in ['drive_downloader.py', 'main.py']:
        file_path = Path(fname)
        if file_path.exists():
            backup_path = Path(fname + '.backup')
            backup_path.write_bytes(file_path.read_bytes())
            print(f"✓ Backed up {{fname}}")
        else:
            print(f"⚠ {{fname}} not found (will create new file)")
    
    print()
    
    # Decode and write updated files
    try:
        drive_content = base64.b64decode(DRIVE_B64)
        Path('drive_downloader.py').write_bytes(drive_content)
        print("✓ Updated drive_downloader.py")
        
        main_content = base64.b64decode(MAIN_B64)
        Path('main.py').write_bytes(main_content)
        print("✓ Updated main.py")
    except Exception as e:
        print(f"✗ Error updating files: {{e}}")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ Files updated successfully!")
    print("=" * 60)
    print()
    print("Verify the updates:")
    print("  grep -n '_find_existing_zips' main.py")
    print("  grep -n '_check_disk_space' drive_downloader.py")
    print("  grep -n 'Phase 1: Listing zip files' main.py")
    print()
    print("Then run:")
    print("  python3 main.py --config config.yaml")
    print()

if __name__ == '__main__':
    main()
''')

print("✓ Created update-vm-files-transfer.py")
ENCODE_SCRIPT

chmod +x update-vm-files-transfer.py
echo "✓ Made update-vm-files-transfer.py executable"
echo ""
echo "To transfer to VM:"
echo "  scp update-vm-files-transfer.py user@vm:/path/to/destination/"
echo ""
echo "Or copy the file contents manually if scp is not available."

