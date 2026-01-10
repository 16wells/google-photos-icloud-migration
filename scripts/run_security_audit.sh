#!/bin/bash
# Run security audit using pip-audit
# This script checks for known vulnerabilities in dependencies

set -e

echo "Running security audit on dependencies..."
echo ""

# Check if pip-audit is installed
if ! command -v pip-audit &> /dev/null; then
    echo "pip-audit not found. Installing..."
    pip install pip-audit
fi

# Run audit on production dependencies
echo "Auditing production dependencies (requirements.txt)..."
pip-audit -r requirements.txt

echo ""
echo "Auditing development dependencies (requirements-dev.txt)..."
pip-audit -r requirements-dev.txt || echo "Note: Some dev dependencies may have vulnerabilities - review carefully"

echo ""
echo "✓ Security audit completed!"
