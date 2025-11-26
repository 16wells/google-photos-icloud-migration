# Testing Branches with Cloud Agents

This guide explains how to test each phase branch using Cursor Cloud Agents before merging.

## Quick Start

### Test a Single Branch

Use the automated test script:

```bash
./test_branch.sh phase-1-dev-tooling
```

### Test All Branches

Run all branch tests at once:

```bash
./test_all_branches.sh
```

## Using Cursor Cloud Agents

### Method 1: Simple Cloud Agent Prompt

Open Cursor Cloud Agents and use this prompt:

```
Please test the branch "phase-X-<name>" by running:
1. git checkout phase-X-<name>
2. pip install -r requirements.txt
3. pip install -r requirements-dev.txt
4. ./test_branch.sh phase-X-<name>
5. python main.py --help

Report any errors found and confirm if the branch is ready to merge.
```

Replace `phase-X-<name>` with the actual branch name (e.g., `phase-1-dev-tooling`).

### Method 2: Copy-Paste Test Command

For Cloud Agents, use this single command:

```bash
BRANCH="phase-1-dev-tooling" && \
git checkout $BRANCH && \
pip install -r requirements.txt && \
pip install -r requirements-dev.txt 2>/dev/null && \
./test_branch.sh $BRANCH && \
python main.py --help && \
echo "✓ Branch $BRANCH is ready to merge"
```

### Method 3: Use the Detailed Guide

See `.cursor/cloud-test-agent.md` for:
- Detailed checklist for each phase
- Phase-specific test commands
- Expected results
- Troubleshooting tips

## What Gets Tested

The test script checks:

1. **Branch checkout** - Verifies branch exists and can be checked out
2. **Dependencies** - Installs required packages
3. **Imports** - Verifies all imports work (supports both old and new package structure)
4. **CLI functionality** - Tests `python main.py --help`
5. **Configuration** - Validates config.yaml.example structure
6. **Code quality** - Runs formatting and linting checks (if tools installed)
7. **Unit tests** - Runs pytest if tests exist
8. **File structure** - Verifies critical files exist
9. **Syntax** - Checks Python syntax is valid

## Example: Testing Phase 10 (Architecture)

Since Phase 10 introduces the package structure, test it like this:

```bash
# In Cloud Agent:
git checkout phase-10-architecture
pip install -e .  # Install the package
pip install -r requirements-dev.txt
./test_branch.sh phase-10-architecture

# Verify package structure works:
python -c "from google_photos_icloud_migration.cli.main import main; print('Package imports work!')"
python main.py --help  # Backward compatibility
```

## Expected Results

✅ **Success indicators:**
- All tests pass
- CLI help command works
- Imports succeed
- No critical errors

⚠️ **Acceptable warnings:**
- Some tests may fail in early phases (tests added later)
- Formatting issues in pre-formatting phases
- Missing optional dev dependencies

❌ **Failure indicators:**
- Syntax errors
- Import failures
- CLI doesn't work
- Critical files missing

## Branch Status

Most branches have already been merged to main. To test individual branches:

1. **Local branches** - Already exist, just checkout and test
2. **Remote branches** - Fetch first: `git fetch origin phase-X-<name>:phase-X-<name>`
3. **Merged branches** - Can test the commits that introduced each phase

## Testing After Merges

To verify main branch after all merges:

```bash
git checkout main
./test_branch.sh main
```

This ensures the final merged state works correctly.

## Troubleshooting

### Branch doesn't exist locally
```bash
git fetch origin
git checkout phase-X-<name>
```

### Import errors in early phases
Early phases use direct imports. The test script handles both:
- Old: `from main import main`
- New: `from google_photos_icloud_migration.cli.main import main`

### Tests fail
Some test failures are expected:
- Phase 1-2: No tests yet
- Phase 3: Formatting may differ
- Later phases: Should have passing tests

Focus on **functionality** - does the tool work?

## Cloud Agent Testing Checklist

When using Cloud Agents, verify:

- [ ] Branch checks out successfully
- [ ] Dependencies install without errors
- [ ] `python main.py --help` works
- [ ] Phase-specific features are present
- [ ] No blocking errors in test output
- [ ] Tool functionality is preserved

## Next Steps

1. Use Cloud Agents to test each branch
2. Fix any issues found
3. Merge successful branches
4. Keep main branch always working

For detailed phase-specific instructions, see `.cursor/cloud-test-agent.md`.

