#!/bin/bash
# Generate requirements lock files using pip-tools
# This ensures reproducible builds

set -e

echo "Generating requirements lock files..."

# Check if pip-tools is installed
if ! command -v pip-compile &> /dev/null; then
    echo "pip-tools not found. Installing..."
    pip install pip-tools
fi

# Generate requirements.lock.txt from requirements.txt
echo "Generating requirements.lock.txt..."
pip-compile \
    requirements.txt \
    --output-file=requirements.lock.txt \
    --resolver=backtracking \
    --upgrade

# Generate requirements-dev.lock.txt from requirements-dev.txt
echo "Generating requirements-dev.lock.txt..."
pip-compile \
    requirements-dev.txt \
    --output-file=requirements-dev.lock.txt \
    --resolver=backtracking \
    --upgrade

echo "✓ Lock files generated successfully!"
echo ""
echo "To install from lock files:"
echo "  pip install -r requirements.lock.txt"
echo "  pip install -r requirements-dev.lock.txt"
