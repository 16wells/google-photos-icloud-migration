# Repository Cleanup Report

## Summary

This report identifies outdated files, incorrect documentation, and cleanup opportunities in the repository.

## Files That Should Be Removed

### 1. Log Files (Already in .gitignore, but should be removed if tracked)
- `migration.log` - Current log file (should stay in .gitignore)
- `migration.log.1` - Rotated log file (should stay in .gitignore)
- `migration.log.2` - Rotated log file (should stay in .gitignore)
- `migration_error.log` - Error log file (should stay in .gitignore)

**Status:** These are already in `.gitignore` and should not be committed. If they're currently tracked, they should be removed with `git rm --cached`.

### 2. Web UI Directory (Potentially Outdated)
- `web/services/log_monitor.py` - Log monitoring service (old web UI code)
- `web/services/process_monitor.py` - Process monitoring service (old web UI code)

**Analysis:** The README states the tool is "terminal only" and mentions the web UI was unreliable. These files appear to be leftover from the old web UI implementation.

**Recommendation:** 
- **Option A:** Remove the `web/` directory entirely if web UI is completely deprecated
- **Option B:** Add a note in the directory explaining it's deprecated/archived code
- **Option C:** Keep if there are plans to revive the web UI

**Current Status:** No active references found in the codebase (only `webbrowser` imports for OAuth, which is different).

## Documentation Issues Fixed

### ✅ Fixed: Missing Documentation for `process_local_zips.py`

**Files Updated:**
- `README.md` - Added section on processing local zip files
- `QUICKSTART.md` - Added Option A for local zip processing
- `COMPLETE_INSTALLATION_GUIDE.md` - Added Option A for local zip processing

**Issue:** The main script the user is using (`process_local_zips.py`) was not documented in the main documentation files.

### ✅ Fixed: Outdated Web UI References

**Files Updated:**
- `.github/REPO_DESCRIPTION.md` - Removed "web UI" references
- `scripts/set_github_repo_info.py` - Removed web UI topics and description

**Issue:** Repository description and topics mentioned "web UI" but the tool is terminal-only.

## Scripts Analysis

### Active Scripts (Keep)
- `process_local_zips.py` - **PRIMARY** - Processes local zip files (with state tracking)
- `process_local_folders.py` - Processes already-extracted folders (alternative workflow)
- `main.py` - Downloads from Google Drive and processes
- `auth_setup.py` - Authentication setup wizard
- `check-auth-status.py` - Check authentication status
- `verify-setup.py` - Verify installation
- `fix_albums.py` - Fix album organization
- `request_photos_permission.py` - Request Photos permission
- `check_terminal_permission.py` - Check terminal permission

### Shell Scripts (Review)
- `setup-macbook.sh` - MacBook setup (likely still useful)
- `setup-git-repo.sh` - Git repo setup (likely still useful)
- `push-to-github.sh` - Push to GitHub (likely still useful)
- `init-git.sh` - Initialize git (likely still useful)
- `grant_photos_permission.sh` - Grant Photos permission (alternative method)
- `fix_photos_permission.sh` - Fix Photos permission (helper)
- `clear-icloud-cookies.sh` - PhotoKit permission helper (updated - no cookies needed for PhotoKit)
- `create-config-on-vm.sh` - VM setup (if using VMs)
- `finish-vm-setup.sh` - VM setup (if using VMs)
- `upload-to-vm.sh` - VM setup (if using VMs)
- `verify-vm-setup.sh` - VM setup (if using VMs)
- `recover-config.sh` - Recover config (utility)
- `test_branch.sh` - Testing (development)
- `test_all_branches.sh` - Testing (development)

**Recommendation:** Most shell scripts appear to be utility scripts. Keep them unless you're not using VMs or specific features.

## Differences Between Scripts

### `process_local_zips.py` vs `process_local_folders.py`

**`process_local_zips.py`** (Recommended):
- Processes **zip files** directly
- Extracts zips automatically
- Has state tracking (`--skip-processed`, `--retry-failed`)
- More feature-complete

**`process_local_folders.py`**:
- Processes **already-extracted folders**
- Skips extraction step
- No state tracking
- Simpler workflow for pre-extracted data

**Recommendation:** Keep both - they serve different use cases. Consider adding documentation explaining when to use each.

## Recommendations

### High Priority
1. ✅ **DONE:** Update documentation to include `process_local_zips.py`
2. ✅ **DONE:** Remove web UI references from repository description
3. **TODO:** Decide on `web/` directory - remove or archive with note

### Medium Priority
4. **TODO:** Add note to `process_local_folders.py` explaining when to use it vs `process_local_zips.py`
5. **TODO:** Review VM-related scripts - remove if not using VMs
6. **TODO:** Consider consolidating permission helper scripts

### Low Priority
7. **TODO:** Review test scripts (`test_branch.sh`, `test_all_branches.sh`) - keep if actively testing
8. **TODO:** Add `.env.example` file if it doesn't exist (for reference)

## Files to Keep

All core functionality files should be kept:
- All files in `google_photos_icloud_migration/` package
- `main.py` (Google Drive download workflow)
- `process_local_zips.py` (Local zip processing - PRIMARY)
- `process_local_folders.py` (Pre-extracted folder processing)
- All documentation files (now updated)
- Configuration files (`config.yaml.example`, `config_schema.json`)
- Requirements files
- Test files

## Next Steps

1. Review this report
2. Decide on `web/` directory (remove or archive)
3. Remove log files if they're tracked in git
4. Consider adding usage notes to `process_local_folders.py`


