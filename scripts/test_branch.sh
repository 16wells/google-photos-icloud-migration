#!/bin/bash
# Test script for verifying branch functionality
# Usage: ./test_branch.sh <branch-name>

set -e

BRANCH_NAME=${1:-"main"}

echo "=========================================="
echo "Testing branch: $BRANCH_NAME"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        exit 1
    fi
}

# Checkout the branch
echo "Checking out branch: $BRANCH_NAME"
git checkout "$BRANCH_NAME" 2>/dev/null || {
    echo -e "${RED}Error: Branch $BRANCH_NAME does not exist${NC}"
    exit 1
}
print_result $? "Checked out branch"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
print_result $? "Installed production dependencies"

# Check if dev dependencies file exists and install if present
if [ -f requirements-dev.txt ]; then
    pip install -r requirements-dev.txt > /dev/null 2>&1 || echo -e "${YELLOW}⚠${NC} Some dev dependencies may be missing (optional)"
fi

# Test 1: Import check
echo ""
echo "Test 1: Checking imports..."
python3 -c "
try:
    from google_photos_icloud_migration.cli.main import main
    print('Package imports: OK')
except ImportError as e:
    # Try old-style imports for earlier branches
    try:
        from main import main
        print('Legacy imports: OK')
    except ImportError:
        print(f'Import failed: {e}')
        exit(1)
" 2>&1
print_result $? "Imports work correctly"

# Test 2: CLI help command
echo ""
echo "Test 2: Testing CLI help command..."
python3 main.py --help > /dev/null 2>&1
print_result $? "CLI help command works"

# Test 3: Configuration validation
echo ""
echo "Test 3: Testing configuration loading..."
if [ -f config.yaml.example ]; then
    python3 -c "
import yaml
with open('config.yaml.example', 'r') as f:
    config = yaml.safe_load(f)
    assert 'google_drive' in config or 'processing' in config, 'Invalid config structure'
    print('Configuration structure: OK')
" 2>&1
    print_result $? "Configuration file is valid"
else
    echo -e "${YELLOW}⚠${NC} config.yaml.example not found (skipping)"
fi

# Test 4: Code quality checks (if dev tools available)
echo ""
echo "Test 4: Running code quality checks..."
if command -v black &> /dev/null; then
    black --check . > /dev/null 2>&1 && echo -e "${GREEN}✓${NC} Code formatting check passed" || echo -e "${YELLOW}⚠${NC} Code formatting issues (non-blocking)"
else
    echo -e "${YELLOW}⚠${NC} black not installed (skipping format check)"
fi

# Test 5: Run unit tests if they exist
echo ""
echo "Test 5: Running unit tests..."
if [ -d "tests" ] && [ -n "$(ls -A tests/*.py 2>/dev/null)" ]; then
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short 2>&1 | tail -5
        TEST_EXIT_CODE=${PIPESTATUS[0]}
        if [ $TEST_EXIT_CODE -eq 0 ] || [ $TEST_EXIT_CODE -eq 5 ]; then
            # Exit code 5 means no tests collected, which is OK for some branches
            print_result 0 "Unit tests completed"
        else
            print_result $TEST_EXIT_CODE "Unit tests failed"
        fi
    else
        echo -e "${YELLOW}⚠${NC} pytest not installed (skipping tests)"
    fi
else
    echo -e "${YELLOW}⚠${NC} No tests found (skipping)"
fi

# Test 6: Check for critical files
echo ""
echo "Test 6: Verifying critical files exist..."
CRITICAL_FILES=("main.py" "requirements.txt" "README.md")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file missing"
        exit 1
    fi
done

# Test 7: Syntax check on Python files
echo ""
echo "Test 7: Checking Python syntax..."
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -not -path "./__pycache__/*" | head -10 | while read file; do
    python3 -m py_compile "$file" 2>&1 || {
        echo -e "${RED}✗${NC} Syntax error in $file"
        exit 1
    }
done
print_result $? "Python syntax is valid"

echo ""
echo -e "${GREEN}=========================================="
echo -e "All tests passed for branch: $BRANCH_NAME"
echo -e "==========================================${NC}"

