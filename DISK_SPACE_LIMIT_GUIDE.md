# Disk Space Limit Feature

## Overview

The migration tool now includes a **Disk Space Limit** feature that allows you to control how much disk space the migration process can use. This is especially useful if:

- You have limited disk space
- You want to ensure other applications have enough room
- You're running the migration on a shared system
- You want to process files in batches without filling the disk

## How It Works

The disk space limit feature monitors the amount of disk space used by the migration process and pauses downloads when the limit is reached. This helps prevent filling up your disk during large migrations.

### What Happens When Limit is Reached

1. **Download Phase**:
   - Downloads pause when disk usage reaches the limit
   - Already-downloaded files continue processing
   - Uploads continue normally

2. **After Cleanup**:
   - When cleanup frees space (after processing ZIPs)
   - Downloads automatically resume
   - Process continues until all files are migrated

3. **User Notification**:
   - Terminal logs show "Waiting for disk space"
   - Logs indicate when pausing/resuming
   - Progress messages show current disk usage

## Configuration

### Via config.yaml

```yaml
processing:
  max_disk_space_gb: 100  # 100 GB limit
  # or
  max_disk_space_gb: null  # Unlimited
  # or
  max_disk_space_gb: 0     # Also unlimited
```

## Recommendations

### For Different Library Sizes

| Library Size | Recommended Limit | Why |
|-------------|-------------------|-----|
| Small (<10 GB) | 50 GB | Plenty of headroom |
| Medium (10-50 GB) | 100 GB | 2x library size |
| Large (50-200 GB) | 200-300 GB | Allows multiple ZIPs |
| Very Large (200+ GB) | Unlimited or 500 GB | Batch processing |

### Best Practices

1. **Leave Headroom**: Set limit to 2-3x your largest ZIP file
2. **Enable Cleanup**: Turn on `cleanup_after_upload` to free space automatically
3. **Monitor**: Watch terminal logs for disk space messages
4. **Adjust**: You can change the limit mid-migration (stop, change config, restart)

## Examples

### Example 1: Limited Laptop Disk

**Scenario**: MacBook with 256 GB SSD, 100 GB free

```yaml
processing:
  max_disk_space_gb: 50  # Use max 50 GB
  cleanup_after_processing: true  # Essential!
```

**Result**:
- Downloads 50 GB at a time
- Processes and uploads
- Cleans up
- Downloads next batch
- Never exceeds 50 GB usage

### Example 2: Large External Drive

**Scenario**: External SSD with 1 TB free, large library

```yaml
processing:
  max_disk_space_gb: 500  # Use max 500 GB
  cleanup_after_processing: false  # Keep for safety
```

**Result**:
- Can download many ZIPs in parallel
- Faster migration (less waiting)
- Files kept until manually deleted

### Example 3: Unlimited Server

**Scenario**: Cloud server with 2 TB disk

```yaml
processing:
  max_disk_space_gb: null  # Unlimited
  cleanup_after_processing: true  # Still recommended
```

**Result**:
- Maximum speed
- No pauses
- Cleanup still happens for tidiness

## Technical Details

### How Space is Calculated

The tool monitors:
1. **Total disk capacity** (e.g., 500 GB)
2. **Currently used space** (e.g., 300 GB)
3. **Migration directory size** (e.g., 50 GB)
4. **Effective usage for migration** = Migration dir size

### Space Check Timing

- **Before each download**: Checks if space available
- **Every 60 seconds**: During active migration
- **After cleanup**: Re-checks to resume downloads

### Safety Margins

- **Buffer**: Tool leaves 10% or 5 GB (whichever is larger) free
- **Example**: 100 GB limit = actually stops at ~95 GB
- **Reason**: Prevents system instability from full disk

## Troubleshooting

### Downloads Keep Pausing

**Problem**: Downloads pause too frequently

**Solutions**:
1. Increase the disk space limit
2. Enable "Cleanup after processing"
3. Manually delete processed ZIPs
4. Check if other apps are using disk space

### Limit Not Working

**Problem**: Migration uses more than the limit

**Possible Causes**:
1. Limit set after download started (finish current download first)
2. Extracted files count toward total
3. Other processes writing to disk

**Solution**: Stop migration, set limit, restart

### Performance Impact

**Problem**: Slower migration due to frequent pauses

**Solutions**:
1. Increase limit to allow more parallel downloads
2. Use faster cleanup (SSD recommended)
3. Set limit to 2-3x your largest ZIP file size

## Monitoring

### Terminal Logs

```
INFO: Checking disk space before download...
INFO: Current usage: 45.2 GB / 100.0 GB limit (45%)
INFO: Space available, starting download: takeout-001.zip
WARNING: Disk space limit approaching (95.8 GB / 100.0 GB)
INFO: Pausing downloads until space is freed
INFO: Cleanup freed 18.5 GB (77.3 GB / 100.0 GB)
INFO: Resuming downloads...
```

## FAQs

### Q: Can I change the limit during migration?
**A**: Yes, but you must stop the migration, change the setting, and restart.

### Q: What if I run out of disk space completely?
**A**: The tool checks before each download, so it should never fill the disk. However, other apps could use space. Always leave 10-20 GB free for system.

### Q: Does the limit apply to uploaded files?
**A**: No, only to files in the migration directory. Uploaded files go to iCloud.

### Q: How do I see current disk usage?
**A**: Use `df -h` in terminal to see disk usage, or check the migration directory size with `du -sh <base_dir>`.

### Q: Should I use unlimited or set a limit?
**A**: 
- **Unlimited**: If you have 200+ GB free and want maximum speed
- **Limited**: If disk space is tight or you want to be safe

## Related Settings

Works best with these settings:

```yaml
processing:
  max_disk_space_gb: 100
  cleanup_after_processing: true  # Free space automatically
  max_parallel_downloads: 3       # Don't overwhelm disk
  verify_after_upload: true       # Safe to delete after verify
```

## Future Enhancements

Potential improvements:
- [ ] Auto-calculate recommended limit based on available space
- [ ] Show progress bar for disk usage
- [ ] Warning when approaching limit
- [ ] Pause/resume button tied to disk space
- [ ] Smart cleanup (delete oldest files first)

---

**Pro Tip**: Start with a conservative limit (e.g., 50 GB) and increase if migration is too slow. It's easier to increase than to recover from a full disk!


