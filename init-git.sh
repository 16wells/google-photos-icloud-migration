#!/bin/bash
# Script to initialize git repository and set up remote

set -e

cd "$(dirname "$0")"

echo "Initializing git repository..."
git init

echo "Adding all files..."
git add .

echo "Creating initial commit..."
git commit -m "Initial commit: Google Photos to iCloud Photos migration tool"

echo "Setting default branch to main..."
git branch -M main

# Get GitHub username
GITHUB_USER=$(git config user.name 2>/dev/null || echo "")
if [ -z "$GITHUB_USER" ]; then
    echo ""
    echo "Please enter your GitHub username:"
    read GITHUB_USER
fi

REMOTE_URL="https://github.com/${GITHUB_USER}/google-photos-icloud-migration.git"

echo ""
echo "Adding remote repository: ${REMOTE_URL}"
git remote add origin "${REMOTE_URL}" 2>/dev/null || git remote set-url origin "${REMOTE_URL}"

echo ""
echo "Git repository initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Create the repository on GitHub:"
echo "   - Go to https://github.com/new"
echo "   - Repository name: google-photos-icloud-migration"
echo "   - Don't initialize with README, .gitignore, or license"
echo "   - Click 'Create repository'"
echo ""
echo "2. Push your code:"
echo "   git push -u origin main"
echo ""

