# Cloud Agent Testing Prompt Template

Copy and paste this prompt into Cursor Cloud Agents to test a specific branch.

## Testing Prompt Template

```
I need you to test the branch "BRANCH_NAME" to verify it works correctly before merging.

Please perform the following steps:

1. Checkout the branch:
   git checkout BRANCH_NAME

2. Install dependencies:
   pip install -r requirements.txt
   pip install -r requirements-dev.txt || echo "Dev deps optional"

3. Run the automated test script:
   ./test_branch.sh BRANCH_NAME

4. Additionally, verify:
   - Run: python main.py --help (should show help without errors)
   - Check that phase-specific files exist (see checklist in .cursor/cloud-test-agent.md)
   - Run any relevant tests: pytest tests/ -v (if tests exist)
   - Check imports work: python -c "from google_photos_icloud_migration.cli.main import main; print('OK')" (for later phases) or python -c "from main import main; print('OK')" (for earlier phases)

5. Report results:
   - List any errors encountered
   - Note any missing files expected for this phase
   - Confirm if the branch is ready to merge
   - Suggest any fixes if issues found

The branch should maintain backward compatibility with existing functionality.
```

## Phase-Specific Test Prompts

### Test Phase 1 (Developer Tooling)
```
Test branch "phase-1-dev-tooling":
- Verify Makefile works: make help
- Check pre-commit config exists: ls -la .pre-commit-config.yaml
- Verify CHANGELOG.md exists
- Run: make format-check (if black is installed)
```

### Test Phase 2 (Testing Infrastructure)
```
Test branch "phase-2-testing":
- Check tests directory exists: ls -la tests/
- Run tests: pytest tests/ -v
- Verify fixtures exist: ls -la tests/fixtures/
- Check test imports work
```

### Test Phase 10 (Architecture)
```
Test branch "phase-10-architecture":
- Verify package structure: ls -la google_photos_icloud_migration/
- Test package install: pip install -e .
- Test imports: python -c "from google_photos_icloud_migration.cli.main import main"
- Verify backward compatibility: python main.py --help
- Check entry point: which photo-migrate || echo "Not installed"
```

### Test Phase 11 (CI/CD)
```
Test branch "phase-11-cicd":
- Verify workflows exist: ls -la .github/workflows/
- Check YAML syntax: yamllint .github/workflows/*.yml || python -c "import yaml; [yaml.safe_load(open(f)) for f in __import__('glob').glob('.github/workflows/*.yml')]"
- Verify CHANGELOG updated
- Check CONTRIBUTING.md has updates
```

## Quick Test Command for Cloud Agents

Single command to test any branch:

```bash
BRANCH="phase-X-name" && \
git checkout $BRANCH && \
pip install -r requirements.txt && \
pip install -r requirements-dev.txt 2>/dev/null && \
./test_branch.sh $BRANCH && \
echo "✓ Branch $BRANCH is ready to merge"
```

## Batch Testing All Branches

To test all phase branches at once:

```bash
for branch in phase-{1..11}-*; do
  echo "Testing $branch..."
  git checkout $branch 2>/dev/null && ./test_branch.sh $branch || echo "Skipped $branch"
done
```

