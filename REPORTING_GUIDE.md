# Migration Reporting Guide

## Overview

The migration tool now generates comprehensive reports at the end of each migration run. These reports provide detailed statistics, error summaries, and actionable recommendations.

## Report Files Generated

When the migration completes, the following files are created in your base directory (default: `/tmp/google-photos-migration`):

1. **`migration_report.txt`** - Human-readable text report with complete migration summary
2. **`migration_statistics.json`** - Machine-readable JSON file with all statistics
3. **`migration.log`** - Detailed log file with all operations and errors (if logging to file is enabled)
4. **`failed_uploads.json`** - List of files that failed to upload (if any)
5. **`corrupted_zips.json`** - List of corrupted zip files (if any)

## Report Contents

### Executive Summary
- Start and end times
- Total duration
- Overall success rate
- High-level statistics

### Phase-by-Phase Breakdown

The report breaks down statistics for each phase:

1. **Phase 1: Download from Google Drive**
   - Total zip files
   - Successfully downloaded
   - Skipped (already existed)
   - Failed downloads
   - Corrupted files
   - Total downloaded size

2. **Phase 2: Extraction**
   - Successfully extracted
   - Extraction failures

3. **Phase 3: Metadata Processing**
   - Media files found
   - Files with JSON metadata
   - Successfully processed
   - Processing failures

4. **Phase 4: Album Parsing**
   - Albums identified
   - Albums from directory structure
   - Albums from JSON metadata

5. **Phase 5: Upload to iCloud Photos**
   - Successfully uploaded
   - Upload failures
   - Verification failures
   - Upload success rate
   - Total uploaded size

### Error Summary

If errors occurred, the report includes:
- Count of errors by category
- References to detailed error logs
- Specific error messages for key failures

### File References

The report provides paths to:
- Detailed log file (contains all operations and errors)
- Failed uploads file (JSON format with file paths and album info)
- Corrupted zip files file (JSON format with file IDs and error info)

### Recommendations & Next Steps

Based on the migration results, the report provides actionable recommendations:
- How to retry failed uploads
- How to handle corrupted zip files
- What to review if verification failures occurred
- Next steps for troubleshooting

## Report Format Recommendations

### Text Report (Default)
- **Format**: Plain text with clear sections and formatting
- **Best for**: Quick reading, sharing via email, printing
- **Location**: `migration_report.txt`

### JSON Statistics
- **Format**: Structured JSON data
- **Best for**: Programmatic analysis, integration with other tools
- **Location**: `migration_statistics.json`

### HTML Report (Future Enhancement)
- The report generator supports HTML format (currently basic)
- Can be enhanced with charts, tables, and interactive elements
- Generate with: `report_generator.save_report(format='html')`

## Accessing Detailed Logs

### Log File
The detailed log file (`migration.log` by default) contains:
- All operations with timestamps
- Error messages with full stack traces
- Debug information
- Progress updates

### Failed Uploads File
The `failed_uploads.json` file contains:
```json
{
  "/path/to/file.jpg": {
    "file": "/path/to/file.jpg",
    "album": "Album Name",
    "retry_count": 1
  }
}
```

### Corrupted Zip Files File
The `corrupted_zips.json` file contains:
```json
{
  "file_id": {
    "file_id": "google_drive_file_id",
    "file_name": "takeout-001.zip",
    "file_size": "1234567890",
    "local_path": "/path/to/local/file.zip",
    "error": "Error message",
    "detected_at": "timestamp",
    "local_size_mb": 1234.56
  }
}
```

## Using the Reports

### After Successful Migration
- Review the executive summary to confirm all files were processed
- Check upload success rate
- Verify album counts match expectations

### After Migration with Errors
1. **Review Error Summary** - See which phases had issues
2. **Check Failed Uploads** - Review `failed_uploads.json` for specific files
3. **Review Log File** - Search for specific error messages
4. **Follow Recommendations** - Use the recommendations section for next steps

### Retrying Failed Uploads
If uploads failed, use the report's recommendation:
```bash
python main.py --config config.yaml --retry-failed
```

### Handling Corrupted Zip Files
1. Check `corrupted_zips.json` for file IDs
2. Manually re-download from Google Drive
3. Or delete local corrupted files and re-run the migration

## Report Customization

### Changing Report Location
The report is saved to the base directory specified in your config:
```yaml
processing:
  base_dir: /path/to/your/directory
```

### Changing Log File Location
Configure in your `config.yaml`:
```yaml
logging:
  file: /path/to/migration.log
  level: INFO
```

## Statistics Tracking

The migration automatically tracks:
- File counts at each phase
- Success/failure rates
- Error messages and timestamps
- File sizes and durations
- Album information

All statistics are collected throughout the migration and compiled into the final report.

## Best Practices

1. **Review the report immediately** after migration completes
2. **Save the report** for your records
3. **Check error summaries** even if migration appears successful
4. **Follow recommendations** for any issues found
5. **Keep log files** for troubleshooting if needed

## Example Report Structure

```
================================================================================
GOOGLE PHOTOS TO iCLOUD PHOTOS MIGRATION REPORT
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Start Time:     2024-01-15 10:00:00
End Time:       2024-01-15 12:30:00
Duration:       2h 30m 0s

Overall Results:
  Zip Files Processed:     45/50 successful
  Zip Files Failed:        5/50
  Success Rate:            90.0%

Media Files:
  Total Found:              12,345
  With Metadata:            11,890
  Processed:                 12,345
  Processing Failed:        0

Upload Results:
  Successfully Uploaded:    12,300
  Upload Failed:            45
  Upload Success Rate:      99.6%
  Total Uploaded Size:       45.2 GB

[... detailed phase breakdown ...]

RECOMMENDATIONS & NEXT STEPS
--------------------------------------------------------------------------------
• Retry failed uploads by running:
  python main.py --config config.yaml --retry-failed
```

## Questions or Issues?

If you have suggestions for improving the reports, please:
1. Check the existing report format
2. Review what information is most useful
3. Consider what additional statistics would be helpful
4. Provide feedback on the report structure

