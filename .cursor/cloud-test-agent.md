# Cloud Agent Testing Guide

This guide explains how to test each branch using Cursor Cloud Agents to verify functionality before merging.

## Quick Start

### Option 1: Automated Testing Script

Run the test script for a specific branch:

```bash
# Make script executable
chmod +x test_branch.sh

# Test a specific branch
./test_branch.sh phase-1-dev-tooling
./test_branch.sh phase-2-testing
./test_branch.sh main
```

### Option 2: Manual Testing Checklist

Use the checklist below to manually verify each branch.

## Testing Checklist for Each Branch

### Phase 1: Developer Tooling & Infrastructure
- [ ] Run `make help` - should show all commands
- [ ] Run `make format-check` - should check formatting
- [ ] Run `make lint` - should run linters (may need `make install-dev` first)
- [ ] Verify `.pre-commit-config.yaml` exists
- [ ] Verify `CHANGELOG.md` exists
- [ ] Verify `py.typed` file exists

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-1-dev-tooling && ./test_branch.sh phase-1-dev-tooling
```

### Phase 2: Testing Infrastructure
- [ ] Verify `tests/` directory exists with test files
- [ ] Run `pytest tests/ -v` - tests should execute (may pass or fail, but should run)
- [ ] Check that test fixtures exist in `tests/fixtures/`
- [ ] Verify `conftest.py` exists

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-2-testing && pip install -r requirements-dev.txt && pytest tests/ -v
```

### Phase 3: Code Quality
- [ ] Run `black --check .` - formatting should be consistent
- [ ] Run `isort --check-only .` - imports should be sorted
- [ ] Run `mypy .` - type checking (may have warnings, but should run)
- [ ] Verify type hints added to functions

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-3-code-quality && make format-check && make lint && make type-check
```

### Phase 4: Error Handling
- [ ] Verify `exceptions.py` exists with custom exceptions
- [ ] Check that error handling uses custom exceptions (grep for `from exceptions import`)
- [ ] Run `python main.py --help` - should work without errors
- [ ] Test that error messages are more descriptive

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-4-error-handling && python main.py --help && python -c "from exceptions import MigrationError; print('OK')"
```

### Phase 5: Security
- [ ] Verify environment variable support (check for `os.getenv` or `python-dotenv`)
- [ ] Check that `config_schema.json` exists
- [ ] Verify configuration validation works
- [ ] Test that credentials are not logged

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-5-security && python -c "from config import MigrationConfig; print('Config OK')"
```

### Phase 6: Configuration Management
- [ ] Verify `config.py` exists with dataclass configs
- [ ] Test configuration loading: `python -c "from config import MigrationConfig; print('OK')"`
- [ ] Check backward compatibility with existing config.yaml

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-6-config-management && python -c "from config import MigrationConfig; c = MigrationConfig.from_yaml('config.yaml.example'); print('Config loaded')"
```

### Phase 7: Logging & Progress
- [ ] Verify `utils/logging_config.py` exists
- [ ] Check for `rich` library usage
- [ ] Run with verbose logging to see enhanced output
- [ ] Verify log rotation is configured

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-7-logging && python -c "from utils.logging_config import setup_logging; print('Logging OK')"
```

### Phase 8: Performance
- [ ] Verify `utils/parallel.py` exists
- [ ] Check for parallel processing implementations
- [ ] Verify caching improvements
- [ ] Test memory usage monitoring

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-8-performance && python -c "from utils.parallel import parallel_process; print('Parallel processing OK')"
```

### Phase 9: Monitoring
- [ ] Verify `utils/metrics.py` exists
- [ ] Verify `utils/health_check.py` exists
- [ ] Test health check functionality
- [ ] Verify metrics tracking

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-9-monitoring && python -c "from utils.health_check import check_health; print('Health checks OK')"
```

### Phase 10: Architecture
- [ ] Verify package structure exists: `google_photos_icloud_migration/`
- [ ] Test package installation: `pip install -e .`
- [ ] Verify imports work: `python -c "from google_photos_icloud_migration.cli.main import main"`
- [ ] Test backward compatibility: `python main.py --help`

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-10-architecture && pip install -e . && python main.py --help
```

### Phase 11: CI/CD
- [ ] Verify `.github/workflows/` directory exists
- [ ] Check that workflow files are valid YAML
- [ ] Verify workflows reference correct paths
- [ ] Check that CONTRIBUTING.md is updated

**Cloud Agent Command:**
```bash
cd /path/to/repo && git checkout phase-11-cicd && ls -la .github/workflows/ && yamllint .github/workflows/*.yml 2>/dev/null || echo "YAML files exist"
```

## Using Cursor Cloud Agents

### Method 1: Create a Test Agent Task

Create a `.cursor/cloud-tasks/test-branch.cursor-task` file with:

```json
{
  "name": "Test Branch Functionality",
  "description": "Test a specific branch to ensure it works correctly",
  "steps": [
    "Checkout the specified branch",
    "Install dependencies (requirements.txt and requirements-dev.txt)",
    "Run the test_branch.sh script",
    "Report results"
  ],
  "commands": [
    "git checkout <branch-name>",
    "pip install -r requirements.txt",
    "pip install -r requirements-dev.txt",
    "./test_branch.sh <branch-name>"
  ]
}
```

### Method 2: Use Cloud Agent Prompt

Ask the Cloud Agent:

```
Please test the branch "phase-X-<name>" by:
1. Checking out the branch
2. Installing all dependencies
3. Running the test script: ./test_branch.sh phase-X-<name>
4. Running pytest if tests exist
5. Verifying the main.py script still works with --help flag
6. Reporting any errors or issues found

Make sure to test that:
- All imports work
- The CLI is functional
- Configuration loading works
- Any phase-specific features are present
```

### Method 3: Batch Testing Script for Cloud Agents

Create a script that tests all branches:

```bash
#!/bin/bash
# test_all_branches.sh - Test all phase branches

BRANCHES=(
    "phase-1-dev-tooling"
    "phase-2-testing"
    "phase-3-code-quality"
    "phase-4-error-handling"
    "phase-5-security"
    "phase-6-config-management"
    "phase-7-logging"
    "phase-8-performance"
    "phase-9-monitoring"
    "phase-10-architecture"
    "phase-11-cicd"
)

for branch in "${BRANCHES[@]}"; do
    echo "=========================================="
    echo "Testing: $branch"
    echo "=========================================="
    
    if git show-ref --verify --quiet refs/heads/$branch; then
        ./test_branch.sh $branch
        if [ $? -eq 0 ]; then
            echo "✓ $branch: PASSED"
        else
            echo "✗ $branch: FAILED"
        fi
    else
        echo "⚠ $branch: Branch does not exist, skipping"
    fi
    
    echo ""
done
```

## Expected Results

Each branch should:
1. ✅ Check out successfully
2. ✅ Install dependencies without errors
3. ✅ Pass import checks
4. ✅ Have working CLI (`--help` flag)
5. ✅ Pass syntax checks
6. ✅ Have appropriate files for that phase

## Reporting Issues

If a branch fails testing:
1. Note which test failed
2. Check if it's expected (e.g., tests may fail in early phases)
3. Verify the branch can still be merged safely
4. Document any issues in the branch's commit message or PR

## Notes

- Some branches may intentionally fail certain tests (e.g., formatting in Phase 3)
- Focus on functionality: does the tool still work?
- Backward compatibility: can existing configs still be used?
- Each phase should build on the previous one

