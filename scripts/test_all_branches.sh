#!/bin/bash
# Test all phase branches to verify they work correctly
# Usage: ./test_all_branches.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Store original branch
ORIGINAL_BRANCH=$(git branch --show-current)
echo -e "${BLUE}Current branch: $ORIGINAL_BRANCH${NC}"
echo ""

PASSED=0
FAILED=0
SKIPPED=0

for branch in "${BRANCHES[@]}"; do
    echo -e "${BLUE}=========================================="
    echo -e "Testing: $branch"
    echo -e "==========================================${NC}"
    
    # Check if branch exists locally
    if ! git show-ref --verify --quiet refs/heads/$branch 2>/dev/null; then
        echo -e "${YELLOW}⚠${NC} Branch '$branch' does not exist locally, checking remote..."
        if git ls-remote --heads origin $branch | grep -q $branch; then
            echo "  Fetching from remote..."
            git fetch origin $branch:$branch 2>/dev/null || {
                echo -e "${YELLOW}⚠${NC} Could not fetch branch, skipping"
                SKIPPED=$((SKIPPED + 1))
                echo ""
                continue
            }
        else
            echo -e "${YELLOW}⚠${NC} Branch does not exist, skipping"
            SKIPPED=$((SKIPPED + 1))
            echo ""
            continue
        fi
    fi
    
    # Test the branch
    if ./test_branch.sh $branch 2>&1; then
        echo -e "${GREEN}✓${NC} $branch: PASSED"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $branch: FAILED"
        FAILED=$((FAILED + 1))
    fi
    
    echo ""
done

# Return to original branch
git checkout $ORIGINAL_BRANCH > /dev/null 2>&1

# Summary
echo -e "${BLUE}=========================================="
echo -e "Testing Summary"
echo -e "==========================================${NC}"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All branches passed testing!${NC}"
    exit 0
else
    echo -e "${RED}Some branches failed testing.${NC}"
    exit 1
fi

