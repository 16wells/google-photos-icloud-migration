# Copy icloud_uploader.py to VM - Instructions

The VM file is missing the fixes. Here's how to update it:

## Method 1: Copy entire file via Browser SSH (Recommended)

1. **Open Browser SSH** in GCP Console for `photos-migration-vm`

2. **Run this command** to create the file:
   ```bash
   cat > icloud_uploader.py << 'ENDOFFILE'
   ```

3. **Copy the entire file** from your local machine:
   - Open: `/Users/skipshean/Sites/google-photos-icloud-migration/icloud_uploader.py`
   - Select all (Cmd+A) and copy (Cmd+C)
   - Paste into the Browser SSH terminal

4. **Finish the command**:
   - Type `ENDOFFILE` on a new line
   - Press Enter

5. **Verify**:
   ```bash
   wc -l icloud_uploader.py  # Should show 454
   grep -c "No trusted devices found" icloud_uploader.py  # Should show 2
   ```

## Method 2: Use Python to write the file

If you have the file content available, you can use Python:

```python
# In Browser SSH, run Python and paste this:
content = """[paste entire file content here]"""

with open('icloud_uploader.py', 'w') as f:
    f.write(content)
```

## Quick Verification Commands

After copying, run these to verify:

```bash
# Check line count (should be 454)
wc -l icloud_uploader.py

# Check for fixes (should all show "Found")
grep -q "No trusted devices found" icloud_uploader.py && echo "✓ Found" || echo "✗ Missing"
grep -q "Ensure devices is a list" icloud_uploader.py && echo "✓ Found" || echo "✗ Missing"
grep -q "while True:" icloud_uploader.py && echo "✓ Found" || echo "✗ Missing"
grep -q "isinstance(devices, list)" icloud_uploader.py && echo "✓ Found" || echo "✗ Missing"
```

