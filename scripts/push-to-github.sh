#!/bin/bash
# Push project to GitHub repository

cd "$(dirname "$0")"

echo "Initializing git repository..."
git init

echo "Adding all files..."
git add .

echo "Creating initial commit..."
git commit -m "Initial commit: Google Photos to iCloud Photos migration tool"

echo "Setting branch to main..."
git branch -M main

echo "Adding remote repository..."
git remote add origin https://github.com/16wells/google-photos-icloud-migration.git 2>/dev/null || git remote set-url origin https://github.com/16wells/google-photos-icloud-migration.git

echo "Pushing to GitHub..."
git push -u origin main

echo ""
echo "✓ Successfully pushed to GitHub!"
echo "Repository: https://github.com/16wells/google-photos-icloud-migration"

