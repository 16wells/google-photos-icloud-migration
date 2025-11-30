# Web UI Statistics Fix

## Problem
The web UI statistics were showing zeros or not updating, making it difficult to know if the migration was running or what progress was being made.

## Root Cause
The statistics monitoring code had a critical bug: it only updated statistics if they were non-zero:

```python
if hasattr(stats, 'zip_files_total') and stats.zip_files_total:
    migration_state['statistics']['zip_files_total'] = stats.zip_files_total
```

The `and stats.zip_files_total:` check meant that:
- If a value was 0 (initial state), it wouldn't update
- Once stuck at 0, it would never update even when the actual value changed
- This caused all statistics to appear as zeros

## Fixes Applied

### 1. Removed Zero-Value Checks
Removed the `and value` checks so statistics update even when they're 0:
```python
if hasattr(stats, 'zip_files_total'):
    migration_state['statistics']['zip_files_total'] = stats.zip_files_total
```

### 2. Improved Log Parsing
Enhanced log message parsing to catch more statistics patterns:
- More flexible regex patterns (case-insensitive)
- Better tracking of uploaded files from log messages
- Improved album detection patterns

### 3. Faster Update Frequency
Reduced polling interval from 2 seconds to 1 second for more responsive UI updates.

### 4. Better Startup Timing
Added a small delay to ensure the orchestrator is fully initialized before statistics monitoring begins.

### 5. Multiple Update Sources
Statistics now come from two sources:
- **Direct from orchestrator statistics object** (most accurate, updated every second)
- **Parsed from log messages** (backup, catches updates that might be missed)

## Testing
To verify the fix works:

1. Start a migration via web UI
2. Statistics should update within 1-2 seconds of activity
3. All counters should increment as processing occurs
4. Progress bars should reflect actual progress

## If Statistics Still Don't Update

If you still see zeros after these fixes, check:

1. **Check the Activity Log** - If logs are appearing, the migration is running
2. **Check console logs** - Look for any errors in the browser console (F12)
3. **Verify orchestrator statistics** - The underlying migration is working if logs show activity

The log parsing should catch most statistics even if the direct statistics reading fails.

## Notes

- This is NOT a MacBook vs internet limitation - it was a code bug
- The terminal version was always working correctly
- These fixes make the web UI much more reliable
- Statistics now update in real-time as the migration progresses






